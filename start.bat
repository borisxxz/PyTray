@echo off
rem Launch PyTray. Optional hotkey arg overrides saved settings once.
rem Prefer double-clicking PyTray.lnk (no console window).
setlocal
cd /d "%~dp0"
if "%~1"=="" (
    start "" venv\Scripts\pythonw.exe pytray.py
) else (
    start "" venv\Scripts\pythonw.exe pytray.py %1
)
