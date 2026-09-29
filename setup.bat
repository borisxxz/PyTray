@echo off
rem PyTray first-time setup: venv + deps + hotkey probe
setlocal
cd /d "%~dp0"

set PY=C:\Python313\python.exe
if not exist "%PY%" set PY=python

echo [1/3] Creating virtual environment "venv" ...
if exist venv\Scripts\python.exe (
    echo       venv already exists, skip.
) else (
    "%PY%" -m venv venv
    if errorlevel 1 goto :fail
)

echo [2/3] Installing dependencies: pystray / pillow / keyboard / customtkinter ...
venv\Scripts\python.exe -m pip install --upgrade pip -q
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [3/3] Probing default hotkey "alt+shift+f9" and "ctrl+alt+down" ...
venv\Scripts\python.exe check_hotkey.py alt+shift+f9 ctrl+alt+down

echo.
echo ==========================================================
echo  Setup finished.  Next: double-click  start.bat
echo ==========================================================
pause
exit /b 0

:fail
echo.
echo  *** Setup FAILED. Read the messages above. ***
pause
exit /b 1
