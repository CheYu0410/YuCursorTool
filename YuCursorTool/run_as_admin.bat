@echo off
echo 以管理員權限啟動 Cursor 自動化工具
echo.

:: 批次檔所在目錄
cd /d "%~dp0"

:: 檢查是否為打包版本（通過檢查 YuCursor.exe 存在與否）
if exist YuCursor.exe (
    echo 檢測到打包版本，使用 YuCursor.exe 啟動...
    powershell -Command "Start-Process -FilePath 'YuCursor.exe' -Verb RunAs"
) else (
    :: 檢測 Python 安裝
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo 錯誤: 未檢測到 Python 安裝
        echo 請先安裝 Python 3.8 或更高版本
        pause
        exit /b 1
    )

    :: 使用 Python 執行
    echo 使用 Python 啟動 gui_app.py...
    powershell -Command "Start-Process -FilePath python -ArgumentList 'gui_app.py' -Verb RunAs"
)

echo 已嘗試以管理員權限啟動，程式窗口將會另外打開
echo 如果沒有看到程式窗口，請檢查 UAC 提示並授權
echo.
timeout /t 5 