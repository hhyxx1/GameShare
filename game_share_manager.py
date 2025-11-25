#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏共享平台管理器 - 重构版本

统一管理游戏共享功能，支持游戏主机模式和游戏客户端模式，
通过第三方FRP服务器实现内网穿透。
"""

import os
import sys
import json
import time
import socket
import subprocess
import threading
import argparse
import http.server
import socketserver
import urllib.request

# 配置常量
DEFAULT_CONFIG = {
    'local_http_port': 8000,
    'remote_control_port': 8888,
    'use_tcp_tunnel': True,
    'remote_frp_server': 'frp-dry.com',
    'remote_frp_port': 49867,
    'frp_token': 'game_share_secret_token'
}

# 工具类
class Logger:
    """日志记录器"""
    
    @staticmethod
    def log(message, level='INFO'):
        """记录日志"""
        print(f"[{level}] {message}")
    
    @staticmethod
    def info(message):
        Logger.log(message, 'INFO')
    
    @staticmethod
    def error(message):
        Logger.log(message, 'ERROR')
    
    @staticmethod
    def success(message):
        Logger.log(f"✅ {message}", 'SUCCESS')

class PortChecker:
    """端口检查器"""
    
    @staticmethod
    def is_port_in_use(port):
        """检查端口是否被占用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    @staticmethod
    def find_available_port(start_port=8000, max_attempts=10):
        """查找可用端口"""
        for port in range(start_port, start_port + max_attempts):
            if not PortChecker.is_port_in_use(port):
                return port
        return None

class ConfigManager:
    """配置管理器"""
    
    @staticmethod
    def load_config(config_file='config.json'):
        """加载配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            Logger.error(f"配置文件不存在或格式错误，使用默认配置")
            return DEFAULT_CONFIG.copy()
    
    @staticmethod
    def save_config(config, config_file='config.json'):
        """保存配置"""
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            Logger.success(f"配置已保存到 {config_file}")
        except Exception as e:
            Logger.error(f"保存配置失败: {str(e)}")

class FRPManager:
    """FRP 管理器（仅客户端功能）"""
    
    def __init__(self, config):
        self.config = config
        self.frp_dir = 'frp_windows_amd64'
        self.frpc_path = os.path.join(self.frp_dir, 'frpc.exe')
    
    def create_frpc_config(self, local_port):
        """创建FRP客户端配置"""
        config_content = f"""
[common]
server_addr = {self.config['remote_frp_server']}
server_port = {self.config['remote_frp_port']}
token = {self.config['frp_token']}

