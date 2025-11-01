@echo off
cls

echo =========================================
echo       游戏共享平台 - TCP隧道模式
=========================================
echo 此脚本将帮助您配置并启动TCP隧道模式的游戏主机

echo.
echo 请确保您已在平台上设置好TCP隧道
set /p confirm="是否已设置好TCP隧道？(y/n): "
if /i "%confirm%" neq "y" (
    echo 请先在平台上配置TCP隧道，然后再运行此脚本
    pause
    exit /b
)

rem 创建TCP隧道配置文件（如果不存在）
if not exist config.json (
    echo 创建TCP隧道配置...
    echo {> config.json
    echo   "use_tcp_tunnel": true,>> config.json
    
    set /p remote_ip="请输入TCP隧道的远程IP地址: "
    echo   "tcp_tunnel_remote_ip": "%remote_ip%",>> config.json
    
    set /p remote_port="请输入TCP隧道的远程端口: "
    echo   "tcp_tunnel_remote_port": %remote_port%,>> config.json
    
    set /p local_port="请输入本地HTTP服务器端口 (默认为8000): "
    if "%local_port%" equ "" set local_port=8000
    echo   "tcp_tunnel_local_port": %local_port%,>> config.json
    
    rem 添加默认配置项
    echo   "frps_server_ip": "127.0.0.1",>> config.json
    echo   "frps_bind_port": 7000,>> config.json
    echo   "frps_http_port": 8080,>> config.json
    echo   "frps_dashboard_port": 7500,>> config.json
    echo   "frps_token": "game_share_secret_token",>> config.json
    echo   "local_http_port": 8000,>> config.json
    echo   "local_webrtc_port": 8088,>> config.json
    echo   "game_subdomain": "game",>> config.json
    echo   "frp_version": "v0.44.0",>> config.json
    echo   "frp_download_url": "https://github.com/fatedier/frp/releases/download/">> config.json
    echo }>> config.json
    echo 配置已保存！
)

echo.
echo 启动游戏共享平台 - TCP隧道模式...
python game_share_manager.py --host

pause