@echo off
REM Voice Transcriber — double-click launcher
REM Uses pythonw so no console window appears. App lives in the system tray.
REM To see logs: run "python src\main.py" in a terminal instead.

cd /d "%~dp0"
start "" pythonw src\main.py
