@echo off
setlocal
cd /d "%~dp0.."

where py >nul 2>&1
if %errorlevel%==0 (
    py app\launcher\launcher.py
    exit /b %errorlevel%
)

where python >nul 2>&1
if %errorlevel%==0 (
    python app\launcher\launcher.py
    exit /b %errorlevel%
)

echo Python 3.11+ was not found.
echo Install Python from https://www.python.org/downloads/ and run this file again.
pause
exit /b 1
