@echo off
title 創建桌面快捷方式

:: 獲取當前目錄
set "CURRENT_DIR=%~dp0"
set "TARGET_FILE=%CURRENT_DIR%run_as_admin.bat"
set "SHORTCUT_NAME=Cursor 自動化工具 (管理員模式)"

:: 創建 VBScript 來生成快捷方式
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\%SHORTCUT_NAME%.lnk" >> "%TEMP%\CreateShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
echo oLink.TargetPath = "%TARGET_FILE%" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WorkingDirectory = "%CURRENT_DIR%" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Description = "以管理員權限啟動 Cursor 自動化工具" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.IconLocation = "%CURRENT_DIR%assets\cursor-icon.ico, 0" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"

:: 執行 VBScript
cscript //nologo "%TEMP%\CreateShortcut.vbs"
del "%TEMP%\CreateShortcut.vbs"

echo 已在桌面創建「%SHORTCUT_NAME%」快捷方式。
echo 請注意：您需要右鍵點擊該快捷方式，選擇「屬性」，
echo 然後在「捷徑」選項卡中勾選「以管理員身份運行」，並點擊「確定」。
pause 