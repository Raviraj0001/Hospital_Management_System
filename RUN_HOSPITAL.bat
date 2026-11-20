@echo off
setlocal
cd /d "%~dp0"
title Hospital Management Portal

echo.
echo ============================================
echo       HOSPITAL MANAGEMENT PORTAL
echo ============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher was not found. Install Python 3.11 and try again.
    pause
    exit /b 1
)

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
    if errorlevel 1 (
        echo Existing environment is not Python 3.11. Rebuilding it...
        rmdir /s /q venv
    )
)

if not exist "venv\Scripts\python.exe" (
    echo Creating Python 3.11 environment...
    py -3.11 -m venv venv
    if errorlevel 1 (
        echo Could not create the virtual environment. Confirm Python 3.11 is installed.
        pause
        exit /b 1
    )
)

echo Preparing project requirements...
"venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 (
    echo Could not update pip. Check your internet connection.
    pause
    exit /b 1
)

"venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo Dependency installation failed. Check your internet connection and Python 3.11 installation.
    pause
    exit /b 1
)

echo.
echo Starting the hospital portal...
echo Your browser will open after the server is ready.
echo Keep this window open while using the portal.
start "" powershell -NoProfile -WindowStyle Hidden -Command "$end=(Get-Date).AddSeconds(60); do { try { Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8000' -TimeoutSec 2 | Out-Null; Start-Process 'http://127.0.0.1:8000'; exit } catch { Start-Sleep -Seconds 1 } } while ((Get-Date) -lt $end)"
"venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo The server has stopped.
pause
