@echo off

:: 游戏共享平台 - 游戏客户端启动脚本
:: 此脚本用于连接到游戏主机

cls
echo ====================================
echo      游戏共享平台 - 游戏客户端      
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

:: 检查frpc.ini文件是否存在
if not exist "frpc.ini" (
    echo 错误: 未找到frpc.ini配置文件
    echo 请确保配置文件存在并正确配置frp服务器地址
    pause
    exit /b 1
)

:: 复制配置文件到frp目录
copy frpc.ini frp_windows_amd64\ /Y >nul

:: 创建web_client目录
if not exist "web_client" mkdir web_client

:: 复制index.html到web_client目录
copy index.html web_client\ /Y >nul

:: 启动客户端HTTP服务器
echo 正在启动客户端HTTP服务器...
python -m http.server 8001 --directory web_client >nul 2>nul &

:: 启动frp客户端
echo 正在启动frp客户端...
echo 配置文件: frpc.ini
echo. 
echo 按 Ctrl+C 停止服务

cd frp_windows_amd64
start cmd /k "frpc.exe -c frpc.ini"

:: 等待frp启动
sleep 2

:: 在默认浏览器中打开客户端页面
echo 正在打开游戏客户端页面...
start http://localhost:8001

echo 游戏客户端已启动，请保持此窗口打开
echo 请在打开的页面中输入房间ID加入游戏
echo. 
pause