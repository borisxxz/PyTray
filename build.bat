@echo off
rem Build dist\PyTray.exe (single-file, windowed, icon embedded)
setlocal
cd /d "%~dp0"
venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed ^
    --name PyTray --icon PyTray.ico --collect-all customtkinter pytray.py
echo.
echo Done: dist\PyTray.exe
pause
