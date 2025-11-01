@echo off
cls
echo 正在启动游戏主机模式...
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
if not exist frpc.ini (
    echo 创建frpc.ini配置文件...
    (echo [common]
    echo server_addr = 127.0.0.1
    echo server_port = 7000
    echo token = game_share_secret_token
    echo use_encryption = true
    echo use_compression = true
    echo log_level = info
    echo log_file = frpc.log
    echo.
    echo [game_http]
    echo type = http
    echo local_ip = 127.0.0.1
    echo local_port = 8000
    echo subdomain = game
    echo.
    echo [game_control]
    echo type = http
    echo local_ip = 127.0.0.1
    echo local_port = 8088
    echo custom_domains = 127.0.0.1
    echo locations = /control) > frpc.ini
)

REM 创建web目录和默认页面
if not exist web mkdir web
if not exist web\index.html (
    echo 创建默认的Web界面...
    (echo ^<!DOCTYPE html^\>
    echo ^<html^\>
    echo ^<head^\>
    echo     ^<title^>游戏共享平台^</title^\>
    echo     ^<meta charset="UTF-8"^\>
    echo     ^<style^\>
    echo         body {
    echo             font-family: Arial, sans-serif;
    echo             max-width: 800px;
    echo             margin: 0 auto;
    echo             padding: 20px;
    echo             text-align: center;
    echo         }
    echo         h1 {
    echo             color: #333;
    echo         }
    echo         .game-list {
    echo             margin-top: 30px;
    echo         }
    echo         .game-item {
    echo             border: 1px solid #ddd;
    echo             padding: 15px;
    echo             margin: 10px 0;
    echo             cursor: pointer;
    echo             transition: background-color 0.3s;
    echo         }
    echo         .game-item:hover {
    echo             background-color: #f5f5f5;
    echo         }
    echo         .controls {
    echo             margin-top: 30px;
    echo         }
    echo         button {
    echo             padding: 10px 20px;
    echo             margin: 0 10px;
    echo             background-color: #4CAF50;
    echo             color: white;
    echo             border: none;
    echo             cursor: pointer;
    echo             font-size: 16px;
    echo         }
    echo         button:hover {
    echo             background-color: #45a049;
    echo         }
    echo     ^</style^\>
    echo ^</head^\>
    echo ^<body^\>
    echo     ^<h1^>游戏共享平台^</h1^\>
    echo     ^<p^>远程与朋友共享网页游戏！^</p^\>
    echo     
    echo     ^<div class="game-list"^\>
    echo         ^<h2^>热门游戏^</h2^\>
    echo         ^<div class="game-item" onclick="window.open('https://www.4399.com/flash/133663_2.htm', '_blank')"^>双人森林冰火人^</div^\>
    echo         ^<div class="game-item" onclick="window.open('https://www.4399.com/flash/133656_2.htm', '_blank')"^>双人坦克大战^</div^\>
    echo         ^<div class="game-item" onclick="window.open('https://www.4399.com/flash/133662_2.htm', '_blank')"^>双人黄金矿工^</div^\>
    echo     ^</div^\>
    echo     
    echo     ^<div class="controls"^\>
    echo         ^<button id="startShareBtn"^>开始共享^</button^\>
    echo         ^<button id="joinShareBtn"^>加入游戏^</button^\>
    echo     ^</div^\>
    echo     
    echo     ^<script^\>
    echo         document.getElementById('startShareBtn').onclick = function() {
    echo             alert('共享功能已准备就绪！');
    echo         };
    echo         document.getElementById('joinShareBtn').onclick = function() {
    echo             const code = prompt('请输入房间代码:');
    echo             if (code) {
    echo                 alert(`正在连接房间 ${code}...`);
    echo             }
    echo         };
    echo     ^</script^\>
    echo ^</body^\>
    echo ^</html^\>) > web\index.html
)

REM 启动游戏主机
echo 启动游戏主机中...
python game_share_manager.py --host