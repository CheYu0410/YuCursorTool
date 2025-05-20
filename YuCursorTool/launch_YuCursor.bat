@echo off
echo 正在啟動 YuCursor...
echo.

:: 批次檔所在目錄
cd /d "%~dp0"

:: 檢查是否為打包版本
if exist YuCursor.exe (
    :: 使用 Python 啟動器腳本
    python flet_launcher.py
) else (
    :: 使用 Python 執行
    python gui_app.py
)

if %errorlevel% neq 0 (
    echo 啟動時發生錯誤，請檢查日誌
    pause
) 