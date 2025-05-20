@echo off
echo 正在啟動 YuCursor (Web 模式)...
echo.

:: 批次檔所在目錄
cd /d "%~dp0"

:: 設置環境變數強制使用瀏覽器模式
set FLET_VIEW=web
set FLET_WEB_PORT=8550

:: 啟動 YuCursor
start "" "YuCursor.exe"

:: 等待 2 秒
timeout /t 2 > nul

:: 嘗試打開瀏覽器
start http://localhost:8550

echo 已嘗試啟動 YuCursor 並打開瀏覽器
echo 如果瀏覽器未自動打開，請手動訪問 http://localhost:8550
echo. 