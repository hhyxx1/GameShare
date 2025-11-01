@echo off

:: 游戏共享平台 - frp服务器启动脚本
:: 此脚本用于启动frp服务器

cls
echo ====================================
echo      游戏共享平台 - FRP服务器      
echo ====================================

:: 检查Python是否安装
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.6或更高版本
    echo 您可以从 https://www.python.org/ 下载安装
    pause
    exit /b 1
)

:: 检查frp是否已下载，如果没有则下载
if not exist "frp_windows_amd64" (
    echo 正在启动游戏共享平台管理器来下载frp...
    python game_share_manager.py --download
    if %errorlevel% neq 0 (
        echo 错误: 下载frp失败
        pause
        exit /b 1
    )
)

:: 检查frps.ini文件是否存在
if not exist "frps.ini" (
    echo 错误: 未找到frps.ini配置文件
    echo 请确保配置文件存在
    pause
    exit /b 1
)

:: 复制配置文件到frp目录
copy frps.ini frp_windows_amd64\ /Y >nul

:: 启动frp服务器
echo 正在启动frp服务器...
echo 配置文件: frps.ini
echo 服务器控制面板地址: http://127.0.0.1:7500
echo 用户名: admin, 密码: admin
echo. 
echo 按 Ctrl+C 停止服务器

cd frp_windows_amd64
start cmd /k "frps.exe -c frps.ini"

:: 等待frp启动
sleep 2

:: 在默认浏览器中打开控制面板
echo 正在打开frp控制面板...
start http://127.0.0.1:7500

cd ..
echo 服务器已启动，请保持此窗口打开
pause