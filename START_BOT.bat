@echo off
chcp 65001 >nul
title ISSSSMAIL Scalper Bot

echo.
echo ============================================================
echo   ISSSSMAIL SCALPER BOT  - Gold + Bitcoin
echo   بوت تداول الذهب والبيتكوين
echo ============================================================
echo.

REM Change to project directory
cd /d "%~dp0"

REM Check if MT5 is configured
echo [1/2] Checking Python environment...
python --version
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

echo.
echo [2/2] Starting ISSSSMAIL Bot API Server...
echo.
echo Dashboard: Open dashboard.html in Antigravity side pane
echo API:       http://127.0.0.1:8765
echo.
echo Press Ctrl+C to stop the bot server
echo ============================================================
echo.

REM Open dashboard in browser after 2 seconds
timeout /t 2 /nobreak >nul
start "" "C:\Users\hassa\.gemini\antigravity\brain\02e71f78-e23d-4289-9b44-7b339e201ce9\dashboard.html"

python main.py

pause
