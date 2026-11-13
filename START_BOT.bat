@echo off
title ISSSSMAIL Scalper Bot v2.1
color 0A
echo ============================================================
echo   ISSSSMAIL SCALPER BOT v2.1 - SMART EDITION
echo   Gold + Bitcoin - Multi-Indicator Confluence System
echo ============================================================
echo.
echo [*] Starting bot server...

cd /d "%~dp0"

REM Kill any existing instance on port 8765
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

timeout /t 2 /nobreak >nul

REM Start bot in background
start /B pythonw main.py

echo [*] Waiting for server to start...
timeout /t 5 /nobreak >nul

REM Open dashboard in default browser
start "" "dashboard.html"

echo.
echo [OK] Bot is running! Dashboard opened in browser.
echo [OK] Press any key to stop the bot and exit.
echo.
pause >nul

REM Kill bot on exit
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo [STOPPED] Bot stopped. Goodbye!
