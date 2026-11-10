@echo off
title Clash of Clans Farming Controller
cd /d "%~dp0"

set "PY_CMD="

REM 1. Check for Python in user's AppData Python bin
if exist "%USERPROFILE%\AppData\Local\Python\bin\python.exe" (
    set "PY_CMD=%USERPROFILE%\AppData\Local\Python\bin\python.exe"
    goto :run
)

REM 2. Check for py launcher
where py >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py"
    goto :run
)

REM 3. Check for standard python in PATH
where python >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :run
)

echo [ERROR] Python was not found on your system!
echo Please make sure Python 3.10+ is installed and in your PATH.
pause
exit /b 1

:run
set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "VECLIB_MAXIMUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"
"%PY_CMD%" -m src.app.main %*
if errorlevel 1 (
    echo.
    echo Bot exited with code %errorlevel%.
    pause
)
