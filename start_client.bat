@echo off
cls
echo 正在启动游戏客户端模式...
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

REM 创建web_client目录和默认页面
if not exist web_client mkdir web_client
if not exist web_client\index.html (
    echo 创建默认的客户端界面...
    (echo ^<!DOCTYPE html^\>
    echo ^<html^\>
    echo ^<head^\>
    echo     ^<title^>游戏客户端^</title^\>
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
    echo         .join-section {
    echo             margin: 30px auto;
    echo             padding: 20px;
    echo             border: 1px solid #ddd;
    echo             border-radius: 5px;
    echo             max-width: 500px;
    echo         }
    echo         input {
    echo             padding: 10px;
    echo             margin: 10px 0;
    echo             width: 100%;
    echo             box-sizing: border-box;
    echo         }
    echo         button {
    echo             padding: 10px 20px;
    echo             background-color: #2196F3;
    echo             color: white;
    echo             border: none;
    echo             cursor: pointer;
    echo             font-size: 16px;
    echo         }
    echo         button:hover {
    echo             background-color: #1976D2;
    echo         }
    echo     ^</style^\>
    echo ^</head^\>
    echo ^<body^\>
    echo     ^<h1^>游戏客户端^</h1^\>
    echo     ^<p^>连接到远程游戏主机...^</p^\>
    echo     
    echo     ^<div class="join-section"^\>
    echo         ^<h2^>加入游戏房间^</h2^\>
    echo         ^<input type="text" id="hostIpInput" placeholder="输入主机IP地址"^\>
    echo         ^<input type="text" id="roomCodeInput" placeholder="输入房间代码"^\>
    echo         ^<button id="joinBtn"^>加入游戏^</button^\>
    echo     ^</div^\>
    echo     
    echo     ^<div id="statusDisplay" style="margin-top: 20px;"^\>
    echo         ^<p^>等待连接...^</p^\>
    echo     ^</div^\>
    echo     
    echo     ^<script^\>
    echo         document.getElementById('joinBtn').onclick = function() {
    echo             const hostIp = document.getElementById('hostIpInput').value;
    echo             const roomCode = document.getElementById('roomCodeInput').value;
    echo             
    echo             if (hostIp && roomCode) {
    echo                 document.getElementById('statusDisplay').innerHTML = 
    echo                     `^<p^>正在连接到 ${hostIp} 的房间 ${roomCode}...^</p^>`;
    echo                 // 这里会实现实际的连接逻辑
    echo                 alert('连接功能已准备就绪！');
    echo             } else {
    echo                 alert('请输入主机IP和房间代码');
    echo             }
    echo         };
    echo     ^</script^\>
    echo ^</body^\>
    echo ^</html^\>) > web_client\index.html
)

REM 启动游戏客户端
echo 启动游戏客户端中...
python game_share_manager.py --client