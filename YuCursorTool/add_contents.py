import os

# 獲取主頁和關於頁面的內容
pages_content = """
    # 創建主頁內容
    home_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Row([logo_image, banner_text], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.Text("歡迎使用 YuCursor", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text("一個專為 Cursor 編輯器設計的帳號管理和自動化工具", text_align=ft.TextAlign.CENTER),
                ft.Container(height=20),
                ft.Text("功能概述:", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("• 自動註冊新帳號 - 透過自動化流程創建新的 Cursor 帳號", text_align=ft.TextAlign.LEFT),
                ft.Text("• 帳號管理 - 儲存和管理多個 Cursor 帳號，方便快速切換", text_align=ft.TextAlign.LEFT),
                ft.Text("• 重置機器碼 - 重置機器識別碼，解決一些登入限制問題", text_align=ft.TextAlign.LEFT),
                ft.Container(height=20),
                ft.Text("開始使用:", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("1. 點擊「功能操作」標籤頁進行各種操作", text_align=ft.TextAlign.LEFT),
                ft.Text("2. 點擊「帳號管理」標籤頁查看和管理已儲存的帳號", text_align=ft.TextAlign.LEFT),
                ft.Text("3. 使用右上角的設定按鈕配置應用程式參數", text_align=ft.TextAlign.LEFT),
            ]),
            padding=20,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            margin=20
        )
    ], alignment=ft.MainAxisAlignment.START, expand=True, scroll=ft.ScrollMode.AUTO)

    # 創建關於頁面內容
    about_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("關於 YuCursor", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Divider(),
                ft.Container(height=10),
                ft.Row([
                    ft.Image(src="/YuCursor.png", width=50, height=50, fit=ft.ImageFit.CONTAIN),
                    ft.Column([
                        ft.Text("YuCursor", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("版本 1.0.1", size=16),
                        ft.Text("發布日期：2025年5月20日", size=16)
                    ])
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=20),
                ft.Text("應用介紹", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("YuCursor 是一款專為 Cursor 編輯器設計的帳號管理和自動化工具，幫助用戶輕鬆創建和管理多個 Cursor 帳號。", size=16),
                ft.Container(height=10),
                ft.Text("開發者資訊", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("本應用由 YuTeam 開發團隊開發", size=16),
                ft.Container(height=20),
                ft.Text("注意事項", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_600),
                ft.Text("• 本工具永久免費，請勿從任何渠道購買", size=16),
                ft.Text("• 請勿將本工具用於非法用途", size=16),
                ft.Text("• 使用本工具所產生的任何後果由使用者自行承擔", size=16),
                ft.Container(height=30),
                ft.Text("© 2025 YuTeam. 保留所有權利。", size=14, italic=True, text_align=ft.TextAlign.CENTER)
            ]),
            padding=20,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            margin=20
        )
    ], alignment=ft.MainAxisAlignment.START, expand=True, scroll=ft.ScrollMode.AUTO)
"""

# 創建一個完全新的文件
with open('gui_app_fixed.py', 'w', encoding='utf-8') as f:
    # 導入部分（保持不變）
    f.write("""import sys
import os
# 確保能找到所有模組
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'Lib', 'site-packages'))

# 確保打包後事件處理正常
os.environ["FLET_FORCE_WEB_VIEW"] = "true"
os.environ["FLET_VIEW"] = "gui"

# 添加圖示相關路徑
def get_resource_path(relative_path):
    \"\"\"獲取資源的絕對路徑，無論是運行腳本還是打包後的 exe\"\"\"
    try:
        # PyInstaller 創建臨時文件夾，將路徑存在 _MEIPASS
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    except Exception:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

import flet as ft
import subprocess
import threading
import sys
import os
from config import Config # <--- 引入 Config
import re # <--- 引入 re for .env parsing
from typing import List, Optional, Dict # <--- 引入 List, Optional, Dict
import time
from accounts_manager import AccountsManager # <--- 引入 AccountsManager
from cursor_auth_manager import CursorAuthManager # <--- 引入 CursorAuthManager
import json
import datetime
import pyautogui
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import pyperclip
import base64
import traceback # 確保 traceback 可用

# Module-level variable to hold the Flet page instance
_flet_page_instance = None
_app_is_closing = False # <--- 新增的全局標誌
""")

    # 從原文件中獲取其餘部分
    with open('gui_app.py', 'r', encoding='utf-8') as source:
        content = source.read()
        
        # 跳過導入部分
        start_idx = content.find("# 保存設定按鈕圖標")
        
        if start_idx != -1:
            # 獲取從 "保存設定按鈕圖標" 開始到 "添加標籤頁控件" 前的部分
            end_idx = content.find("# 添加標籤頁控件")
            
            if end_idx != -1:
                f.write("\n")
                f.write(content[start_idx:end_idx])
                f.write("\n")
                
                # 添加頁面內容定義
                f.write(pages_content)
                f.write("\n")
                
                # 添加更新日誌內容
                changelog_section = content.find("# 創建更新日誌內容")
                if changelog_section != -1:
                    changelog_end = content.find("# 添加標籤頁控件", changelog_section)
                    if changelog_end != -1:
                        f.write(content[changelog_section:changelog_end])
                        f.write("\n")
                
                # 添加剩餘部分
                f.write(content[end_idx:])
            else:
                print("找不到標籤頁控件部分")
        else:
            print("找不到開始部分")

print("已創建修復後的文件：gui_app_fixed.py") 