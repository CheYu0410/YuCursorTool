@echo off
echo Installing required Python modules...

REM Check if pip is available
pip --version >nul 2>nul
if errorlevel 1 (
    echo Error: pip is not installed or not found in PATH.
    echo Please ensure Python and pip are installed correctly and added to your system PATH.
    goto :eof
)

REM Install modules from requirements.txt
for /F "delims==" %%i in (requirements.txt) do (
    echo Installing %%i
    pip install %%i
    if errorlevel 1 (
        echo Failed to install %%i. Please check the error message above.
    )
)

echo.
echo All modules from requirements.txt have been processed.
pause 