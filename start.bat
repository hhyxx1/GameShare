@echo off
cls
echo ====================================
echo      游戏共享平台 - 统一启动器
====================================
echo 1. 启动服务器模式
 echo 2. 启动游戏主机模式
 echo 3. 启动游戏客户端模式
 echo 4. 下载FRP工具
====================================

set /p choice=请选择操作 (1-4): 

if "%choice%" == "1" (
    echo 正在启动服务器模式...
    python game_share_manager.py --server
) else if "%choice%" == "2" (
    echo 正在启动游戏主机模式...
    python game_share_manager.py --host
) else if "%choice%" == "3" (
    echo 正在启动游戏客户端模式...
    python game_share_manager.py --client
) else if "%choice%" == "4" (
    echo 正在下载FRP工具...
    python game_share_manager.py --download
) else (
    echo 无效选择！
    pause
    exit /b 1
)

pause