[web]
type = http
local_port = {local_port}
custom_domains = {self.config['remote_frp_server']}
        """
        
        with open(os.path.join(self.frp_dir, 'frpc.ini'), 'w', encoding='utf-8') as f:
            f.write(config_content.strip())
        return os.path.join(self.frp_dir, 'frpc.ini')
    
    def start_frp_client(self, local_port):
        """启动FRP客户端"""
        if not os.path.exists(self.frpc_path):
            Logger.error("FRP客户端文件不存在，请先下载FRP工具")
            return None
        
        config_path = self.create_frpc_config(local_port)
        Logger.info(f"启动FRP客户端，配置文件: {config_path}")
        
        try:
            process = subprocess.Popen(
                [self.frpc_path, '-c', config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 检查是否成功启动
            time.sleep(1)
            if process.poll() is None:
                Logger.success("FRP客户端已启动")
                return process
            else:
                Logger.error("FRP客户端启动失败")
                return None
        except Exception as e:
            Logger.error(f"启动FRP客户端出错: {str(e)}")
            return None
    
    @staticmethod
    def download_frp():
        """下载FRP工具"""
        url = 'https://github.com/fatedier/frp/releases/download/v0.38.0/frp_0.38.0_windows_amd64.zip'
        output_file = 'frp.zip'
        
        Logger.info(f"正在下载FRP工具: {url}")
        
        try:
            urllib.request.urlretrieve(url, output_file)
            Logger.success(f"FRP工具已下载到: {output_file}")
            
            # 简单提示用户手动解压
            Logger.info("请手动解压 frp.zip 文件到 frp_windows_amd64 目录")
        except Exception as e:
            Logger.error(f"下载FRP工具失败: {str(e)}")

class HTTPServerManager:
    """HTTP服务器管理器"""
    
    @staticmethod
    def start_http_server(port=8000, directory='web'):
        """启动HTTP服务器"""
        # 检查端口是否被占用
        if PortChecker.is_port_in_use(port):
            Logger.error(f"端口 {port} 已被占用，尝试查找可用端口...")
            available_port = PortChecker.find_available_port(port)
            if available_port:
                port = available_port
                Logger.info(f"切换到可用端口: {port}")
            else:
                Logger.error("无法找到可用端口")
                return None
        
        # 检查目录是否存在
        if not os.path.exists(directory):
            Logger.error(f"目录不存在: {directory}")
            return None
        
        # 切换到web目录
        original_dir = os.getcwd()
        os.chdir(directory)
        
        try:
            handler = http.server.SimpleHTTPRequestHandler
            httpd = socketserver.TCPServer(("0.0.0.0", port), handler)
            
            Logger.success(f"HTTP服务器已启动在端口 {port}")
            Logger.info(f"本地访问地址: http://localhost:{port}")
            
            # 在新线程中启动服务器
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            return httpd
        except Exception as e:
            Logger.error(f"启动HTTP服务器出错: {str(e)}")
            return None
        finally:
            # 恢复原始目录
            os.chdir(original_dir)

class RemoteControlServer:
    """远程控制服务器"""
    
    def __init__(self, config):
        self.config = config
        self.server = None
    
    def start(self):
        """启动远程控制服务器"""
        port = self.config.get('remote_control_port', 8888)
        Logger.info(f"启动远程控制服务器，端口: {port}")
        
        # 这里可以扩展更复杂的远程控制功能
        # 目前使用简单的HTTP服务器提供远程控制页面
        self.server = HTTPServerManager.start_http_server(port, 'web')
        return self.server

class GameShareManager:
    """游戏共享管理器"""
    
    def __init__(self):
        self.config = ConfigManager.load_config()
        self.frp_manager = FRPManager(self.config)
        self.http_server = None
        self.frp_process = None
        self.remote_control_server = RemoteControlServer(self.config)
    
    def start_game_host(self):
        """启动游戏主机模式"""
        Logger.info("=== 启动游戏主机模式 ===")
        
        # 确定使用的端口
        port = self.config['local_http_port']
        Logger.info(f"将使用端口: {port}")
        
        # 如果启用了TCP隧道，启动FRP客户端
        if self.config['use_tcp_tunnel']:
            Logger.info("启用TCP隧道模式")
            self.frp_process = self.frp_manager.start_frp_client(port)
            if not self.frp_process:
                Logger.error("FRP客户端启动失败，无法使用远程访问功能")
            
            remote_url = f"http://{self.config['remote_frp_server']}:{self.config['remote_frp_port']}"
            Logger.info(f"远程访问地址: {remote_url}")
        
        # 启动HTTP服务器
        Logger.info("启动HTTP服务器...")
        self.http_server = HTTPServerManager.start_http_server(port, 'web')
        
        if self.http_server:
            Logger.success("游戏主机已成功启动!")
            Logger.info("按Ctrl+C退出")
            return True
        else:
            Logger.error("启动游戏主机失败")
            return False
    
    def start_game_client(self):
        """启动游戏客户端模式"""
        Logger.info("=== 启动游戏客户端模式 ===")
        
        # 使用不同的端口避免冲突
        port = 8001
        Logger.info(f"将使用端口: {port}")
        
        # 启动HTTP服务器提供客户端页面
        Logger.info("启动游戏客户端...")
        self.http_server = HTTPServerManager.start_http_server(port, 'web')
        
        if self.http_server:
            Logger.success("游戏客户端已成功启动!")
            Logger.info("按Ctrl+C退出")
            return True
        else:
            Logger.error("启动游戏客户端失败")
            return False
    
    def start_remote_control(self):
        """启动远程控制服务器"""
        Logger.info("=== 启动远程控制服务器 ===")
        
        # 启动远程控制服务器
        self.server = self.remote_control_server.start()
        
        if self.server:
            Logger.success("远程控制服务器已成功启动!")
            Logger.info(f"访问地址: http://localhost:{self.config['remote_control_port']}")
            Logger.info("按Ctrl+C退出")
            return True
        else:
            Logger.error("启动远程控制服务器失败")
            return False
    
    def download_frp_tools(self):
        """下载FRP工具"""
        self.frp_manager.download_frp()
    
    def stop(self):
        """停止所有服务"""
        Logger.info("正在停止服务...")
        
        # 停止HTTP服务器
        if self.http_server:
            try:
                self.http_server.shutdown()
                Logger.info("HTTP服务器已停止")
            except:
                pass
        
        # 停止FRP进程
        if self.frp_process:
            try:
                self.frp_process.terminate()
                Logger.info("FRP进程已停止")
            except:
                pass
        
        Logger.success("所有服务已停止")

# 主函数
def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='游戏共享平台管理器')
    parser.add_argument('--host', action='store_true', help='启动游戏主机模式')
    parser.add_argument('--client', action='store_true', help='启动游戏客户端模式')
    parser.add_argument('--download', action='store_true', help='下载FRP工具')
    parser.add_argument('--remote', action='store_true', help='启动远程控制服务器')
    
    args = parser.parse_args()
    
    manager = GameShareManager()
    
    try:
        # 根据参数执行相应操作
        if args.host:
            success = manager.start_game_host()
        elif args.client:
            success = manager.start_game_client()
        elif args.download:
            manager.download_frp_tools()
            success = True
        elif args.remote:
            success = manager.start_remote_control()
        else:
            # 默认显示帮助信息
            parser.print_help()
            success = False
        
        # 如果启动了服务，保持程序运行
        if success and not args.download:
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                Logger.info("收到中断信号，正在退出...")
    finally:
        # 停止所有服务
        manager.stop()

if __name__ == '__main__':
    # 确保中文显示正常
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
    
    main()
