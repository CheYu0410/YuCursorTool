@echo off
set PYTHONWARNINGS=ignore::SyntaxWarning:DrissionPage
echo Building Cursor Keep Alive...

:: Check if virtual environment exists
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment!
        exit /b 1
    )
)

:: Activate virtual environment and wait for activation to complete
call venv\Scripts\activate.bat
timeout /t 2 /nobreak > nul

:: Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Run build script
echo Starting build process...
python build.py

:: Deactivate virtual environment
deactivate

:: Keep window open
echo Build completed!
pause 