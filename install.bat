@echo off
title CoC Farm Controller - 1-Click Installer & Setup
cd /d "%~dp0"

echo ================================================================
echo    Clash of Clans Autonomous Farm Controller - Setup & Install
echo ================================================================
echo.

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10, 3.11, or 3.12 from https://www.python.org/
    echo Make sure to check 'Add python.exe to PATH' during installation.
    echo.
    pause
    exit /b 1
)
python --version

echo.
echo [2/3] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [3/3] Installing all required dependencies from requirements.txt...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Some packages failed to install. Retrying with basic dependencies...
    python -m pip install customtkinter pillow opencv-python numpy easyocr ultralytics pydantic pyyaml pyautogui pygetwindow keyboard mss pywin32
)

echo.
echo ================================================================
echo   INSTALLATION COMPLETED SUCCESSFULLY!
echo.
echo   To launch the Farming Controller, double-click 'run_coc_bot.bat'
echo   or run: python -m src.app.main
echo ================================================================
echo.
pause
