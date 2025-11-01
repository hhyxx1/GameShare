# Game Share Platform - PowerShell Starter Script
# This script is designed to work in PowerShell environment

Clear-Host
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "     Game Share Platform Starter   " -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

Write-Host "1. Checking environment..." -ForegroundColor Green

# Check if Python is installed
Try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} Catch {
    Write-Host "Error: Python not found. Please install Python 3.6 or higher." -ForegroundColor Red
    Write-Host "You can download from https://www.python.org/" -ForegroundColor Red
    Pause
    exit 1
}

# Create necessary directories
Write-Host "2. Setting up environment..." -ForegroundColor Green
New-Item -ItemType Directory -Path "web" -Force | Out-Null
New-Item -ItemType Directory -Path "web_client" -Force | Out-Null

# Create frps.ini if not exists
if (-not (Test-Path "frps.ini")) {
    Write-Host "Creating frps.ini configuration file..." -ForegroundColor Yellow
    @"
[common]
bind_port = 7000
vhost_http_port = 8080
use_encryption = true
use_compression = true
log_level = info
log_file = frps.log
token = game_share_secret_token
"@ | Set-Content -Path "frps.ini"
}

# Create frpc.ini if not exists
if (-not (Test-Path "frpc.ini")) {
    Write-Host "Creating frpc.ini configuration file..." -ForegroundColor Yellow
    @"
[common]
server_addr = 127.0.0.1
server_port = 7000
token = game_share_secret_token
use_encryption = true
use_compression = true
log_level = info
log_file = frpc.log

[game_http]
type = http
local_ip = 127.0.0.1
local_port = 8000
subdomain = game

[game_control]
type = http
local_ip = 127.0.0.1
local_port = 8088
custom_domains = 127.0.0.1
locations = /control
"@ | Set-Content -Path "frpc.ini"
}

# Create default index.html
if (-not (Test-Path "web\index.html")) {
    Write-Host "Creating default web interface..." -ForegroundColor Yellow
    @"
<!DOCTYPE html>
<html>
<head>
    <title>Game Share Platform</title>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            text-align: center;
        }
        h1 {
            color: #333;
        }
        .game-list {
            margin-top: 30px;
        }
        .game-item {
            border: 1px solid #ddd;
            padding: 15px;
            margin: 10px 0;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .game-item:hover {
            background-color: #f5f5f5;
        }
        .controls {
            margin-top: 30px;
        }
        button {
            padding: 10px 20px;
            margin: 0 10px;
            background-color: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <h1>Game Share Platform</h1>
    <p>Share web games with friends remotely!</p>
    
    <div class="game-list">
        <h2>Popular Games</h2>
        <div class="game-item" onclick="window.open('https://www.4399.com/flash/133663_2.htm', '_blank')">双人森林冰火人</div>
        <div class="game-item" onclick="window.open('https://www.4399.com/flash/133656_2.htm', '_blank')">双人坦克大战</div>
        <div class="game-item" onclick="window.open('https://www.4399.com/flash/133662_2.htm', '_blank')">双人黄金矿工</div>
    </div>
    
    <div class="controls">
        <button id="startShareBtn">Start Sharing</button>
        <button id="joinShareBtn">Join Game</button>
    </div>
    
    <script>
        document.getElementById('startShareBtn').onclick = function() {
            alert('Share functionality is ready!');
        };
        document.getElementById('joinShareBtn').onclick = function() {
            const code = prompt('Please enter room code:');
            if (code) {
                alert(`Connecting to room ${code}...`);
            }
        };
    </script>
</body>
</html>
"@ | Set-Content -Path "web\index.html"
}

Write-Host "3. Setup complete!" -ForegroundColor Green

# Display menu
Write-Host "`n====================================" -ForegroundColor Cyan
Write-Host "Please select service to start:" -ForegroundColor Cyan
Write-Host "1. Start frp server" -ForegroundColor Cyan
Write-Host "2. Start game host" -ForegroundColor Cyan
Write-Host "3. Start game client" -ForegroundColor Cyan
Write-Host "4. Exit" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

# Get user choice
$choice = Read-Host "Enter your choice (1-4)"

# Handle user choice
if ($choice -eq "1") {
    Write-Host "Starting frp server..." -ForegroundColor Green
    # Start frp server
    python game_share_manager.py --server
} elseif ($choice -eq "2") {
    Write-Host "Starting game host..." -ForegroundColor Green
    # Start game host
    python game_share_manager.py --host
} elseif ($choice -eq "3") {
    Write-Host "Starting game client..." -ForegroundColor Green
    # Start game client
    python game_share_manager.py --client
} elseif ($choice -eq "4") {
    Write-Host "Exiting program" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Invalid selection" -ForegroundColor Red
    Pause
    exit 1
}