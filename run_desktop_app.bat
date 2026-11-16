@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Checking for updates...
git pull --ff-only

if errorlevel 1 (
    echo Failed to update repository.
    pause
    exit /b 1
)

echo Starting application...
"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%desktop_app.py"

if errorlevel 1 pause