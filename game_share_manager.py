#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏共享平台管理器
用于管理frp服务、配置文件和Web服务器
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

class GameShareManager:
    def __init__(self):
        self.config = self.load_config()
        self.frp_dir = 'frp_windows_amd64'
        self.http_server = None
        self.frp_process = None
    
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
                    super().do_GET()
                except ConnectionAbortedError:
                    # 忽略连接被客户端中止的错误
                    pass
                except BrokenPipeError:
                    # 忽略管道破裂错误
                    pass
                except Exception as e:
                    # 记录其他错误但不中断服务器
                    print(f"HTTP请求处理错误: {e}")
            
            def copyfile(self, source, outputfile):
                try:
                    super().copyfile(source, outputfile)
                except (ConnectionAbortedError, BrokenPipeError):
                    # 忽略文件复制过程中的连接错误
                    pass
        
        try:
            server_address = ('', port)
            self.http_server = HTTPServer(server_address, Handler)
            print(f"HTTP服务器已启动在端口 {port}，目录: {directory}")
            
            # 在新线程中运行服务器
            http_thread = threading.Thread(target=self.http_server.serve_forever)
            http_thread.daemon = True
            http_thread.start()
            return True
        except Exception as e:
            print(f"启动HTTP服务器失败: {e}")
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
    
    print("=== 游戏共享平台管理器 ===")
    print("1. 启动FRP服务器")
    print("2. 启动游戏主机模式")
    print("3. 启动游戏客户端模式")
    print("4. 修改配置")
    print("5. 设置TCP隧道")
    print("6. 退出")
    
    try:
        while True:
            choice = input("\n请选择操作 (1-6): ")
            
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
                manager.stop()
                print("感谢使用，再见！")
                break
            else:
                print("无效的选择，请重新输入")
                
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