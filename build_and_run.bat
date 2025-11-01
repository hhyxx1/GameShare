@echo off

:: 游戏共享平台 - 构建和运行脚本（中文）
:: 此脚本用于一键构建并启动游戏共享平台

cls
echo ====================================
echo     游戏共享平台 - 构建和运行      
echo ====================================

echo 1. 检查环境...

:: 检查Python是否安装
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.6或更高版本
    echo 您可以从 https://www.python.org/ 下载安装
    pause
    exit /b 1
)

echo 2. 下载frp工具...

:: 使用Python脚本下载frp
python game_share_manager.py --download
if %errorlevel% neq 0 (
    echo 警告: 自动下载失败，尝试手动下载...
    
    :: 创建frp目录
    if not exist "frp_windows_amd64" mkdir frp_windows_amd64
    
    echo 请手动下载frp工具并解压到 frp_windows_amd64 目录
    echo 下载地址: https://github.com/fatedier/frp/releases
    pause
)

echo 3. 准备配置文件...

:: 确保配置文件存在
if not exist "frps.ini" (
    echo 创建默认的frps.ini配置文件...
    (echo [common]
    echo bind_port = 7000
    echo vhost_http_port = 8080
    echo use_encryption = true
    echo use_compression = true
    echo log_level = info
    echo log_file = frps.log
    echo token = game_share_secret_token) > frps.ini
)

if not exist "frpc.ini" (
    echo 创建默认的frpc.ini配置文件...
    (echo [common]
    echo server_addr = 127.0.0.1
    echo server_port = 7000
    echo token = game_share_secret_token
    echo use_encryption = true
    echo use_compression = true
    echo log_level = info
    echo log_file = frpc.log
    echo [game_http]
    echo type = http
    echo local_ip = 127.0.0.1
    echo local_port = 8000
    echo subdomain = game
    echo [game_control]
    echo type = http
    echo local_ip = 127.0.0.1
    echo local_port = 8088
    echo custom_domains = 127.0.0.1
    echo locations = /control) > frpc.ini
)

echo 4. 构建完成!

echo.
echo ====================================
echo 请选择要启动的服务：
echo 1. 启动frp服务器
 echo 2. 启动游戏主机（作为游戏房主）
echo 3. 启动游戏客户端（加入他人的游戏）
echo 4. 退出
 echo ====================================

set /p choice=请输入选择 (1-4): 

if "%choice%" == "1" (
    echo 启动frp服务器...
    call start_frps.bat
)
else if "%choice%" == "2" (
    echo 启动游戏主机...
    call start_game_host.bat
)
else if "%choice%" == "3" (
    echo 启动游戏客户端...
    call start_game_client.bat
)
else if "%choice%" == "4" (
    echo 退出程序
    exit /b 0
)
else (
    echo 无效的选择
    pause
    exit /b 1
)