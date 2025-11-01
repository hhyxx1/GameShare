@echo off
cls
echo 正在启动FRP服务器...
echo ====================

REM 检查Python是否安装
python --version >nul 2>nul
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.6或更高版本
    echo 您可以从 https://www.python.org/ 下载安装
    pause
    exit /b 1
)

REM 创建默认配置文件（如果不存在）
if not exist frps.ini (
    echo 创建frps.ini配置文件...
    (echo [common]
    echo bind_port = 7000
    echo vhost_http_port = 8080
    echo use_encryption = true
    echo use_compression = true
    echo log_level = info
    echo log_file = frps.log
    echo token = game_share_secret_token) > frps.ini
)

REM 启动FRP服务器
echo 启动FRP服务器中...
python game_share_manager.py --server