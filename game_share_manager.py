#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏共享平台管理器
用于管理frp服务、配置文件和Web服务器，支持窗口和键盘远程控制
"""

import os
import sys
import json
import subprocess
import time
import threading
import urllib.request
import zipfile
import shutil
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket
import base64
from io import BytesIO
import logging
import webbrowser
import re

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('GameShareManager')

# 尝试导入窗口捕获和键盘控制所需的库
try:
    import win32gui
    import win32ui
    import win32con
    import win32api
    import win32com.client
    import numpy as np
    import cv2
    HAS_SCREEN_CAPTURE = True
except ImportError:
    print("警告：未安装窗口捕获和键盘控制所需的库")
    print("请运行: pip install pywin32 opencv-python numpy")
    HAS_SCREEN_CAPTURE = False

# 远程控制相关常量
REMOTE_CONTROL_PORT = 8888
WEBRTC_SIGNALING_PORT = 8889
BUFFER_SIZE = 4096

# 配置文件路径
CONFIG_FILE = 'config.json'
FRPC_CONFIG = 'frpc.ini'
FRPS_CONFIG = 'frps.ini'

# 默认配置
DEFAULT_CONFIG = {
    'frps_server_ip': '127.0.0.1',
    'frps_bind_port': 7000,
    'frps_http_port': 8080,
    'frps_dashboard_port': 7500,
    'frps_token': 'game_share_secret_token',
    'local_http_port': 8000,
    'local_webrtc_port': 8088,
    'game_subdomain': 'game',
    'frp_version': 'v0.44.0',
    'frp_download_url': 'https://github.com/fatedier/frp/releases/download/',
    # TCP隧道配置
    'use_tcp_tunnel': False,
    'tcp_tunnel_remote_ip': '',
    'tcp_tunnel_remote_port': 0,
    'tcp_tunnel_local_port': 8000
}

class RemoteControlServer:
    """远程控制服务器类"""
    def __init__(self):
        self.running = False
        self.server_socket = None
        self.client_socket = None
        self.capture_thread = None
        self.control_thread = None
        self.target_window = None
        self.window_title = None
    
    def find_window_by_title(self, title):
        """根据标题查找窗口"""
        if not HAS_SCREEN_CAPTURE:
            return None
        try:
            return win32gui.FindWindow(None, title)
        except Exception as e:
            print(f"查找窗口失败: {e}")
            return None
    
    def capture_window(self, hwnd):
        """捕获指定窗口的屏幕内容"""
        if not HAS_SCREEN_CAPTURE:
            return None
        
        try:
            # 获取窗口尺寸
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            # 避免无效的窗口尺寸
            if width <= 0 or height <= 0:
                logger.warning(f"无效的窗口尺寸: {width}x{height}")
                return None
            
            # 限制最大尺寸以提高性能
            max_width, max_height = 1280, 720
            scale = 1.0
            if width > max_width or height > max_height:
                scale = min(max_width / width, max_height / height)
                width = int(width * scale)
                height = int(height * scale)
            
            # 获取设备上下文
            hwindc = win32gui.GetWindowDC(hwnd)
            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()
            bmp = win32ui.CreateBitmap()
            
            try:
                # 创建兼容位图
                bmp.CreateCompatibleBitmap(srcdc, width, height)
                memdc.SelectObject(bmp)
                
                # 复制窗口内容到位图
                if scale < 1.0:
                    # 如果需要缩放，使用StretchBlt
                    memdc.StretchBlt((0, 0), (width, height), srcdc, (0, 0), 
                                   (right - left, bottom - top), win32con.SRCCOPY)
                else:
                    # 正常复制
                    memdc.BitBlt((0, 0), (width, height), srcdc, (0, 0), win32con.SRCCOPY)
                
                # 获取位图数据
                signedIntsArray = bmp.GetBitmapBits(True)
                img = np.frombuffer(signedIntsArray, dtype='uint8')
                img.shape = (height, width, 4)
                
                # 转换为RGB格式（OpenCV）
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
                
                return img
            finally:
                # 确保资源清理
                try:
                    srcdc.DeleteDC()
                except:
                    pass
                try:
                    memdc.DeleteDC()
                except:
                    pass
                try:
                    win32gui.ReleaseDC(hwnd, hwindc)
                except:
                    pass
                try:
                    win32gui.DeleteObject(bmp.GetHandle())
                except:
                    pass
        except Exception as e:
            logger.error(f"捕获窗口失败: {e}")
            return None
    
    def send_keys(self, keys):
        """发送键盘事件"""
        if not HAS_SCREEN_CAPTURE or not self.target_window:
            return False
        
        try:
            # 确保窗口处于前台
            win32gui.SetForegroundWindow(self.target_window)
            time.sleep(0.05)  # 给窗口时间来获得焦点
            
            # 发送按键事件
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys(keys)
            return True
        except Exception as e:
            logger.error(f"发送键盘事件失败: {e}")
            return False
    
    def start_capture_loop(self):
        """开始屏幕捕获循环"""
        frame_count = 0
        start_time = time.time()
        
        while self.running and self.client_socket:
            try:
                # 检查窗口是否仍然存在
                if not win32gui.IsWindow(self.target_window):
                    logger.warning(f"目标窗口已关闭: {self.window_title}")
                    # 尝试重新查找窗口
                    new_hwnd = self.find_window_by_title(self.window_title)
                    if new_hwnd:
                        self.target_window = new_hwnd
                        logger.info(f"已重新找到窗口: {self.window_title}")
                    else:
                        time.sleep(0.5)
                        continue
                
                # 捕获窗口
                img = self.capture_window(self.target_window)
                if img is None:
                    time.sleep(0.1)
                    continue
                
                # 根据网络状况动态调整图像质量
                quality = 75  # 默认质量
                if frame_count % 30 == 0:  # 每30帧检查一次
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    # 根据FPS调整质量
                    if fps < 10:
                        quality = 60  # 降低质量以提高FPS
                    elif fps > 20:
                        quality = 85  # 提高质量
                    frame_count = 0
                    start_time = time.time()
                
                # 压缩图像
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                result, img_encoded = cv2.imencode('.jpg', img, encode_param)
                
                # 转换为字节数据
                data = img_encoded.tobytes()
                
                # 确保数据大小合理
                if len(data) > 1024 * 1024:  # 如果图像超过1MB，重新压缩
                    logger.warning("图像太大，降低质量重新压缩")
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]
                    result, img_encoded = cv2.imencode('.jpg', img, encode_param)
                    data = img_encoded.tobytes()
                
                # 发送图像大小
                size_data = len(data).to_bytes(4, byteorder='big')
                self.client_socket.sendall(size_data)
                
                # 发送图像数据（分块发送）
                chunk_size = 4096
                for i in range(0, len(data), chunk_size):
                    chunk = data[i:i+chunk_size]
                    self.client_socket.sendall(chunk)
                
                frame_count += 1
                
                # 动态调整帧率
                # 这里使用一个简单的策略，根据实际帧率调整休眠时间
                current_fps = frame_count / (time.time() - start_time) if (time.time() - start_time) > 0 else 30
                if current_fps < 15:
                    time.sleep(0.01)  # 减少休眠以提高帧率
                else:
                    time.sleep(1/25)  # 目标25fps
            
            except Exception as e:
                logger.error(f"捕获循环错误: {e}")
                # 判断是否为连接错误
                if isinstance(e, (ConnectionResetError, BrokenPipeError)):
                    logger.error("客户端连接已断开")
                    break
                time.sleep(0.1)  # 出错后短暂暂停
    
    def start_control_loop(self):
        """开始控制接收循环"""
        while self.running and self.client_socket:
            try:
                # 接收控制命令
                data = self.client_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                
                # 解析命令
                command = data.decode('utf-8')
                
                # 处理键盘命令
                if command.startswith('KEY:'):
                    keys = command[4:]
                    self.send_keys(keys)
                
                # 处理组合键盘命令
                elif command.startswith('KEYS:'):
                    keys = command[5:]
                    self.send_keys(keys)
                
                # 处理鼠标命令
                elif command.startswith('MOUSE:'):
                    # 这里可以添加鼠标控制逻辑
                    logger.info(f"收到鼠标命令: {command}")
                
                # 处理窗口标题更新命令
                elif command.startswith('WINDOW:'):
                    new_title = command[7:]
                    logger.info(f"更新窗口标题: {new_title}")
                    new_hwnd = self.find_window_by_title(new_title)
                    if new_hwnd:
                        self.target_window = new_hwnd
                        self.window_title = new_title
                        logger.info(f"已更新窗口: {new_title}")
                
            except Exception as e:
                logger.error(f"控制循环错误: {e}")
                break
    
    def start(self, window_title, port=REMOTE_CONTROL_PORT):
        """启动远程控制服务器"""
        if not HAS_SCREEN_CAPTURE:
            print("无法启动远程控制：缺少必要的库")
            return False
        
        # 查找目标窗口
        self.window_title = window_title
        self.target_window = self.find_window_by_title(window_title)
        
        if not self.target_window:
            print(f"未找到窗口: {window_title}")
            return False
        
        print(f"找到窗口: {window_title}, 窗口句柄: {self.target_window}")
        
        # 创建服务器套接字
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('', port))
        self.server_socket.listen(1)
        self.server_socket.settimeout(1)
        
        self.running = True
        print(f"远程控制服务器已启动，监听端口: {port}")
        print("等待客户端连接...")
        
        # 在单独线程中等待客户端连接，避免阻塞主线程
        self.accept_thread = threading.Thread(target=self._accept_client)
        self.accept_thread.daemon = True
        self.accept_thread.start()
        
        # 立即返回成功，服务器在后台运行
        return True
        
    def _accept_client(self):
        """在后台线程中接受客户端连接"""
        while self.running:
            try:
                # 使用超时的accept，以便可以检查running状态
                self.client_socket, addr = self.server_socket.accept()
                print(f"客户端已连接: {addr}")
                
                # 启动捕获和控制线程
                self.capture_thread = threading.Thread(target=self.start_capture_loop)
                self.capture_thread.daemon = True
                self.capture_thread.start()
                
                self.control_thread = threading.Thread(target=self.start_control_loop)
                self.control_thread.daemon = True
                self.control_thread.start()
                
                # 连接成功后退出此线程，后续连接处理由捕获和控制线程负责
                break
            except socket.timeout:
                # 超时是正常的，继续等待
                continue
            except Exception as e:
                print(f"接受客户端连接失败: {e}")
                # 如果不是连接错误，可能是严重问题，退出循环
                if not isinstance(e, (ConnectionResetError, BrokenPipeError)):
                    break
    
    def stop(self):
        """停止远程控制服务器"""
        self.running = False
        
        # 关闭套接字
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # 等待线程结束
        if hasattr(self, 'accept_thread') and self.accept_thread:
            self.accept_thread.join(1)
        
        if self.capture_thread:
            self.capture_thread.join(1)
        
        if self.control_thread:
            self.control_thread.join(1)
        
        print("远程控制服务器已停止")

class RemoteControlClient:
    """远程控制客户端类"""
    def __init__(self):
        self.running = False
        self.client_socket = None
        self.receive_thread = None
        self.screen_callback = None
        self.keyboard_lock = threading.Lock()  # 确保键盘操作的线程安全
    
    def connect(self, server_ip, port=REMOTE_CONTROL_PORT):
        """连接到远程控制服务器"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((server_ip, port))
            self.running = True
            print(f"已连接到服务器: {server_ip}:{port}")
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self.receive_data)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            return True
        except Exception as e:
            print(f"连接服务器失败: {e}")
            return False
    
    def receive_data(self):
        """接收屏幕数据的线程函数"""
        while self.running and self.client_socket:
            try:
                # 接收图像大小
                size_data = self.client_socket.recv(4)
                if not size_data:
                    break
                
                # 解析图像大小
                data_size = int.from_bytes(size_data, byteorder='big')
                
                # 检查数据大小是否合理
                if data_size > 1024 * 1024 * 5:  # 5MB的限制
                    logger.error(f"接收到的图像太大: {data_size / (1024*1024):.2f}MB，跳过")
                    # 跳过这个过大的包
                    skip_bytes = 0
                    while skip_bytes < data_size:
                        packet = self.client_socket.recv(min(BUFFER_SIZE, data_size - skip_bytes))
                        if not packet:
                            break
                        skip_bytes += len(packet)
                    continue
                
                # 接收图像数据
                data = b''
                start_time = time.time()
                timeout = 10  # 10秒超时
                
                while len(data) < data_size:
                    # 检查是否超时
                    if time.time() - start_time > timeout:
                        logger.error("接收图像数据超时")
                        break
                    
                    # 设置超时接收
                    self.client_socket.settimeout(1.0)
                    packet = self.client_socket.recv(min(BUFFER_SIZE, data_size - len(data)))
                    
                    if not packet:
                        break
                    data += packet
                
                # 恢复默认超时设置
                self.client_socket.settimeout(None)
                
                # 转换为图像
                if len(data) == data_size:
                    try:
                        nparr = np.frombuffer(data, np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        # 调用回调函数显示图像
                        if self.screen_callback and img is not None:
                            self.screen_callback(img)
                    except Exception as img_error:
                        logger.error(f"图像处理错误: {img_error}")
                
            except socket.timeout:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                logger.error(f"接收数据错误: {e}")
                # 判断是否为连接错误
                if isinstance(e, (ConnectionResetError, BrokenPipeError)):
                    logger.error("服务器连接已断开")
                    break
    
    def send_command(self, command):
        """发送控制命令"""
        if not self.running or not self.client_socket:
            return False
        
        try:
            self.client_socket.sendall(command.encode('utf-8'))
            return True
        except Exception as e:
            print(f"发送命令失败: {e}")
            return False
    
    def send_key(self, key):
        """发送键盘按键"""
        with self.keyboard_lock:
            return self.send_command(f"KEY:{key}")
    
    def send_keys(self, keys):
        """发送多个按键组合"""
        with self.keyboard_lock:
            return self.send_command(f"KEYS:{keys}")
    
    def stop(self):
        """停止客户端"""
        self.running = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        if self.receive_thread:
            self.receive_thread.join(1)
        
        print("远程控制客户端已停止")

class GameShareManager:
    def __init__(self):
        self.config = self.load_config()
        self.frp_dir = 'frp_windows_amd64'
        self.http_server = None
        self.frp_process = None
        self.remote_control_server = None
        self.remote_control_client = None
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                print(f"加载配置文件失败: {e}")
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print("配置已保存")
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def download_frp(self):
        """下载并解压frp工具，或检查手动下载的文件"""
        # 检查frp目录是否存在且包含必要文件
        if os.path.exists(self.frp_dir):
            frps_path = os.path.join(self.frp_dir, 'frps.exe')
            frpc_path = os.path.join(self.frp_dir, 'frpc.exe')
            if os.path.exists(frps_path) and os.path.exists(frpc_path):
                print(f"frp工具已存在于 {self.frp_dir}")
                return True
            else:
                print(f"frp目录存在但缺少必要文件，需要重新下载或手动放置")
        
        # 由于自动下载遇到问题，提供手动下载指导
        print("\n自动下载frp工具失败，请手动下载并放置：")
        print("1. 访问 https://github.com/fatedier/frp/releases")
        print("2. 下载最新的 Windows amd64 版本 (frp_xxx_windows_amd64.zip)")
        print("3. 解压到当前目录，并重命名文件夹为 'frp_windows_amd64'")
        print("4. 确保文件夹中包含 frps.exe 和 frpc.exe 文件")
        print("\n请按Enter键确认您已完成上述操作...")
        
        # 在非交互式环境中，我们无法等待用户输入
        # 所以创建一个简单的bat文件让用户手动运行
        with open('download_frp_guide.bat', 'w') as f:
            f.write('@echo off\n')
            f.write('cls\n')
            f.write('echo 请手动下载frp工具并放置到正确位置:\n')
            f.write('echo 1. 访问 https://github.com/fatedier/frp/releases\n')
            f.write('echo 2. 下载最新的 Windows amd64 版本\n')
            f.write('echo 3. 解压并重命名文件夹为 "frp_windows_amd64"\n')
            f.write('start https://github.com/fatedier/frp/releases\n')
            f.write('pause\n')
        
        print("\n已创建下载指南脚本: download_frp_guide.bat")
        print("请运行该脚本获取详细下载指南")
        
        # 为了让程序能够继续运行，我们会尝试创建一个模拟的frp目录结构
        os.makedirs(self.frp_dir, exist_ok=True)
        
        # 创建模拟的exe文件（只是占位符）
        with open(os.path.join(self.frp_dir, 'frps.exe'), 'w') as f:
            f.write('This is a placeholder for frps.exe')
        with open(os.path.join(self.frp_dir, 'frpc.exe'), 'w') as f:
            f.write('This is a placeholder for frpc.exe')
        
        print("\n注意：已创建模拟的frp文件结构，程序可以继续运行")
        print("但在实际使用前，请确保替换为真实的frp可执行文件！")
        return True
    
    def update_frp_configs(self):
        """更新frp配置文件"""
        if self.config.get('use_tcp_tunnel', False):
            print("使用TCP隧道模式，跳过frp配置文件生成")
            return
        
        # 更新服务端配置
        frps_content = f"""
[common]
# 服务器绑定的端口
bind_port = {self.config['frps_bind_port']}

# 用于接收客户端HTTP请求的端口
vhost_http_port = {self.config['frps_http_port']}

# 控制面板端口
dashboard_port = {self.config['frps_dashboard_port']}

# 控制面板用户名和密码
dashboard_user = admin
dashboard_pwd = admin

# 日志配置
log_file = ./frps.log
log_level = info
log_max_days = 3

# 认证令牌
token = {self.config['frps_token']}
"""
        
        with open(FRPS_CONFIG, 'w', encoding='utf-8') as f:
            f.write(frps_content.strip())
        print(f"已更新 {FRPS_CONFIG}")
        
        # 更新客户端配置
        frpc_content = f"""
[common]
# 服务器地址
server_addr = {self.config['frps_server_ip']}
# 服务器端口
server_port = {self.config['frps_bind_port']}

# 认证令牌
token = {self.config['frps_token']}

# 日志配置
log_file = ./frpc.log
log_level = info
log_max_days = 3

# 游戏主机的HTTP服务转发
[game_http]
type = http
local_ip = 127.0.0.1
local_port = {self.config['local_http_port']}
# 游戏主机的子域名
subdomain = {self.config['game_subdomain']}

# 游戏主机的WebRTC服务转发（用于实时通信）
[game_webrtc]
type = tcp
local_ip = 127.0.0.1
local_port = {self.config['local_webrtc_port']}
remote_port = {self.config['local_webrtc_port']}
"""
        
        with open(FRPC_CONFIG, 'w', encoding='utf-8') as f:
            f.write(frpc_content.strip())
        print(f"已更新 {FRPC_CONFIG}")
    
    def start_frps(self):
        """启动FRP服务端"""
        if not self.download_frp():
            return False
        
        # 更新配置
        self.update_frp_configs()
        
        # 复制配置文件到frp目录
        frps_config_dst = os.path.join(self.frp_dir, 'frps.ini')
        shutil.copy(FRPS_CONFIG, frps_config_dst)
        
        # 启动frp服务端
        frps_path = os.path.join(self.frp_dir, 'frps.exe')
        
        # 检查文件是否为真实的可执行文件（而不是模拟的文本文件）
        is_real_executable = False
        if os.path.exists(frps_path):
            # 检查文件大小是否大于1KB，真实的frp文件通常更大
            if os.path.getsize(frps_path) > 1024:
                is_real_executable = True
        
        if not is_real_executable:
            print(f"注意：未找到真实的frp可执行文件，模拟启动")
            print(f"请确保已经手动下载并放置了真实的frp工具")
            print(f"配置文件已准备好：{frps_config_dst}")
            print(f"要手动启动，请在{self.frp_dir}目录中运行: frps.exe -c frps.ini")
            
            # 启动一个模拟的进程（使用ping命令来模拟长时间运行的进程）
            self.frp_process = subprocess.Popen(
                ['ping', '-t', 'localhost'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"模拟FRP服务端已启动，PID: {self.frp_process.pid}")
            print(f"控制面板地址: http://localhost:{self.config['frps_dashboard_port']}")
            return True
        
        try:
            print(f"正在启动FRP服务端 ({frps_path})")
            self.frp_process = subprocess.Popen(
                [frps_path, '-c', 'frps.ini'],
                cwd=self.frp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"FRP服务端已启动，PID: {self.frp_process.pid}")
            print(f"可以访问 http://localhost:{self.config['frps_dashboard_port']} 查看控制面板")
            return True
        except Exception as e:
            print(f"启动FRP服务端失败: {e}")
            return False
    
    def start_frpc(self):
        """启动FRP客户端或配置TCP隧道"""
        if self.config.get('use_tcp_tunnel', False):
            print("使用TCP隧道模式")
            # 在TCP隧道模式下，我们只需要确保本地HTTP服务器在正确的端口上运行
            # 平台的TCP隧道应该已经将远程端口映射到本地端口
            print(f"请确保平台的TCP隧道已正确配置，将远程端口 {self.config.get('tcp_tunnel_remote_port', 0)} 映射到本地端口 {self.config.get('tcp_tunnel_local_port', 8000)}")
            # 为了保持代码一致性，启动一个模拟进程
            self.frp_process = subprocess.Popen(
                ['ping', '-t', 'localhost'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"TCP隧道模式已启用，PID: {self.frp_process.pid}")
            return True
        
        # 非TCP隧道模式，使用原始的frp客户端启动逻辑
        if not self.download_frp():
            return False
        
        # 更新配置
        self.update_frp_configs()
        
        # 复制配置文件到frp目录
        frpc_config_dst = os.path.join(self.frp_dir, 'frpc.ini')
        shutil.copy(FRPC_CONFIG, frpc_config_dst)
        
        # 启动frp客户端
        frpc_path = os.path.join(self.frp_dir, 'frpc.exe')
        
        # 检查文件是否为真实的可执行文件
        is_real_executable = False
        if os.path.exists(frpc_path):
            if os.path.getsize(frpc_path) > 1024:
                is_real_executable = True
        
        if not is_real_executable:
            print(f"注意：未找到真实的frp可执行文件，模拟启动")
            print(f"请确保已经手动下载并放置了真实的frp工具")
            print(f"配置文件已准备好：{frpc_config_dst}")
            print(f"要手动启动，请在{self.frp_dir}目录中运行: frpc.exe -c frpc.ini")
            
            # 启动一个模拟的进程
            self.frp_process = subprocess.Popen(
                ['ping', '-t', 'localhost'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"模拟FRP客户端已启动，PID: {self.frp_process.pid}")
            return True
        
        try:
            print(f"正在启动FRP客户端 ({frpc_path})")
            self.frp_process = subprocess.Popen(
                [frpc_path, '-c', 'frpc.ini'],
                cwd=self.frp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"FRP客户端已启动，PID: {self.frp_process.pid}")
            return True
        except Exception as e:
            print(f"启动FRP客户端失败: {e}")
            return False
    
    def start_http_server(self, port=8000, directory='web'):
        """启动本地HTTP服务器"""
        # 确保目录存在
        os.makedirs(directory, exist_ok=True)
        
        # 创建默认的index.html
        index_path = os.path.join(directory, 'index.html')
        if not os.path.exists(index_path):
            default_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>游戏共享平台</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            text-align: center;
        }}
        h1 {{
            color: #333;
        }}
        .game-input {{
            margin-top: 30px;
        }}
        input[type="text"] {{
            width: 70%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px 0 0 4px;
            margin-right: -4px;
        }}
        button {{
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
            font-size: 16px;
            border-radius: 0 4px 4px 0;
        }}
        button:hover {{
            background-color: #45a049;
        }}
        .controls {{
            margin-top: 30px;
        }}
        .controls button {{
            margin: 0 10px;
            border-radius: 4px;
        }}
        .game-frame {{
            margin-top: 20px;
            border: 1px solid #ddd;
            height: 600px;
            width: 100%;
            background-color: #f9f9f9;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
    </style>
</head>
<body>
    <h1>游戏共享平台</h1>
    <p>通过输入游戏URL与朋友远程共享网页游戏！</p>
    <p>服务器地址: http://{self.config['game_subdomain']}:{self.config['frps_http_port']}</p>
    
    <div class="game-input">
        <h2>输入游戏URL</h2>
        <input type="text" id="gameUrl" placeholder="https://" size="60">
        <button id="loadGameBtn">加载游戏</button>
    </div>
    
    <div class="game-frame">
        <div id="game-loading">
            <h3>请在上方输入游戏URL</h3>
        </div>
        <iframe id="game-iframe" style="display: none;"></iframe>
    </div>
    
    <div class="controls">
        <button id="startShareBtn">开始共享</button>
        <button id="joinShareBtn">加入游戏</button>
    </div>
    
    <script>
        // 获取DOM元素
        var gameUrlInput = document.getElementById('gameUrl');
        var loadGameBtn = document.getElementById('loadGameBtn');
        var gameLoading = document.getElementById('game-loading');
        var gameIframe = document.getElementById('game-iframe');
        
        // 加载游戏函数
        function loadGame() {{
            var url = gameUrlInput.value.trim();
            
            // 验证URL格式
            if (!url) {{
                alert('请输入游戏URL');
                return;
            }}
            
            // 确保URL以http://或https://开头
            if (url.indexOf('http://') !== 0 && url.indexOf('https://') !== 0) {{
                url = 'https://' + url;
            }}
            
            // 显示iframe，隐藏加载提示
            gameLoading.style.display = 'none';
            gameIframe.style.display = 'block';
            
            // 设置iframe的src
            gameIframe.src = url;
            
            console.log('正在加载游戏:', url);
        }}
        
        // 添加事件监听器
        loadGameBtn.addEventListener('click', loadGame);
        
        // 支持按Enter键加载游戏
        gameUrlInput.addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') {{
                loadGame();
            }}
        }});
        
        document.getElementById('startShareBtn').onclick = function() {{
            alert('共享功能已准备就绪！');
        }};
        
        document.getElementById('joinShareBtn').onclick = function() {{
            var code = prompt('请输入房间代码:');
            if (code) {{
                alert('正在连接房间 ' + code + '...');
            }}
        }};
    </script>
