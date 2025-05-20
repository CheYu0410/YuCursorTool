@echo off
echo Starting YuCursor GUI...

REM Check if python is available
python --version >nul 2>nul
if errorlevel 1 (
    echo Error: Python is not installed or not found in PATH.
    echo Please ensure Python is installed correctly and added to your system PATH.
    goto :eof
)

REM Check if gui_app.py exists
if not exist gui_app.py (
    echo Error: gui_app.py not found in the current directory.
    echo Please make sure this script is in the same directory as gui_app.py.
    goto :eof
)

python gui_app.py

echo.
echo YuCursor GUI has been closed.
pause 