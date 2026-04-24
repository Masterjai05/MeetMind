@echo off
echo Starting MeetMind...
cd /d D:\Jai\Projects\meetmind\backend
call venv\Scripts\activate.bat
start python app.py
timeout /t 3 >nul
start "" "D:\Jai\Projects\meetmind\frontend\index.html"
echo MeetMind is running. Close this window to stop.
pause