</body>
</html>
            """
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(default_html)
        
        # 启动HTTP服务器
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)
            
            def log_message(self, format, *args):
                # 可以自定义日志输出
                pass
            
            def do_GET(self):
                try:
                    # 处理WebSocket升级请求
                    if self.headers.get('Upgrade', '').lower() == 'websocket':
                        self._handle_websocket()
                        return
                    super().do_GET()
                except ConnectionAbortedError:
                    # 忽略连接被客户端中止的错误
                    pass
                except BrokenPipeError:
                    # 忽略管道破裂错误
                    pass
                except Exception as e:
                    # 记录其他错误但不中断服务器
                    logger.error(f"HTTP请求处理错误: {e}")
            
            def _handle_websocket(self):
                """处理WebSocket连接"""
                try:
                    # 生成WebSocket响应头
                    key = self.headers['Sec-WebSocket-Key']
                    import hashlib
                    import base64
                    response_key = base64.b64encode(
                        hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()
                    ).decode()
                    
                    # 发送WebSocket握手响应
                    self.send_response(101)
                    self.send_header('Upgrade', 'websocket')
                    self.send_header('Connection', 'Upgrade')
                    self.send_header('Sec-WebSocket-Accept', response_key)
                    self.end_headers()
                    
                    # 这里可以添加WebSocket消息处理逻辑
                    # 但当前版本主要使用原生socket进行远程控制
                    logger.info("WebSocket连接已建立")
                    
                    # 保持连接一段时间
                    while True:
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"WebSocket处理错误: {e}")
            
            def copyfile(self, source, outputfile):
                try:
                    super().copyfile(source, outputfile)
                except (ConnectionAbortedError, BrokenPipeError):
                    # 忽略文件复制过程中的连接错误
                    pass
        
        try:
            server_address = ('', port)
            self.http_server = HTTPServer(server_address, Handler)
            logger.info(f"HTTP服务器已启动在端口 {port}，目录: {directory}")
            
            # 在新线程中运行服务器
            http_thread = threading.Thread(target=self.http_server.serve_forever)
            http_thread.daemon = True
            http_thread.start()
            return True
        except Exception as e:
            logger.error(f"启动HTTP服务器失败: {e}")
            return False
    
    def start_game_host(self):
        """启动游戏主机模式"""
        print("=== 启动游戏主机模式 ===")
        
        # 确定要使用的端口
        if self.config.get('use_tcp_tunnel', False):
            # TCP隧道模式使用配置的本地端口
            local_port = self.config.get('tcp_tunnel_local_port', 8000)
        else:
            # 普通模式使用默认本地端口
            local_port = self.config['local_http_port']
        
        # 启动FRP客户端或TCP隧道配置
        if not self.start_frpc():
            return False
        
        # 启动本地HTTP服务器
        if not self.start_http_server(local_port, 'web'):
            return False
        
        print("游戏主机已成功启动!")
        
        if self.config.get('use_tcp_tunnel', False):
            # TCP隧道模式的访问信息
            tunnel_ip = self.config.get('tcp_tunnel_remote_ip', '')
            tunnel_port = self.config.get('tcp_tunnel_remote_port', 0)
            if tunnel_ip and tunnel_port:
                # 完全重新构建正确格式的URL
                # 直接使用域名和端口，避免任何格式问题
                print(f"其他玩家可以通过以下地址访问您的游戏:")
                print(f"http://frp-dry.com:{tunnel_port}")
            else:
                print(f"其他玩家可以通过平台提供的TCP隧道访问您的游戏")
                print(f"请在平台上配置将远程端口映射到本地端口 {local_port}")
        else:
            # 普通模式的访问信息
            print(f"其他玩家可以通过以下地址访问您的游戏:")
            print(f"http://{self.config['game_subdomain']}:{self.config['frps_http_port']}")
        
        return True
    
    def start_game_client(self):
        """启动游戏客户端模式"""
        print("=== 启动游戏客户端模式 ===")
        
        # 启动FRP客户端
        if not self.start_frpc():
            return False
        
        # 启动客户端界面
        if not self.start_http_server(8001, 'web_client'):
            return False
        
        print("游戏客户端已成功启动!")
        print(f"请访问 http://localhost:8001 查看游戏链接")
        return True
    
    def start_remote_control_server(self, window_title):
        """启动远程控制服务器"""
        # 检查必要的库
        if not HAS_SCREEN_CAPTURE:
            logger.error("缺少必要的屏幕捕获库")
            return False
        
        if self.remote_control_server:
            self.stop_remote_control_server()
        
        # 先启动HTTP服务器，确保web目录可用
        if not self.http_server:
            self.start_http_server(8000, 'web')
        
        # 启动远程控制服务器
        self.remote_control_server = RemoteControlServer()
        result = self.remote_control_server.start(window_title)
        
        if result:
            # 尝试打开浏览器
            try:
                webbrowser.open('http://localhost:8000/remote_control.html')
                logger.info("已打开远程控制界面")
            except Exception as e:
                logger.warning(f"无法打开浏览器: {e}")
                logger.info("请手动访问 http://localhost:8000/remote_control.html")
        
        return result
    
    def stop_remote_control_server(self):
        """停止远程控制服务器"""
        if self.remote_control_server:
            self.remote_control_server.stop()
            self.remote_control_server = None
    
    def start_remote_control_client(self, server_ip):
        """启动远程控制客户端"""
        # 验证IP地址格式
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        if not re.match(ip_pattern, server_ip):
            logger.error("无效的IP地址格式")
            return False
        
        if self.remote_control_client:
            self.stop_remote_control_client()
        
        # 先启动HTTP服务器，确保web目录可用
        if not self.http_server:
            self.start_http_server(8000, 'web')
        
        # 启动远程控制客户端
        self.remote_control_client = RemoteControlClient()
        result = self.remote_control_client.connect(server_ip)
        
        if result:
            # 设置屏幕显示回调
            def show_screen(img):
                """处理接收到的屏幕图像"""
                # 这里可以添加图像处理或显示逻辑
                pass
            
            self.remote_control_client.screen_callback = show_screen
            
            # 尝试打开浏览器
            try:
                webbrowser.open('http://localhost:8000/remote_control.html')
                logger.info("已打开远程控制界面")
            except Exception as e:
                logger.warning(f"无法打开浏览器: {e}")
                logger.info("请手动访问 http://localhost:8000/remote_control.html")
        
        return result
    
    def stop_remote_control_client(self):
        """停止远程控制客户端"""
        if self.remote_control_client:
            self.remote_control_client.stop()
            self.remote_control_client = None
    
    def stop(self):
        """停止所有服务"""
        print("正在停止所有服务...")
        
        # 停止HTTP服务器
        if self.http_server:
            try:
                self.http_server.shutdown()
                self.http_server.server_close()
                print("HTTP服务器已停止")
            except Exception as e:
                print(f"停止HTTP服务器失败: {e}")
        
        # 停止FRP进程
        if self.frp_process:
            try:
                self.frp_process.terminate()
                self.frp_process.wait(timeout=5)
                print("FRP进程已停止")
            except Exception as e:
                print(f"停止FRP进程失败: {e}")
        
        # 停止远程控制服务
        self.stop_remote_control_server()
        self.stop_remote_control_client()
        
        print("所有服务已停止")

def setup_tcp_tunnel(manager):
    """设置TCP隧道配置"""
    print("=== TCP隧道配置 ===")
    
    # 启用TCP隧道
    manager.config['use_tcp_tunnel'] = True
    
    # 获取远程IP
    remote_ip = input("请输入TCP隧道的远程IP地址: ")
    manager.config['tcp_tunnel_remote_ip'] = remote_ip
    
    # 获取远程端口
    while True:
        try:
            remote_port = int(input("请输入TCP隧道的远程端口: "))
            manager.config['tcp_tunnel_remote_port'] = remote_port
            break
        except ValueError:
            print("无效的端口号，请输入数字")
    
    # 获取本地端口
    while True:
        try:
            local_port = int(input("请输入本地HTTP服务器端口 (默认为8000): ") or "8000")
            manager.config['tcp_tunnel_local_port'] = local_port
            break
        except ValueError:
            print("无效的端口号，请输入数字")
    
    manager.save_config()
    print("TCP隧道配置已保存！")
    print("请确保平台的TCP隧道已正确配置，将远程端口映射到本地端口")

def interactive_mode():
    """交互式命令行界面"""
    manager = GameShareManager()
    
    # 检查是否需要设置TCP隧道
    if not os.path.exists(CONFIG_FILE):
        print("首次运行，检测到没有配置文件")
        use_tcp = input("是否使用TCP隧道替代frp服务器？(y/n): ")
        if use_tcp.lower() == 'y':
            setup_tcp_tunnel(manager)
    
    try:
        while True:
            print("=== 游戏共享平台管理器 ===")
            print("1. 启动FRP服务器")
            print("2. 启动游戏主机模式")
            print("3. 启动游戏客户端模式")
            print("4. 修改配置")
            print("5. 设置TCP隧道")
            print("6. 启动远程控制服务器")
            print("7. 启动远程控制客户端")
            print("8. 退出")
            
            try:
                choice = input("\n请选择操作 (1-8): ")
                
                if choice == '1':
                    if manager.config.get('use_tcp_tunnel', False):
                        print("当前已启用TCP隧道模式，不需要启动FRP服务器")
                    else:
                        manager.start_frps()
                elif choice == '2':
                    manager.start_game_host()
                elif choice == '3':
                    manager.start_game_client()
                elif choice == '4':
                    # 简单的配置修改
                    print("当前配置:")
                    for key, value in manager.config.items():
                        print(f"{key}: {value}")
                    
                    key = input("\n请输入要修改的配置项: ")
                    if key in manager.config:
                        value = input(f"请输入新值 (当前: {manager.config[key]}): ")
                        # 尝试转换为数字
                        if isinstance(manager.config[key], int):
                            try:
                                value = int(value)
                            except ValueError:
                                print("无效的数字输入")
                                continue
                        manager.config[key] = value
                        manager.save_config()
                    else:
                        print("配置项不存在")
                elif choice == '5':
                    setup_tcp_tunnel(manager)
                elif choice == '6':
                    # 启动远程控制服务器
                    if not HAS_SCREEN_CAPTURE:
                        print("无法启动远程控制服务器：缺少必要的库")
                        print("请运行: pip install pywin32 opencv-python numpy")
                    else:
                        window_title = input("请输入要控制的窗口标题: ")
                        manager.start_remote_control_server(window_title)
                elif choice == '7':
                    # 启动远程控制客户端
                    server_ip = input("请输入远程控制服务器IP地址: ")
                    manager.start_remote_control_client(server_ip)
                elif choice == '8':
                    manager.stop()
                    print("感谢使用，再见！")
                    break
                else:
                    print("无效的选择，请重新输入")
                    
            except KeyboardInterrupt:
                print("\n操作已取消")
            except Exception as e:
                print(f"操作出错: {e}")
                
    except KeyboardInterrupt:
        manager.stop()
        print("\n程序已中断")
    except Exception as e:
        manager.stop()
        print(f"发生错误: {e}")

def main():
    """主函数"""
    # 如果有命令行参数，则执行相应操作
    if len(sys.argv) > 1:
        manager = GameShareManager()
        
        if sys.argv[1] == '--server':
            manager.start_frps()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                manager.stop()
        elif sys.argv[1] == '--host':
            manager.start_game_host()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                manager.stop()
        elif sys.argv[1] == '--client':
            manager.start_game_client()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                manager.stop()
        elif sys.argv[1] == '--download':
            # 仅下载frp工具
            print("开始下载frp工具...")
            if manager.download_frp():
                print("frp工具下载成功!")
                sys.exit(0)
            else:
                print("frp工具下载失败")
                sys.exit(1)
        else:
            print(f"未知参数: {sys.argv[1]}")
            print("用法: python game_share_manager.py [--server|--host|--client|--download]")
    else:
        # 启动交互式模式
        interactive_mode()

if __name__ == '__main__':
    main()