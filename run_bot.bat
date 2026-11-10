@echo off
title Clash of Clans Farming Controller
cd /d "%~dp0"

echo =====================================================================
echo  Clash of Clans Autonomous Farming Controller - Setup & Launcher
echo =====================================================================
echo.

set "PY_CMD="

REM 1. Check for standard python in PATH
where python >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :check_dependencies
)

REM 2. Check for py launcher
where py >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py"
    goto :check_dependencies
)

REM 3. Check for Python in user's AppData Python bin
if exist "%USERPROFILE%\AppData\Local\Python\bin\python.exe" (
    set "PY_CMD=%USERPROFILE%\AppData\Local\Python\bin\python.exe"
    goto :check_dependencies
)

echo [ERROR] Python was not found on your system!
echo Please download and install Python 3.10+ from https://www.python.org/
echo (Important: Be sure to check the box "Add Python to PATH" during installation)
echo.
pause
exit /b 1

:check_dependencies
echo [1/2] Verifying Python environment...
REM Check if core dependencies are installed (e.g. customtkinter, cv2, mss)
"%PY_CMD%" -c "import customtkinter, cv2, mss, rapidocr_onnxruntime, yaml" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [*] Required packages are missing. Installing dependencies automatically...
    echo     Running: %PY_CMD% -m pip install -r requirements.txt
    echo.
    "%PY_CMD%" -m pip install --upgrade pip >nul 2>&1
    "%PY_CMD%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install dependencies!
        echo Please check your internet connection and try running:
        echo   pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo [*] Dependencies installed successfully!
) else (
    echo [*] All core dependencies are verified.
)

echo.
echo [2/2] Launching Clash of Clans Farming Dashboard...

set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "VECLIB_MAXIMUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"

"%PY_CMD%" -m src.app.main %*
if errorlevel 1 (
    echo.
    echo [!] Bot exited with code %errorlevel%.
    pause
)
