@echo off

:: Game Sharing Platform - Build and Run Script (English)
:: This script is used to build and start the game sharing platform with one click

cls
echo ====================================
echo      Game Sharing Platform         
echo        Build and Run              
echo ====================================

echo 1. Checking environment...

:: Check if Python is installed
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python 3.6 or higher first.
    echo You can download it from https://www.python.org/
    pause
    exit /b 1
)

echo 2. Downloading frp tools...

:: Use Python script to download frp
python game_share_manager.py --download
if %errorlevel% neq 0 (
    echo Warning: Auto-download failed. Trying manual download...
    
    :: Create frp directory
    if not exist "frp_windows_amd64" mkdir frp_windows_amd64
    
    echo Please manually download frp tools and extract them to frp_windows_amd64 directory
    echo Download URL: https://github.com/fatedier/frp/releases
    pause
)

echo 3. Preparing configuration files...

:: Ensure configuration files exist
if not exist "frps.ini" (
    echo Creating default frps.ini configuration file...
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
    echo Creating default frpc.ini configuration file...
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

echo 4. Build completed!

echo.
echo ====================================
echo Please select the service to start:
echo 1. Start frp server
 echo 2. Start game host (as room owner)
echo 3. Start game client (join others' game)
echo 4. Exit
 echo ====================================

set /p choice=Please enter your choice (1-4): 

if "%choice%" == "1" (
    echo Starting frp server...
    call start_frps.bat
)
else if "%choice%" == "2" (
    echo Starting game host...
    call start_game_host.bat
)
else if "%choice%" == "3" (
    echo Starting game client...
    call start_game_client.bat
)
else if "%choice%" == "4" (
    echo Exiting program
    exit /b 0
)
else (
    echo Invalid choice
    pause
    exit /b 1
)