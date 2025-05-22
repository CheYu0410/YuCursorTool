import sys
import os
# 確保能找到所有模組
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'Lib', 'site-packages'))

# 確保打包後事件處理正常
os.environ["FLET_FORCE_WEB_VIEW"] = "true"
os.environ["FLET_VIEW"] = "gui"

# 定義全局變數
accounts_manager = None
refresh_account_list = None
refresh_current_account = None
_flet_page_instance = None
_app_is_closing = False
current_account_email = None
manual_verification_code = None
g_keep_alive_process = None

# 添加圖示相關路徑
def get_resource_path(relative_path):
    """獲取資源的絕對路徑，無論是運行腳本還是打包後的 exe"""
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
import cursor_acc_info # <--- 導入 cursor_acc_info 模組

# 預先初始化關鍵模組
try:
    if accounts_manager is None:
        accounts_manager = AccountsManager()
        print("已預先初始化 AccountsManager")
except Exception as e:
    print(f"預先初始化 AccountsManager 失敗: {str(e)}")
    traceback.print_exc()

# Module-level variable to hold the Flet page instance
_flet_page_instance = None
_app_is_closing = False # <--- 新增的全局標誌

# 保存設定按鈕圖標
def save_icon_files():
    try:
        # 設定圖標 (齒輪圖標) 的二進制數據
        settings_icon_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x14\x00\x00\x00\x14\x08\x06\x00\x00\x00\x8d\x89\x1d\r\x00\x00\x00\tpHYs\x00\x00\x0e\xc4\x00\x00\x0e\xc4\x01\x95+\x0e\x1b\x00\x00\x00\x89IDAT8\x8dc`\x18\x05\xa3a\x80\r\x18\xa5\xa5\xa5\xbd\x19\x19\x19\x93@\xf8\xff\xff\xff\x95@L0&//\xbf\x89\x11\xa8h\x15P\x02\x19\x97\x97\x97\x9f\xc51\xa2A\x8a@j\x91\xc5\x19\xa1\xaa\x84\x80\xf8\x1d\x10\x7f\x03\xe2N$5\x10\x8c\xa4\x17\x14\x8a\xc8\n\x818\x1c\x88\x93\x80x\x03\x10\xdfE\xd3\x83\xa0\r\xac\x06\xe2\x10\x888\x1a\x88\xaf\x01\xf15 \xfeD\xd2\x83,\x1f\x02\xc5\x9f\x80x\x15\x10\x7f\x07\xe27\xd8\x1c\x83\xcdi\xa1\xda\x82\xa1\x06\xb4\xf9\x03\xc4&\xa0\x04210\x18i6\x0c\x00\x00\xe6\xfc\x1b\xbe,\x8d\x8d\xd5\x00\x00\x00\x00IEND\xaeB`\x82'
        
        # 保存路徑
        app_path = os.path.dirname(os.path.abspath(__file__))
        settings_icon_path = os.path.join(app_path, "settings_icon.png")
        
        # 如果圖標文件不存在，則保存
        if not os.path.exists(settings_icon_path):
            with open(settings_icon_path, 'wb') as f:
                f.write(settings_icon_data)
            print(f"已保存設定圖標到 {settings_icon_path}")
        
        return True
    except Exception as e:
        print(f"保存圖標文件時出錯: {str(e)}")
        return False

# 嘗試保存圖標文件
save_icon_files()

# 重新導向標準輸出和錯誤到 GUI
class UILogHandler:
    def __init__(self, log_view):
        self.log_view = log_view
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.page = None
        self.buffer = ""  # 添加一個緩衝區來收集完整輸出
        self.max_log_lines = 5000  # 增加日誌最大顯示行數，使其能顯示更多內容

    def write(self, message):
        self.original_stdout.write(message)
        
        # 將消息添加到緩衝區
        self.buffer += message
        
        # 檢查消息是否包含換行符，如果有則處理並清除緩衝區
        if "\n" in self.buffer:
            # 按換行符分割
            lines = self.buffer.split("\n")
            # 保留最後一行（可能不完整）
            self.buffer = lines[-1]
            # 處理完整的行
            for line in lines[:-1]:
                if self.log_view.page:
                    # 無條件添加所有非空行到日誌視圖
                    if line.strip():  # 只處理非空行
                        # 驗證碼相關檢測
                        if ("找到邮件主题:" in line and "verification code" in line.lower()) or \
                           ("等待手動輸入驗證碼" in line or "請輸入驗證碼:" in line):
                            self.show_verification_dialog()
                        
                        # 添加時間戳
                        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
                        
                        # 根據訊息類型設置樣式
                        text_color = None
                        if "錯誤" in line or "error" in line.lower() or "失敗" in line:
                            text_color = ft.Colors.RED
                        elif "警告" in line or "warning" in line.lower():
                            text_color = ft.Colors.ORANGE
                        elif "成功" in line or "success" in line.lower() or "已完成" in line:
                            text_color = ft.Colors.GREEN
                        
                        # 添加日誌條目，使用等寬字體並保留格式
                        log_text = ft.Text(
                            f"{timestamp}{line}",
                            color=text_color,
                            font_family="monospace",
                            selectable=True  # 使文字可選擇，方便複製
                        )
                        
                        self.log_view.controls.append(log_text)
                        
                        # 如果日誌條目超過最大數量，移除較早的條目
                        if len(self.log_view.controls) > self.max_log_lines:
                            self.log_view.controls.pop(0)
                        
                        self.log_view.update()

    def flush(self):
        # 當 flush 被調用時，如果緩衝區中還有數據，則輸出它
        if self.buffer:  # 移除.strip()檢查，確保所有緩衝內容都被輸出
            if self.log_view.page:
                # 添加時間戳
                timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
                
                # 添加日誌條目，使用等寬字體
                log_text = ft.Text(
                    f"{timestamp}{self.buffer}",
                    font_family="monospace",
                    selectable=True  # 使文字可選擇，方便複製
                )
                
                self.log_view.controls.append(log_text)
                # 如果日誌條目超過最大數量，移除較早的條目
                if len(self.log_view.controls) > self.max_log_lines:
                    self.log_view.controls.pop(0)
                self.log_view.update()
            self.buffer = ""
        self.original_stdout.flush()

    def start_redirect(self):
        sys.stdout = self
        sys.stderr = self

    def stop_redirect(self):
        global _app_is_closing # <--- 訪問全局標誌
        # 確保在停止重定向前清空緩衝區
        if not _app_is_closing:
            self.flush()
        else:
            print("UILogHandler.stop_redirect: App is closing, skipping flush.")
            self.buffer = "" 
            self.original_stdout.flush()

        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
    def set_page(self, page):
        self.page = page
        
    def show_verification_dialog(self):
        if not self.page:
            return
            
        def close_dlg(e):
            verification_dialog.open = False
            self.page.update()
            
        def submit_code(e):
            code = verification_code_field.value
            if code and len(code) == 6 and code.isdigit():
                # 將驗證碼寫入到標準輸入用於程式處理
                # 這裡使用一個全局變數來傳遞驗證碼
                global manual_verification_code
                manual_verification_code = code
                verification_dialog.open = False
                self.page.update()
                self.page.overlay.append(ft.SnackBar(ft.Text(f"驗證碼 {code} 已提交"), open=True))
                self.page.update()
            else:
                verification_code_field.error_text = "請輸入6位數字驗證碼"
                verification_code_field.update()
                
        verification_code_field = ft.TextField(
            label="請輸入驗證碼",
            hint_text="請輸入您收到的6位數字驗證碼",
            width=300
        )
        
        verification_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("請輸入驗證碼"),
            content=ft.Column([
                ft.Text("程式正在等待驗證碼輸入，請查看您的郵箱並輸入收到的6位數字驗證碼"),
                verification_code_field,
            ], tight=True),
            actions=[
                ft.TextButton("取消", on_click=close_dlg),
                ft.TextButton("提交", on_click=submit_code),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            open=True
        )
        
        self.page.overlay.append(verification_dialog)
        self.page.update()

def main(page: ft.Page):
    # 確保首先導入需要的模組
    from accounts_manager import AccountsManager
    from cursor_auth_manager import CursorAuthManager
    
    # 設置全局變數，讓外部函數可以訪問
    global accounts_manager, refresh_account_list, refresh_current_account
    global _flet_page_instance, _app_is_closing, current_account_email
    _flet_page_instance = page
    current_account_email = None # 初始化為 None
    
    # 初始化帳號管理器 (不管是否為重啟模式都需要)
    try:
        accounts_manager = AccountsManager()
        print("帳號管理器已初始化")
    except Exception as e:
        print(f"初始化帳號管理器失敗: {str(e)}")
        traceback.print_exc()
    
    # 檢查是否為重啟模式，如果是則進行額外初始化
    is_restarted = "--restarted" in sys.argv
    if is_restarted:
        print("在主函數中檢測到重啟模式，進行額外初始化...")
        # 確保全局對象已正確初始化
        if 'accounts_manager' not in globals() or accounts_manager is None:
            from accounts_manager import AccountsManager
            accounts_manager = AccountsManager()
            print("已在重啟模式下重新初始化 accounts_manager")

    page.title = "YuCursor" # 修改視窗標題
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 900  # 增加窗口寬度
    page.window_height = 750  # 增加窗口高度
    page.window_focused = True
    page.padding = 5  # 減少頁面邊距
    page.spacing = 5  # 減少頁面元素間距
    
    # 使用 Flet 規定的 page.window_icon_url 設定圖示
    # 確保 YuCursor.png 在 assets_dir (即腳本所在目錄)
    icon_path = get_resource_path("YuCursor.png")
    page.window_icon_url = "/YuCursor.png"
    
    # 定義啟動提示視窗函數
    def show_welcome_dialog():
        def close_welcome_dialog(e):
            welcome_dialog.open = False
            page.update()
            
            # 確保關閉對話框後顯示「主頁」標籤頁
            if tabs:
                tabs.selected_index = 0  # 切換到主頁
                tabs.update()
        
        welcome_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.ORANGE, size=30),
                ft.Text("重要提示", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
            ], alignment=ft.MainAxisAlignment.CENTER),
            content=ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.VERIFIED_USER, color=ft.Colors.BLUE_600, size=24),
                            ft.Text("YuCursor永久免費", 
                                   size=20, 
                                   weight=ft.FontWeight.BOLD, 
                                   color=ft.Colors.BLUE_600, 
                                   text_align=ft.TextAlign.CENTER),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        margin=10
                    ),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.DO_NOT_DISTURB_ON, color=ft.Colors.RED, size=24),
                            ft.Text("請勿轉賣", 
                                   size=20, 
                                   weight=ft.FontWeight.BOLD, 
                                   color=ft.Colors.RED, 
                                   text_align=ft.TextAlign.CENTER),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        margin=10
                    ),
                    ft.Divider(height=1, thickness=1, color=ft.Colors.GREY_400),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("本軟體為免費工具，提供 Cursor 帳號管理功能", 
                                size=16,
                                text_align=ft.TextAlign.CENTER,
                                color=ft.Colors.BLACK),
                            ft.Text("請尊重開發者的勞動成果，不要用於非法用途", 
                                size=16,
                                text_align=ft.TextAlign.CENTER,
                                color=ft.Colors.BLACK),
                        ]),
                        padding=10,
                        border_radius=5,
                        bgcolor=ft.Colors.GREY_100
                    ),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Text("請勿在任何平台出售此軟體，違者必究",
                                size=14,
                                color=ft.Colors.RED_700,
                                text_align=ft.TextAlign.CENTER,
                                weight=ft.FontWeight.BOLD),
                        padding=10,
                        border=ft.border.all(1, ft.Colors.RED_200),
                        border_radius=5,
                        bgcolor=ft.Colors.RED_50
                    )
                ], 
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5
                ),
                width=450,
                padding=20,
                border_radius=10,
                bgcolor=ft.Colors.GREY_200 # 主要內容容器背景
            ),
            actions=[
                ft.ElevatedButton(
                    "我已了解並同意",
                    icon=ft.Icons.CHECK_CIRCLE,
                    on_click=close_welcome_dialog,
                    style=ft.ButtonStyle(
                        color=ft.Colors.WHITE,
                        bgcolor=ft.Colors.BLUE_500
                    )
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            bgcolor=ft.Colors.GREY_300, # 整個對話框背景
            shape=ft.RoundedRectangleBorder(radius=10),
            open=True
        )
        
        page.overlay.append(welcome_dialog)
        page.update()
        
    # 稍後調用 show_welcome_dialog() 函數
    
    # page.theme_mode = ft.ThemeMode.DARK

    # 初始化日誌視圖，增加高度並設置自動滾動
    log_view = ft.ListView(
        expand=True, 
        spacing=0,  # 減少行間距以顯示更多內容
        auto_scroll=True, 
        height=500,  # 增加日誌區域的高度
        # 使用定寬字體，改善日誌顯示效果
        item_extent=22  # 設置每個項目的高度，使其更緊湊
    )
    
    # 設置日誌視圖的容器樣式
    log_container = ft.Container(
        content=log_view,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=5,
        padding=10,
        expand=True,
        # 優化滾動效果
        clip_behavior=ft.ClipBehavior.HARD_EDGE
    )
    
    ui_log_handler = UILogHandler(log_view)
    ui_log_handler.start_redirect()
    ui_log_handler.set_page(page)  # 設置頁面引用
    
    # 將 ui_log_handler 保存到 page 實例中
    page._ui_log_handler = ui_log_handler

    # 初始化帳號管理器
    accounts_manager = AccountsManager()
    
    # 複製到剪貼板功能
    def copy_to_clipboard(text, type_name):
        page.set_clipboard(text)
        page.overlay.append(ft.SnackBar(ft.Text(f"{type_name}已複製到剪貼板"), open=True))
        page.update()
    
    # === 添加帳號選擇區域 ===
    def refresh_account_list():
        global _app_is_closing # <--- 訪問全局標誌
        if _app_is_closing:
            print("refresh_account_list: App is closing, skipping UI updates.")
            return
        
        # 清空當前列表
        account_list.controls.clear()
        
        try:
            # 獲取帳號列表
            accounts = accounts_manager.get_accounts()
            
            if not accounts:
                # 嘗試重新載入帳號管理器
                # reload_accounts_manager() # 避免循環調用或潛在問題，如果需要確保已載入，應在更高層次處理
                accounts = accounts_manager.get_accounts() # 直接再次獲取
            
            # 使用集合確保帳號唯一性
            processed_emails = set()
                
            # 為每個帳號創建一個卡片
            if accounts:
                for account in accounts:
                    email = account.get('email', '')
                    
                    # 如果這個郵箱已經處理過，則跳過，避免重複顯示
                    if email in processed_emails:
                        continue
                    
                    # 將此郵箱添加到已處理集合
                    processed_emails.add(email)
                    
                    # 以下是原有的卡片創建邏輯
                    password = account.get('password', '')
                    created_at = account.get('created_at', '未知時間')
                    updated_at = account.get('updated_at', '未知時間')
                    
                    # 這個是當前使用的帳號嗎？
                    is_current = False
                    if current_account_email and email == current_account_email:
                        is_current = True
                    
                    # 初始化狀態顯示和進度條變數
                    status_text = "Free"
                    subscription_text = "快速回應: 0/50"
                    usage_percent = 0
                    progress_color = ft.Colors.GREEN
                    has_usage_info = False
                    
                    # 獲取會員資訊（如果有）
                    if account.get('membership') and isinstance(account['membership'], dict):
                        membership = account['membership']
                        if membership.get('type'):
                            status_text = membership.get('type')
                    
                    # 獲取使用資訊（如果有）
                    if account.get('usage') and isinstance(account['usage'], dict):
                        usage = account['usage']
                        has_usage_info = True
                        try:
                            if 'premium_usage' in usage and 'max_premium_usage' in usage:
                                # 確保將字符串轉換為數字
                                try:
                                    premium_usage = int(usage.get('premium_usage', 0))
                                except (ValueError, TypeError):
                                    print(f"警告: 帳號 {email} 的 premium_usage 無法轉換為整數: {usage.get('premium_usage')}")
                                    premium_usage = 0
                                
                                try:
                                    max_premium_usage = int(usage.get('max_premium_usage', 50))
                                except (ValueError, TypeError):
                                    print(f"警告: 帳號 {email} 的 max_premium_usage 無法轉換為整數: {usage.get('max_premium_usage')}")
                                    max_premium_usage = 50
                                
                                # 防止除零錯誤
                                if max_premium_usage <= 0:
                                    max_premium_usage = 100
                                
                                # 計算使用比例
                                usage_percent = min(premium_usage / max_premium_usage, 1.0)
                                
                                # 根據使用百分比決定顏色
                                if usage_percent > 0.8:
                                    progress_color = ft.Colors.RED
                                elif usage_percent > 0.6:
                                    progress_color = ft.Colors.ORANGE
                                else:
                                    progress_color = ft.Colors.GREEN
                                    
                                subscription_text = f"快速回應: {premium_usage}/{max_premium_usage}"
                            else:
                                print(f"警告: 帳號 {email} 的用量資訊中缺少必要欄位")
                                subscription_text = "快速回應: 0/50"
                                usage_percent = 0
                        except Exception as e:
                            print(f"處理帳號 {email} 用量資訊時出錯: {str(e)}")
                            traceback.print_exc()
                    else:
                        # 沒有用量資訊時提供默認值
                        has_usage_info = False
                        subscription_text = "快速回應: 0/50"
                        usage_percent = 0
                    
                    # 建立帳號卡片
                    account_card = ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(
                                        email,
                                        weight=ft.FontWeight.BOLD, 
                                        size=16,
                                        color=ft.Colors.BLUE_700 if is_current else None,
                                        selectable=True,  # 使郵箱可以選擇
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.CONTENT_COPY,
                                        tooltip="複製郵箱",
                                        icon_size=16,
                                        on_click=lambda e, em=email: copy_to_clipboard(em, "郵箱")
                                    ),
                                    ft.Text("(當前使用中)", size=12, color=ft.Colors.GREEN_700) if is_current else ft.Container(),
                                ]),
                                
                                # 添加可複製的密碼區域
                                ft.Row([
                                    ft.Text("密碼:", weight=ft.FontWeight.BOLD, size=14),
                                    ft.TextField(
                                        value=password if password else "無密碼",
                                        read_only=True,
                                        password=True,
                                        can_reveal_password=True,
                                        border=ft.InputBorder.NONE,
                                        height=40,
                                        width=150,
                                        text_size=14,
                                        content_padding=ft.padding.only(top=4),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.CONTENT_COPY,
                                        tooltip="複製密碼",
                                        icon_size=16,
                                        on_click=lambda e, pw=password: copy_to_clipboard(pw, "密碼")
                                    ),
                                ]),
                                
                                ft.Text(f"訂閱類型: {status_text}", size=14),
                                
                                # 添加快速回應用量顯示以及進度條
                                ft.Text(subscription_text, size=14),
                                
                                # 始終顯示進度條，但根據是否有用量資訊決定顯示方式
                                ft.ProgressBar(
                                    width=200, 
                                    value=usage_percent if has_usage_info else 0,
                                    color=progress_color if has_usage_info else ft.Colors.GREY_500,
                                    bgcolor=ft.Colors.GREY_300,
                                    height=5
                                ),
                                
                                ft.Text(f"創建時間: {created_at}", size=12, color=ft.Colors.GREY_700),
                                
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.Icons.LOGIN, 
                                        tooltip="使用此帳號",
                                        on_click=lambda e, em=email: use_account(em)
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE, 
                                        tooltip="刪除帳號",
                                        on_click=lambda e, em=email: delete_account(em)
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.INFO, 
                                        tooltip="帳號詳情",
                                        on_click=lambda e, acc=account.copy(): show_account_details(acc)
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.REFRESH, 
                                        tooltip="刷新帳號資訊",
                                        on_click=lambda e, em=email: refresh_account_info(em)
                                    ),
                                ], alignment=ft.MainAxisAlignment.END),
                            ]),
                            padding=10,
                        ),
                        margin=5,
                    )
                    
                    account_list.controls.append(account_card)
            else:
                # 如果沒有帳號，顯示提示
                account_list.controls.append(
                    ft.Container(
                        content=ft.Text("目前沒有儲存的帳號，請使用自動註冊功能或手動添加帳號。", 
                                       text_align=ft.TextAlign.CENTER),
                        margin=20,
                        alignment=ft.alignment.center
                    )
                )
        except Exception as e:
            print(f"刷新帳號列表時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 顯示錯誤資訊
            account_list.controls.append(
                ft.Container(
                    content=ft.Text(f"載入帳號列表時出錯: {str(e)}", 
                                   text_align=ft.TextAlign.CENTER, 
                                   color=ft.Colors.RED),
                    margin=20,
                    alignment=ft.alignment.center
                )
            )
        
        # 更新 UI
        try:
            account_list.update()
        except RuntimeError as e:
            print(f"refresh_account_list: account_list.update() failed (loop likely closed): {str(e)}")
        except Exception as e:
            print(f"refresh_account_list: Unexpected error during account_list.update(): {str(e)}")
    
    # 新增刷新單個帳號資訊的功能
    def refresh_account_info(email):
        try:
            # 找到帳號
            account = accounts_manager.get_account(email)
            if not account:
                print(f"找不到帳號: {email}")
                return
            
            # 獲取令牌
            access_token = account.get('access_token')
            if not access_token:
                print(f"帳號 {email} 沒有有效的訪問令牌")
                page.overlay.append(ft.SnackBar(ft.Text(f"帳號 {email} 沒有有效的訪問令牌"), open=True))
                page.update()
                return
            
            # 顯示正在刷新的提示
            page.overlay.append(ft.SnackBar(
                ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2),
                    ft.Text(f"正在刷新帳號 {email} 的資訊...")
                ]),
                open=True
            ))
            page.update()
            
            # 在背景執行獲取帳號詳情的任務
            def update_account_info_task():
                try:
                    print(f"開始獲取帳號 {email} 的詳細資訊...")
                    
                    # 獲取使用情況 - 執行直接呼叫以便調試
                    print(f"使用令牌尾碼 {access_token[-5:]} 獲取用量資訊...")
                    usage_info = cursor_acc_info.UsageManager.get_usage(access_token)
                    
                    # 獲取訂閱信息
                    print(f"使用令牌尾碼 {access_token[-5:]} 獲取訂閱資訊...")
                    subscription_info = cursor_acc_info.UsageManager.get_stripe_profile(access_token)
                    
                    # 輸出為調試
                    print(f"取得用量資訊: {usage_info}")
                    print(f"取得訂閱資訊: {subscription_info}")
                    
                    # 確保 usage_info 有效
                    if usage_info is None:
                        print(f"警告: 帳號 {email} 獲取用量資訊失敗，使用默認值")
                        usage_info = {"premium_usage": 0, "max_premium_usage": 50, "basic_usage": 0, "max_basic_usage": "無限"}
                    
                    # 更新帳號信息
                    account['usage'] = usage_info
                    
                    if subscription_info:
                        # 保存會員資訊
                        account['membership'] = subscription_info
                        account['account_status'] = cursor_acc_info.format_subscription_type(subscription_info)
                    
                    # 保存更新
                    print(f"正在儲存帳號資訊...")
                    accounts_manager._save_accounts()
                    print(f"帳號資訊已成功儲存至 {accounts_manager.accounts_file}")
                    
                    # 在UI線程中更新界面
                    def update_ui():
                        try:
                            # 刷新帳號列表顯示
                            refresh_account_list()
                            
                            # 準備顯示用量資訊
                            premium_usage = "0"
                            max_premium_usage = "50"
                            
                            try:
                                if usage_info and 'premium_usage' in usage_info:
                                    premium_usage = str(usage_info.get('premium_usage', '0'))
                                    max_premium_usage = str(usage_info.get('max_premium_usage', '50'))
                                    print(f"在對話框中顯示快速回應用量: {premium_usage}/{max_premium_usage}")
                            except Exception as ue:
                                print(f"處理用量資訊時出錯: {ue}")
                            
                            # 計算進度條顏色和百分比
                            try:
                                usage_percent = float(premium_usage) / float(max_premium_usage) if float(max_premium_usage) > 0 else 0
                                color_text = ft.Colors.GREEN
                                if usage_percent > 0.8:
                                    color_text = ft.Colors.RED
                                elif usage_percent > 0.6:
                                    color_text = ft.Colors.ORANGE
                            except Exception as ce:
                                print(f"計算用量百分比時出錯: {ce}")
                                usage_percent = 0
                                color_text = ft.Colors.GREEN
                            
                            # 顯示成功訊息
                            success_dialog = ft.AlertDialog(
                                title=ft.Row([
                                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                                    ft.Text("帳號資訊已更新")
                                ]),
                                content=ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text(f"帳號: {email}", weight=ft.FontWeight.BOLD),
                                            ft.Text(f"訂閱類型: {account.get('account_status', 'Free')}"),
                                            ft.Row([
                                                ft.Text(f"快速回應用量: {premium_usage}/{max_premium_usage}", color=color_text),
                                                ft.IconButton(
                                                    icon=ft.Icons.INFO,
                                                    tooltip="查看詳情",
                                                    on_click=lambda e, acc=account: show_account_details(acc)
                                                )
                                            ]),
                                            # 顯示進度條
                                            ft.ProgressBar(
                                                width=300,
                                                value=usage_percent,
                                                color=color_text,
                                                bgcolor=ft.Colors.GREY_300,
                                                height=8
                                            )
                                        ],
                                        spacing=10,
                                    ),
                                    padding=ft.padding.all(20),
                                ),
                                actions=[
                                    ft.TextButton("確定", on_click=lambda e, dlg=None: close_success_dialog(e, success_dialog)),
                                ],
                                actions_alignment=ft.MainAxisAlignment.END
                            )
                            
                            def close_success_dialog(e, dialog):
                                page.dialog = dialog
                                dialog.open = False
                                page.update()
                            
                            page.dialog = success_dialog
                            success_dialog.open = True
                            page.update()
                            
                        except Exception as ui_ex:
                            print(f"更新UI時出錯: {str(ui_ex)}")
                            traceback.print_exc()
                    
                    def show_error():
                        # 顯示錯誤訊息
                        page.overlay.append(ft.SnackBar(ft.Text(f"獲取帳號資訊失敗"), open=True))
                        page.update()
                    
                    if _app_is_closing:
                        print("refresh_account_info: App is closing, skipping UI updates.")
                        return
                    
                    # 確保在UI線程中更新界面
                    try:
                        # 嘗試使用不同的方法在UI線程中安全執行更新
                        if hasattr(page, 'run_thread_safe'):
                            # 方法1: 使用 run_thread_safe (如果存在)
                            page.run_thread_safe(update_ui)
                        elif hasattr(page, 'add_to_control_event_queue'):
                            # 方法2: 使用 add_to_control_event_queue (如果存在)
                            page.add_to_control_event_queue(update_ui)
                        else:
                            # 方法3: 直接在這個線程中更新UI (作為最後手段)
                            print("警告: 無法使用安全的UI更新方法，直接更新可能不穩定")
                            update_ui()
                    except Exception as run_thread_ex:
                        print(f"排程UI更新時出錯: {str(run_thread_ex)}")
                        traceback.print_exc()
                        try:
                            # 仍然嘗試更新UI
                            update_ui()
                        except Exception as direct_ex:
                            print(f"直接更新UI時出錯: {str(direct_ex)}")
                
                except Exception as e:
                    print(f"獲取帳號 {email} 詳細資訊時出錯: {str(e)}")
                    traceback.print_exc()
                    if not _app_is_closing:
                        try:
                            # 嘗試使用不同的方法在UI線程中顯示錯誤
                            if hasattr(page, 'run_thread_safe'):
                                page.run_thread_safe(show_error)
                            elif hasattr(page, 'add_to_control_event_queue'):
                                page.add_to_control_event_queue(show_error)
                            else:
                                show_error()
                        except Exception:
                            pass
            
            # 在背景執行任務
            threading.Thread(target=update_account_info_task, daemon=True).start()
            
        except Exception as e:
            print(f"刷新帳號資訊時出錯: {str(e)}")
            traceback.print_exc()
            page.overlay.append(ft.SnackBar(ft.Text(f"刷新帳號資訊時出錯: {str(e)}"), open=True))
            page.update()
    
    # 新增帳號詳情對話框
    def show_account_details(account):
        try:
            print(f"顯示帳號詳情：{account.get('email', '未知')}")
            
            def close_dlg(e):
                try:
                    print("關閉帳號詳情對話框")
                    # 先設置 open=False
                    details_dialog.open = False
                    # 使用 update 刷新對話框狀態
                    page.update()
                    # 延遲一小段時間後再移除對話框，避免並發問題
                    def remove_dialog():
                        try:
                            # 檢查是否已經關閉應用程式
                            global _app_is_closing
                            if _app_is_closing:
                                return
                            # 確保安全移除對話框
                            if details_dialog in page.overlay:
                                page.overlay.remove(details_dialog)
                            page.update()
                            print("對話框已成功移除")
                        except Exception as remove_err:
                            print(f"移除對話框時出錯: {str(remove_err)}")
                            traceback.print_exc()
                    
                    # 使用短暫延遲避免並發問題
                    threading.Timer(0.2, remove_dialog).start()
                except Exception as close_err:
                    print(f"關閉對話框時出錯: {str(close_err)}")
                    traceback.print_exc()
            
            def copy_all_details(e):
                try:
                    print("複製全部帳號資訊")
                    # 生成完整詳情文本
                    details_text = f"帳號: {account.get('email', '')}\n"
                    details_text += f"密碼: {account.get('password', '')}\n"
                    details_text += f"創建時間: {account.get('created_at', '')}\n"
                    details_text += f"更新時間: {account.get('updated_at', '')}\n"
                    
                    # 會員資訊
                    if account.get('membership') and isinstance(account['membership'], dict):
                        membership = account['membership']
                        details_text += f"會員類型: {account.get('account_status', 'Free')}\n"
                        
                        # 顯示更多會員詳情
                        if 'status' in membership:
                            details_text += f"會員狀態: {membership['status']}\n"
                        if 'expiresAt' in membership:
                            details_text += f"到期時間: {membership['expiresAt']}\n"
                    else:
                        details_text += f"會員類型: {account.get('account_status', 'Free')}\n"
                    
                    # 使用資訊
                    if account.get('usage') and isinstance(account['usage'], dict):
                        usage = account['usage']
                        details_text += f"快速回應用量: {usage.get('premium_usage', '0')}/{usage.get('max_premium_usage', '無限')}\n"
                        details_text += f"基本回應用量: {usage.get('basic_usage', '0')}/{usage.get('max_basic_usage', '無限')}\n"
                    
                    # 令牌資訊
                    if account.get('access_token'):
                        details_text += f"訪問令牌: {account.get('access_token', '')}\n"
                    if account.get('refresh_token'):
                        details_text += f"刷新令牌: {account.get('refresh_token', '')}\n"
                    
                    # 複製到剪貼板
                    page.set_clipboard(details_text)
                    page.overlay.append(ft.SnackBar(ft.Text("已複製完整帳號資訊到剪貼板"), open=True))
                    page.update()
                except Exception as copy_err:
                    print(f"複製帳號資訊時出錯: {str(copy_err)}")
                    traceback.print_exc()
            
            def refresh_account_details(e):
                try:
                    print("刷新帳號詳情")
                    # 先關閉對話框
                    details_dialog.open = False
                    page.update()
                    
                    # 使用延遲確保對話框正確關閉後再執行刷新
                    def do_refresh():
                        try:
                            # 檢查是否已經關閉應用程式
                            global _app_is_closing
                            if _app_is_closing:
                                return
                            # 安全移除對話框
                            if details_dialog in page.overlay:
                                page.overlay.remove(details_dialog)
                            page.update()
                            print("對話框已移除，開始刷新帳號資訊")
                            # 刷新帳號資訊
                            refresh_account_info(account.get('email', ''))
                        except Exception as do_refresh_err:
                            print(f"執行刷新操作時出錯: {str(do_refresh_err)}")
                            traceback.print_exc()
                            # 顯示錯誤提示
                            page.overlay.append(ft.SnackBar(ft.Text(f"刷新資訊時出錯: {str(do_refresh_err)}"), open=True))
                            page.update()
                    
                    # 使用短暫延遲避免並發問題
                    threading.Timer(0.2, do_refresh).start()
                except Exception as refresh_err:
                    print(f"刷新帳號詳情時出錯: {str(refresh_err)}")
                    traceback.print_exc()
            
            # 準備顯示的控件列表
            print("準備帳號詳情控件...")
            content_controls = []
            
            # 郵箱和密碼行
            content_controls.append(ft.Row([
                ft.Text("帳號:", weight=ft.FontWeight.BOLD),
                ft.Text(account.get('email', ''), selectable=True),
                ft.IconButton(
                    icon=ft.Icons.CONTENT_COPY,
                    tooltip="複製郵箱",
                    on_click=lambda e, em=account.get('email', ''): copy_to_clipboard(em, "郵箱")
                )
            ]))
            
            content_controls.append(ft.Row([
                ft.Text("密碼:", weight=ft.FontWeight.BOLD),
                ft.TextField(
                    value=account.get('password', ''),
                    read_only=True,
                    password=True,
                    can_reveal_password=True,
                    border=ft.InputBorder.NONE,
                    height=40,
                    width=220,
                    text_size=14,
                    content_padding=ft.padding.only(top=4),
                ),
                ft.IconButton(
                    icon=ft.Icons.CONTENT_COPY,
                    tooltip="複製密碼",
                    on_click=lambda e, pw=account.get('password', ''): copy_to_clipboard(pw, "密碼")
                )
            ]))
            
            # 會員資訊區塊
            membership_section = []
            membership_section.append(ft.Text("會員資訊", size=16, weight=ft.FontWeight.BOLD))
            
            # 訂閱類型（帶顏色指示）
            subscription_type = account.get('account_status', 'Free')
            subscription_color = ft.Colors.GREEN if 'Pro' in subscription_type else ft.Colors.GREY
            membership_section.append(ft.Row([
                ft.Icon(ft.Icons.CARD_MEMBERSHIP, color=subscription_color),
                ft.Text(f"訂閱類型: {subscription_type}", color=subscription_color),
            ]))
            
            # 更多會員詳情（如果有）
            if account.get('membership') and isinstance(account['membership'], dict):
                membership = account['membership']
                if 'status' in membership:
                    membership_section.append(ft.Text(f"會員狀態: {membership['status']}"))
                if 'expiresAt' in membership:
                    membership_section.append(ft.Text(f"到期時間: {membership['expiresAt']}"))
            
            content_controls.append(ft.Container(
                content=ft.Column(membership_section),
                padding=10,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                margin=ft.margin.only(top=10, bottom=10)
            ))
            
            # 使用資訊區塊（如果有）
            if account.get('usage') and isinstance(account['usage'], dict):
                usage_section = []
                usage_section.append(ft.Text("使用情況", size=16, weight=ft.FontWeight.BOLD))
                
                usage = account['usage']
                
                # 快速回應用量 - 使用進度條顯示
                if 'premium_usage' in usage and 'max_premium_usage' in usage:
                    premium_usage = int(usage.get('premium_usage', 0))
                    max_premium_usage = int(usage.get('max_premium_usage', 50))
                    
                    # 防止除零錯誤
                    if max_premium_usage <= 0:
                        max_premium_usage = 100
                    
                    # 計算使用比例
                    usage_percent = min(premium_usage / max_premium_usage, 1.0)
                    
                    # 根據使用百分比決定顏色
                    progress_color = ft.Colors.GREEN
                    if usage_percent > 0.8:
                        progress_color = ft.Colors.RED
                    elif usage_percent > 0.6:
                        progress_color = ft.Colors.ORANGE
                    
                    usage_section.append(ft.Text(f"快速回應用量:"))
                    usage_section.append(
                        ft.Row([
                            ft.ProgressBar(
                                width=250,
                                value=usage_percent,
                                color=progress_color,
                                bgcolor=ft.Colors.GREY_300,
                            ),
                            ft.Text(f"{premium_usage}/{max_premium_usage}", color=progress_color),
                        ])
                    )
                
                # 基本回應用量 - 通常為無限
                if 'basic_usage' in usage:
                    basic_usage = usage.get('basic_usage', 0)
                    max_basic_usage = usage.get('max_basic_usage', '無限')
                    usage_section.append(ft.Text(f"基本回應用量: {basic_usage}/{max_basic_usage}"))
                
                content_controls.append(ft.Container(
                    content=ft.Column(usage_section),
                    padding=10,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=5,
                    margin=ft.margin.only(top=10, bottom=10)
                ))
            
            # 時間資訊
            time_section = []
            time_section.append(ft.Text("時間資訊", size=16, weight=ft.FontWeight.BOLD))
            time_section.append(ft.Text(f"創建時間: {account.get('created_at', '未知')}"))
            time_section.append(ft.Text(f"更新時間: {account.get('updated_at', '未知')}"))
            
            content_controls.append(ft.Container(
                content=ft.Column(time_section),
                padding=10,
                border=ft.border.all(1, ft.Colors.GREY_300),
                border_radius=5,
                margin=ft.margin.only(top=10, bottom=10)
            ))
            
            print("創建帳號詳情對話框...")
            details_dialog = ft.AlertDialog(
                title=ft.Text("帳號詳情"),
                content=ft.Container(
                    content=ft.Column(
                        content_controls,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=400,
                    height=500,
                    padding=10,
                ),
                actions=[
                    ft.TextButton("關閉", on_click=close_dlg),
                    ft.TextButton("複製全部", on_click=copy_all_details),
                    ft.TextButton("刷新資訊", on_click=refresh_account_details),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            print("設置和顯示對話框...")
            # 修改為使用 overlay 而非 dialog 屬性
            page.overlay.append(details_dialog)
            details_dialog.open = True
            page.update()
            print("帳號詳情對話框已顯示")
            
        except Exception as e:
            print(f"顯示帳號詳情時出錯: {str(e)}")
            traceback.print_exc()
            try:
                page.overlay.append(ft.SnackBar(ft.Text(f"顯示帳號詳情時出錯: {str(e)}"), open=True))
                page.update()
            except Exception as snack_err:
                print(f"顯示錯誤提示時出錯: {str(snack_err)}")

    # 新增帳號對話框
    def show_add_account_dialog(e):
        def close_dlg(e):
            add_dialog.open = False
            page.update()
            
        def add_account(e):
            email = email_field.value.strip()
            password = password_field.value.strip()
            status = status_field.value.strip()
            
            if not email or not password:
                page.overlay.append(ft.SnackBar(ft.Text("郵箱和密碼不能為空！"), open=True))
                page.update()
                return
            
            # 添加帳號
            kwargs = {
                'account_status': status if status else None
            }
            
            if accounts_manager.add_account(email, password, **kwargs):
                page.overlay.append(ft.SnackBar(ft.Text(f"帳號 {email} 已成功保存！"), open=True))
                add_dialog.open = False
                refresh_account_list()
            else:
                page.overlay.append(ft.SnackBar(ft.Text(f"保存帳號 {email} 失敗！"), open=True))
            
            page.update()
            
        email_field = ft.TextField(
            label="郵箱",
            hint_text="請輸入郵箱地址",
            width=300,
        )
        
        password_field = ft.TextField(
            label="密碼",
            hint_text="請輸入密碼",
            password=True,
            can_reveal_password=True,
            width=300,
        )
        
        status_field = ft.TextField(
            label="帳號狀態 (可選)",
            hint_text="例如：Pro, Premium 等",
            width=300,
        )
        
        add_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("添加新帳號"),
            content=ft.Column([
                email_field,
                password_field,
                status_field,
            ], tight=True),
            actions=[
                ft.TextButton("取消", on_click=close_dlg),
                ft.TextButton("添加", on_click=add_account),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            open=True
        )
        
        page.overlay.append(add_dialog)
        page.update()

    # 使用指定帳號
    def use_account(email):
        try:
            # 獲取帳號詳情
            account = accounts_manager.get_account(email)
            if not account:
                print(f"錯誤：找不到帳號 {email}")
                page.overlay.append(ft.SnackBar(ft.Text(f"找不到帳號 {email}"), open=True))
                return
            
            # 確認使用帳號
            print(f"嘗試使用帳號: {email}")
            
            if g_keep_alive_process and g_keep_alive_process.poll() is None:
                print("警告：已有自動登入進程在運行，無法切換帳號")
                page.overlay.append(ft.SnackBar(ft.Text("已有自動登入進程在運行，請停止後再切換帳號"), open=True))
                return
            
            auth_manager = CursorAuthManager()
            update_successful = False

            # 檢查是否有令牌
            access_token = account.get('access_token')
            refresh_token = account.get('refresh_token')
            # user_id = account.get('user') # 'user' is the key in account, but CursorAuthManager might expect 'user_id'

            if access_token and refresh_token:
                try:
                    # 使用令牌切換帳號
                    print(f"使用令牌切換到帳號: {email}")
                    if auth_manager.update_from_saved_account(account):
                        print(f"成功透過 auth_manager 更新認證資料庫: {email}")
                        update_successful = True
                    else:
                        print(f"透過 auth_manager 更新認證資料庫失敗: {email}")
                        page.overlay.append(ft.SnackBar(ft.Text(f"更新認證資料庫失敗，令牌可能已過期"), open=True))
                except Exception as token_error:
                    print(f"更新認證資料庫時出錯: {str(token_error)}")
                    page.overlay.append(ft.SnackBar(ft.Text(f"更新認證資料庫時出錯: {str(token_error)}"), open=True))
            else:
                # 如果沒有令牌，提示用戶，但仍然允許"選中"該帳號以供後續可能的手動登入或腳本操作
                print(f"帳號 {email} 沒有令牌，無法自動更新認證資料庫。")
                page.overlay.append(ft.SnackBar(ft.Text(f"帳號 {email} 無令牌，請手動登入或執行相關腳本。"), open=True))
                # 即使沒有令牌，也標記為"更新成功"，以便UI更新和後續的Cursor關閉嘗試
                # 因為目標是讓用戶感覺選中了這個帳號，然後提示重啟
                update_successful = True


            if update_successful:
                current_account_text.value = f"當前選中帳號: {email}"
                current_account_password_field.value = account.get('password', '')
                current_account_password_field.visible = True
                page.overlay.append(ft.SnackBar(ft.Text(f"已選中帳號: {email}。正在嘗試關閉並重啟 Cursor 以應用變更..."), open=True))
                
                # 刷新當前帳號顯示
                refresh_current_account() # This should update UI based on auth_manager.get_current_auth()
                                        # which reads from the database we just updated.
                
                # 嘗試關閉 Cursor 以讓變更生效
                try:
                    print("嘗試執行 exit_cursor.py 來關閉 Cursor...")
                    from exit_cursor import ExitCursor # 確保 exit_cursor.py 在 Python 路徑中
                    ExitCursor()
                    print("已執行 exit_cursor.py。請檢查 Cursor 是否已關閉。")
                    page.overlay.append(ft.SnackBar(ft.Text(f"已嘗試關閉 Cursor。現在嘗試重新啟動..."), open=True, duration=3000))
                except ImportError:
                    print("錯誤: 找不到 exit_cursor.py 模組。")
                    page.overlay.append(ft.SnackBar(ft.Text("找不到 exit_cursor.py，無法自動關閉 Cursor。"), open=True))
                except Exception as exit_error:
                    print(f"執行 exit_cursor.py 時出錯: {str(exit_error)}")
                    page.overlay.append(ft.SnackBar(ft.Text(f"關閉 Cursor 時出錯: {str(exit_error)}"), open=True))
                
                # 等待一小段時間確保 Cursor 已關閉
                time.sleep(2) # 等待2秒

                if _app_is_closing: # <--- 在重啟 Cursor 和重新載入帳號前檢查
                    print("use_account: App is closing, skipping Cursor restart and account reload.")
                    return

                # 嘗試重新啟動 Cursor
                try:
                    print("嘗試重新啟動 Cursor...")
                    cursor_exe_paths = [
                        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Cursor", "Cursor.exe"),
                        os.path.join(os.environ.get("ProgramFiles", ""), "Cursor", "Cursor.exe"),
                        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Cursor", "Cursor.exe")
                    ]
                    
                    cursor_started = False
                    for path in cursor_exe_paths:
                        if os.path.exists(path):
                            print(f"找到 Cursor.exe 於: {path}")
                            
                            # 使用更穩定的方式啟動 Cursor
                            try:
                                # 在 Windows 上使用特定標誌啟動 Cursor
                                if os.name == 'nt':
                                    # 創建啟動信息對象以隱藏命令提示符
                                    startup_info = subprocess.STARTUPINFO()
                                    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                                    startup_info.wShowWindow = 0  # SW_HIDE
                                    
                                    # 啟動 Cursor 並分離進程
                                    proc = subprocess.Popen(
                                        [path],
                                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                                        close_fds=True,
                                        startupinfo=startup_info
                                    )
                                else:  # Unix/Linux/Mac
                                    proc = subprocess.Popen(
                                        [path],
                                        start_new_session=True,
                                        close_fds=True
                                    )
                                
                                print(f"已從 {path} 成功啟動 Cursor (PID: {proc.pid})。")
                                page.overlay.append(ft.SnackBar(ft.Text(f"已從 {path} 啟動 Cursor，請等待它啟動。"), open=True, duration=5000))
                                cursor_started = True
                                break
                            except Exception as popen_ex:
                                print(f"使用增強方式啟動 Cursor 時出錯: {str(popen_ex)}")
                                
                                # 回退到基本啟動方式
                                try:
                                    subprocess.Popen([path])
                                    print(f"已嘗試使用基本方式從 {path} 啟動 Cursor。")
                                    page.overlay.append(ft.SnackBar(ft.Text(f"使用基本方式啟動 Cursor。"), open=True, duration=5000))
                                    cursor_started = True
                                    break
                                except Exception as basic_ex:
                                    print(f"使用基本方式啟動 Cursor 時出錯: {str(basic_ex)}")
                    
                    if not cursor_started:
                        print("錯誤: 找不到 Cursor.exe。請手動啟動 Cursor。")
                        page.overlay.append(ft.SnackBar(ft.Text("找不到 Cursor.exe，請手動啟動。"), open=True))
                except Exception as start_error:
                    print(f"啟動 Cursor 時出錯: {str(start_error)}")
                    page.overlay.append(ft.SnackBar(ft.Text(f"啟動 Cursor 時出錯: {str(start_error)}"), open=True))

                if _app_is_closing: # <--- 在重新載入帳號和更新 UI 前再次檢查
                    print("use_account: App is closing after Cursor launch attempt, skipping account reload and UI updates.")
                    return

            else: # 如果更新認證資料庫失敗 (例如，令牌無效)
                # 顯示提示選中但未實際切換 (如果 auth_manager.update_from_saved_account 返回 False)
                current_account_text.value = f"當前選中帳號: {email} (未啟用 - 更新失敗)"
                current_account_password_field.value = account.get('password', '')
                current_account_password_field.visible = True
                page.overlay.append(ft.SnackBar(ft.Text(f"選中帳號 {email}，但自動更新失敗，請手動登入或檢查令牌。"), open=True))


            # 重新載入帳號管理器 (這主要影響 accounts_manager 內存中的列表，UI更新依賴 _flet_page_instance)
            reload_accounts_manager() 
            
            if _app_is_closing: # <--- 在最終 UI 更新前再次檢查
                print("use_account: App is closing, skipping final UI updates.")
                return

            # 更新界面
            try:
                current_account_text.update()
                current_account_password_field.update()
                page.update()
            except RuntimeError as e:
                print(f"use_account: Final UI update failed (loop likely closed): {str(e)}")
            except Exception as e:
                 print(f"use_account: Unexpected error during final UI update: {str(e)}")

        except Exception as e:
            error_msg = f"使用帳號時出錯: {str(e)}"
            print(error_msg)
            page.overlay.append(ft.SnackBar(ft.Text(error_msg), open=True))
            page.update()
    
    # 刪除帳號
    def delete_account(email):
        try:
            if accounts_manager.delete_account(email):
                page.overlay.append(ft.SnackBar(ft.Text(f"已成功刪除帳號: {email}"), open=True))
                refresh_account_list()
            else:
                page.overlay.append(ft.SnackBar(ft.Text(f"刪除帳號失敗: {email}"), open=True))
        except Exception as e:
            page.overlay.append(ft.SnackBar(ft.Text(f"刪除帳號時出錯: {str(e)}"), open=True))
        page.update()

    # 顯示當前使用的帳號
    current_account_text = ft.Text("當前帳號: 無", style=ft.TextStyle(italic=True))
    current_account_password_field = ft.TextField(
        label="密碼",
        read_only=True,
        password=True,
        can_reveal_password=True,
        value="",
        visible=False,
        border=ft.InputBorder.NONE,
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        text_size=14,
        width=300,
    )

    # 建立帳號清單
    account_list = ft.ListView(
        expand=True,
        spacing=5,  # 減少項目間間距
        padding=0,  # 移除內邊距
        auto_scroll=True,
        height=None  # 設為None以允許完全展開
    )
    
    # 刷新帳號清單和顯示當前帳號
    def refresh_current_account():
        global _app_is_closing, current_account_email, accounts_manager # <--- 添加 accounts_manager
        if _app_is_closing:
            print("refresh_current_account: App is closing, skipping UI updates.")
            return
            
        try:
            auth_manager = CursorAuthManager()
            current_auth = auth_manager.get_current_auth()
            if current_auth and current_auth.get('email'):
                email = current_auth['email']
                current_account_text.value = f"當前帳號: {email}"
                print(f"當前使用帳號: {email}")
                
                # 更新全局變數
                current_account_email = email
                
                # 嘗試從 AccountsManager 中獲取密碼
                account_info = accounts_manager.get_account(email)
                if account_info and account_info.get('password'):
                    current_account_password_field.value = account_info.get('password')
                else:
                    current_account_password_field.value = "無密碼"
                
                # 無論是否找到密碼，都顯示密碼欄位
                current_account_password_field.visible = True
            else:
                current_account_text.value = "當前帳號: 無"
                current_account_password_field.value = "無帳號"
                current_account_password_field.visible = False
                print("目前沒有登入的帳號")
            current_account_text.update()
            current_account_password_field.update()
        except RuntimeError as e: # <--- 捕獲 RuntimeError
            print(f"獲取當前帳號時 UI 更新失敗 (loop likely closed): {str(e)}")
        except Exception as e:
            print(f"獲取當前帳號時出錯: {str(e)}")
    
    # 預先宣告函式
    def reset_id_action(e):
        print("啟動重置機器碼流程...")
        # 1. 先退出可能正在運行的 Cursor
        try:
            from exit_cursor import ExitCursor
            ExitCursor()
            print("已關閉正在運行的 Cursor 應用")
        except Exception as exit_error:
            print(f"嘗試關閉 Cursor 時出錯: {str(exit_error)}")
        
        # 2. 執行重置機器碼腳本
        run_script("reset_machine.py")
        
    # 定義運行腳本的函數，這樣 reset_id_action 可以使用它
    def run_script(script_name: str, args: list = None):
        # 在 run_script 的外層作用域聲明，以便 task 函數可以訪問並修改 page 和按鈕狀態
        # (或者將 page 和按鈕作為參數傳遞給 task，但目前它們是 main 函數作用域的)

        def task():
            global g_keep_alive_process # 允許在 task 中修改全局變數
            process = None # 初始化 process 變數
            output_buffer = ""  # 收集輸出
            account_info = None  # 存儲解析的帳號信息
            
            try:
                command = [sys.executable, script_name]
                if args:
                    command.extend(args)
                
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["RUNNING_IN_GUI"] = "1"  # 設置環境變數告知腳本在 GUI 中運行
                
                # 如果是 cursor_pro_keep_alive.py 則使用管道通信
                if script_name == "cursor_pro_keep_alive.py":
                    global manual_verification_code
                    manual_verification_code = None
                    
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                              stdin=subprocess.PIPE, text=True, encoding='utf-8', 
                                              errors='replace', bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW 
                                              if os.name == 'nt' else 0, env=env)
                    g_keep_alive_process = process # 保存進程實例
                    
                    # 啟動一個線程檢查是否需要輸入驗證碼
                    def check_for_verification_code():
                        global manual_verification_code
                        while process.poll() is None:
                            if manual_verification_code:
                                try:
                                    process.stdin.write(manual_verification_code + "\n")
                                    process.stdin.flush()
                                    manual_verification_code = None
                                except Exception as e:
                                    print(f"無法寫入驗證碼: {str(e)}")
                            time.sleep(0.5)
                    
                    verification_thread = threading.Thread(target=check_for_verification_code)
                    verification_thread.daemon = True
                    verification_thread.start()
                    
                else:
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                             text=True, encoding='utf-8', errors='replace', bufsize=1, 
                                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, env=env)
                
                # 修改標準輸出讀取函數以收集輸出並監控註冊信息
                def read_output(stream, prefix=""):
                    nonlocal output_buffer, account_info
                    for line in iter(stream.readline, ''):
                        line = line.strip()
                        if line:  # 只處理非空行
                            # 收集輸出
                            output_buffer += line + "\n"
                            
                            # 檢查是否包含註冊完成的標記
                            if "=== 注册完成 ===" in line:
                                print("檢測到註冊完成信號，開始解析帳號信息...")
                            
                            # 檢查是否存在儲存帳號資訊時出錯的信息
                            if "儲存帳號資訊時出錯" in line and "datetime" in line:
                                print("檢測到帳號儲存錯誤，將嘗試手動解析並儲存...")
                                # 如果前面的輸出已經包含了完整的帳號信息
                                parsed_info = parse_registration_output(output_buffer)
                                if parsed_info:
                                    account_info = parsed_info
                                    # 直接儲存帳號
                                    direct_add_account(account_info['email'], account_info['password'])
                            
                            # 輸出到介面
                            if prefix and "error" in line.lower():  # 只在實際錯誤時添加前綴
                                print(f"{prefix} {line}")
                            else:
                                print(line)
                            page.update()
                
                # 創建並啟動讀取標準輸出的線程
                stdout_thread = threading.Thread(
                    target=read_output,
                    args=(process.stdout, ""),
                    daemon=True
                )
                stdout_thread.start()
                
                # 創建並啟動讀取標準錯誤的線程
                stderr_thread = threading.Thread(
                    target=read_output,
                    args=(process.stderr, "[錯誤]"),
                    daemon=True
                )
                stderr_thread.start()
                
                # 等待進程結束
                process.wait()

                # 如果進程結束後我們還沒有儲存帳號，進行最後一次嘗試
                if script_name == "cursor_pro_keep_alive.py" and process.returncode == 0 and not account_info:
                    parsed_info = parse_registration_output(output_buffer)
                    if parsed_info:
                        account_info = parsed_info
                        direct_add_account(account_info['email'], account_info['password'])

                # ----- 開始: 新增解析和列印帳號資訊的邏輯 -----
                if script_name == "cursor_pro_keep_alive.py" and process.returncode == 0:
                    full_output = "".join(process.stdout.readlines()) # 確保讀取所有輸出
                    print(f"來自 {script_name} 的原始輸出: {full_output}") # 列印原始輸出以供調試
                    try:
                        # 嘗試找到 JSON 部分 (假設 JSON 被明確標記或在特定位置)
                        # 這裡假設 JSON 物件是輸出的主要部分，或者有特定標記
                        # 一個簡單的假設是，JSON 以 '{' 開始並以 '}' 或 ']' 結束
                        # 您可能需要更複雜的解析邏輯，取決於腳本的實際輸出格式
                        
                        json_output = None
                        # 嘗試從輸出中提取 JSON，假設它可能被包裹在其他文本中
                        # 或者直接就是 JSON 字符串
                        # 這裡需要一個健壯的方法來提取 JSON，以下是一個基本嘗試
                        
                        # 嘗試直接解析整個輸出，如果它是純 JSON
                        try:
                            parsed_account_info = json.loads(full_output)
                            json_output = parsed_account_info
                        except json.JSONDecodeError:
                            # 如果直接解析失敗，嘗試在輸出中尋找 JSON 結構
                            # 這是一個非常基礎的查找，可能需要改進
                            json_start_brace = full_output.find('{')
                            json_start_bracket = full_output.find('[')
                            
                            json_start = -1
                            if json_start_brace != -1 and (json_start_bracket == -1 or json_start_brace < json_start_bracket):
                                json_start = json_start_brace
                            elif json_start_bracket != -1:
                                json_start = json_start_bracket
                                
                            if json_start != -1:
                                # 假設 JSON 物件是連續的
                                # 查找匹配的結束符號可能很複雜，特別是對於巢狀結構
                                # 為了簡化，我們先假設 JSON 是輸出中的最後一個主要結構
                                # 或者我們可以依賴於腳本輸出一個格式良好的單行 JSON
                                if full_output.strip().startswith( ("{", "[") ) and full_output.strip().endswith( ("}", "]") ):
                                     potential_json_str = full_output.strip()
                                     try:
                                         parsed_account_info = json.loads(potential_json_str)
                                         json_output = parsed_account_info
                                     except json.JSONDecodeError as je:
                                         print(f"提取的 JSON 字串解析失敗: {je}")
                                else: # 如果不是純JSON，嘗試從找到的起始點開始解析
                                    try:
                                        parsed_account_info = json.loads(full_output[json_start:])
                                        json_output = parsed_account_info
                                    except json.JSONDecodeError as je:
                                        print(f"從索引 {json_start} 開始的 JSON 解析失敗: {je}")
                                        # 可以嘗試更複雜的查找匹配的括號的邏輯，但這裡從簡
                                        # 例如，如果JSON物件後還有其他輸出，上面的解析會失敗
                                        # 一個更可靠的方法是讓 cursor_pro_keep_alive.py
                                        # 用一個明確的標記來包圍JSON輸出，例如
                                        # print("ACCOUNT_JSON_START")
                                        # print(json.dumps(account_details))
                                        # print("ACCOUNT_JSON_END")
                                        # 然後在這裡查找這些標記

                        if json_output:
                            print(f"從 {script_name} 解析到的帳號資訊: {json.dumps(json_output, indent=2, ensure_ascii=False)}")
                            
                            # 假設 json_output 是一個包含帳號詳細資訊的字典
                            # 或者是一個包含單個帳號字典的列表
                            
                            account_to_add = None
                            if isinstance(json_output, list) and len(json_output) > 0:
                                account_to_add = json_output[0] # 取列表中的第一個元素
                            elif isinstance(json_output, dict):
                                account_to_add = json_output

                            if account_to_add and isinstance(account_to_add, dict):
                                email = account_to_add.get("email")
                                password = account_to_add.get("password") # 確保 password 存在
                                access_token = account_to_add.get("token") # JSON 中是 token
                                user_id = account_to_add.get("user")       # JSON 中是 user
                                cookie = account_to_add.get("cookie")
                                membership = account_to_add.get("membership")
                                account_status = account_to_add.get("account_status")
                                usage = account_to_add.get("usage")
                                created_at = account_to_add.get("created_at")

                                if email and password: # 假設 email 和 password 是必要的
                                    print(f"準備將解析到的帳號添加到 AccountsManager: {email}")
                                    if accounts_manager.add_account(
                                        email=email,
                                        password=password,
                                        access_token=access_token,
                                        user_id=user_id, # 傳遞 user_id
                                        cookie=cookie,
                                        membership=membership,
                                        account_status=account_status,
                                        usage=usage,
                                        created_at_override=created_at # 傳遞覆蓋的創建時間
                                    ):
                                        print(f"帳號 {email} 已成功添加到 AccountsManager。")
                                        refresh_account_list() # 更新GUI中的帳號列表
                                    else:
                                        print(f"帳號 {email} 添加到 AccountsManager 失敗。")
                                else:
                                    print(f"從 {script_name} 的輸出中未能解析出必要的 email 或 password。")
                            else:
                                print(f"從 {script_name} 的輸出中未能正確解析出帳號字典。")
                        else:
                            print(f"未能從 {script_name} 的輸出中解析出 JSON 帳號資訊。")
                    except Exception as ex_parse:
                        print(f"解析 {script_name} 輸出時發生錯誤: {str(ex_parse)}")
                # ----- 結束: 新增解析和列印帳號資訊的邏輯 -----
                
                # 等待讀取線程結束
                stdout_thread.join()
                
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()

                print(f"\n{script_name} 執行完成，返回碼: {process.returncode}")
            except Exception as ex:
                print(f"\n執行 {script_name} 時發生錯誤: {str(ex)}")
            finally:
                if script_name == "cursor_pro_keep_alive.py":
                    auto_register_button.disabled = False
                    stop_auto_register_button.disabled = True # 禁用停止按鈕
                    auto_register_button.update()
                    stop_auto_register_button.update()
                    g_keep_alive_process = None # 清理進程實例
                    
                    # 嘗試解析帳號資訊並保存
                    if json_output:
                        print(f"從 {script_name} 解析到的帳號資訊: {json.dumps(json_output, indent=2, ensure_ascii=False)}")
                        
                        # 假設 json_output 是一個包含帳號詳細資訊的字典
                        # 或者是一個包含單個帳號字典的列表
                        
                        account_to_add = None
                        if isinstance(json_output, list) and len(json_output) > 0:
                            account_to_add = json_output[0] # 取列表中的第一個元素
                        elif isinstance(json_output, dict):
                            account_to_add = json_output

                        if account_to_add and isinstance(account_to_add, dict):
                            email = account_to_add.get("email")
                            password = account_to_add.get("password") # 確保 password 存在
                            access_token = account_to_add.get("token") # JSON 中是 token
                            user_id = account_to_add.get("user")       # JSON 中是 user
                            cookie = account_to_add.get("cookie")
                            membership = account_to_add.get("membership")
                            account_status = account_to_add.get("account_status")
                            usage = account_to_add.get("usage")
                            created_at = account_to_add.get("created_at")

                            if email and password: # 假設 email 和 password 是必要的
                                print(f"準備將解析到的帳號添加到 AccountsManager: {email}")
                                if accounts_manager.add_account(
                                    email=email,
                                    password=password,
                                    access_token=access_token,
                                    user_id=user_id, # 傳遞 user_id
                                    cookie=cookie,
                                    membership=membership,
                                    account_status=account_status,
                                    usage=usage,
                                    created_at_override=created_at # 傳遞覆蓋的創建時間
                                ):
                                    print(f"帳號 {email} 已成功添加到 AccountsManager。")
                                    refresh_account_list() # 更新GUI中的帳號列表
                                else:
                                    print(f"帳號 {email} 添加到 AccountsManager 失敗。")
                            else:
                                print(f"從 {script_name} 的輸出中未能解析出必要的 email 或 password。")
                        else:
                            print(f"從 {script_name} 的輸出中未能正確解析出帳號字典。")
                    else:
                        print(f"未能從 {script_name} 的輸出中解析出 JSON 帳號資訊。")
                elif script_name == "reset_machine.py":
                    reset_id_button.disabled = False
                    reset_id_button.update()
                page.update()

        print(f"開始執行 {script_name}...")
        if script_name == "cursor_pro_keep_alive.py":
            auto_register_button.disabled = True
            stop_auto_register_button.disabled = False # 啟用停止按鈕
            auto_register_button.update()
            stop_auto_register_button.update()
        elif script_name == "reset_machine.py":
            reset_id_button.disabled = True
            reset_id_button.update()
        page.update()
        
        thread = threading.Thread(target=task)
        thread.daemon = True
        thread.start()
        
    def auto_register_action(e):
        print("啟動自動註冊流程...")
        
        # 將執行方式從命令行參數改為直接調用函數
        try:
            # 導入cursor_pro_keep_alive模組
            import cursor_pro_keep_alive
            import traceback # 確保 traceback 可用
            
            # 禁用按鈕以避免重複點擊
            auto_register_button.disabled = True
            stop_auto_register_button.disabled = False
            auto_register_button.update()
            stop_auto_register_button.update()
            page.update()
            
            # 創建一個執行註冊流程的線程
            def run_registration():
                try:
                    # 設置環境變數，確保無頭模式設置正確
                    headless = os.getenv("BROWSER_HEADLESS", "True").lower() == "true"
                    print(f"使用瀏覽器模式: {'無頭模式' if headless else '有頭模式'}")
                    
                    # 直接調用sign_up_and_save函數
                    result = cursor_pro_keep_alive.sign_up_and_save(headless=headless)
                    
                    if result:
                        print("自動註冊流程成功完成！")
                        
                        # 詢問是否重啟應用程式
                        def show_restart_confirm():
                            restart_dialog = ft.AlertDialog(
                                title=ft.Row([
                                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                                    ft.Text("註冊成功", color=ft.Colors.GREEN)
                                ]),
                                content=ft.Text("註冊成功，帳號已儲存！是否要重新啟動應用程式以更新帳號列表？"),
                                actions=[
                                    ft.TextButton("否", on_click=lambda e: close_restart_dialog(e, restart_dialog, False)),
                                    ft.TextButton("是", on_click=lambda e: close_restart_dialog(e, restart_dialog, True))
                                ],
                                actions_alignment=ft.MainAxisAlignment.END,
                                open=True
                            )
                            
                            page.overlay.append(restart_dialog)
                            page.update()
                        
                        def close_restart_dialog(e, dialog, should_restart):
                            dialog.open = False
                            page.update()
                            
                            if should_restart:
                                # 在關閉對話框後重啟 GUI，顯示明確的提示
                                page.overlay.append(ft.SnackBar(ft.Text("註冊成功，正在重啟應用..."), open=True))
                                page.update()
                                # 延遲一點時間讓提示訊息顯示出來
                                threading.Timer(1.0, restart_gui_app).start()
                            else:
                                # 僅刷新帳號列表
                                refresh_account_list()
                                page.overlay.append(ft.SnackBar(ft.Text("註冊成功，帳號已儲存！"), open=True))
                        
                        page.run_thread_safe(show_restart_confirm)
                    else:
                        print("自動註冊流程未能成功完成。")
                        page.overlay.append(ft.SnackBar(ft.Text("註冊失敗，請查看日誌了解詳情。"), open=True))
                except Exception as ex:
                    # 捕獲並顯示詳細的錯誤信息
                    error_details = traceback.format_exc()
                    print(f"執行註冊流程時發生錯誤: {str(ex)}")
                    print(f"錯誤詳情: {error_details}")
                    page.overlay.append(ft.SnackBar(ft.Text(f"註冊錯誤: {str(ex)}"), open=True))
                finally:
                    # 重新啟用按鈕
                    auto_register_button.disabled = False
                    stop_auto_register_button.disabled = True
                    auto_register_button.update()
                    stop_auto_register_button.update()
                    page.update()
                    
            # 啟動註冊線程
            thread = threading.Thread(target=run_registration)
            thread.daemon = True
            thread.start()
            
        except ImportError as ie:
            print(f"無法導入cursor_pro_keep_alive模組: {str(ie)}")
            # 如果導入失敗，則回退到舊的執行方式
            run_script("cursor_pro_keep_alive.py", args=["--mode", "2"])
        except Exception as ex:
            error_details = traceback.format_exc() if 'traceback' in sys.modules else "無法獲取詳細錯誤信息"
            print(f"啟動自動註冊流程時發生錯誤: {str(ex)}")
            print(f"錯誤詳情: {error_details}")
            page.overlay.append(ft.SnackBar(ft.Text(f"啟動註冊失敗: {str(ex)}"), open=True))
            page.update()

    # 解析標準輸出並找出註冊資訊
    def parse_registration_output(output):
        try:
            # 移除ANSI控制碼
            def remove_ansi_codes(text):
                import re
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                return ansi_escape.sub('', text) if isinstance(text, str) else text
            
            # 先對整個輸出進行清理
            output = remove_ansi_codes(output)
            
            # 尋找包含帳號資訊的行
            email = None
            password = None
            
            # 匹配郵箱 - 增加更多可能的模式
            email_patterns = [
                r'邮箱: ([^\s]+@[^\s]+)',
                r'郵箱: ([^\s]+@[^\s]+)',
                r'账号: ([^\s]+@[^\s]+)',
                r'帳號: ([^\s]+@[^\s]+)',
                r'Email: ([^\s]+@[^\s]+)',
                r'email: ([^\s]+@[^\s]+)'
            ]
            
            for pattern in email_patterns:
                email_match = re.search(pattern, output)
                if email_match:
                    email = email_match.group(1).strip()
                    break
                
            # 匹配密碼 - 增加更多可能的模式
            password_patterns = [
                r'密码: ([^\s]+)',
                r'密碼: ([^\s]+)',
                r'Password: ([^\s]+)',
                r'password: ([^\s]+)'
            ]
            
            for pattern in password_patterns:
                password_match = re.search(pattern, output)
                if password_match:
                    password = password_match.group(1).strip()
                    break
            
            # 進一步清理郵箱和密碼
            if email:
                email = remove_ansi_codes(email).strip()
            if password:
                password = remove_ansi_codes(password).strip()
                
            if email and password:
                print(f"從輸出中解析到帳號: {email}, 密碼: {password}")
                return {'email': email, 'password': password}
            else:
                print("無法從輸出中解析出帳號資訊")
                return None
        except Exception as ex:
            print(f"解析註冊輸出時出錯: {str(ex)}")
            traceback.print_exc() if 'traceback' in sys.modules else None
            return None

    # 新增一個直接添加帳號的函數
    def direct_add_account(email, password):
        try:
            # 移除ANSI控制碼
            def remove_ansi_codes(text):
                if not text:
                    return text
                import re
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                return ansi_escape.sub('', text) if isinstance(text, str) else text
            
            # 清理郵箱和密碼中的控制碼和多餘空白
            email = remove_ansi_codes(email).strip() if email else None
            password = remove_ansi_codes(password).strip() if password else None
            
            if not email or not password:
                print(f"錯誤：郵箱或密碼為空，無法添加帳號。郵箱: {email}, 密碼: {password}")
                return False
            
            print(f"嘗試直接添加帳號: {email}")
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 改進添加帳號的方式，增加錯誤處理
            try:
                # 添加到管理器
                if accounts_manager.add_account(
                    email=email,
                    password=password,
                    created_at_override=current_time
                ):
                    print(f"帳號 {email} 已成功添加到 AccountsManager。")
                    refresh_account_list()  # 更新GUI中的帳號列表
                    # 顯示成功提示
                    page.overlay.append(ft.SnackBar(ft.Text(f"帳號 {email} 已成功儲存！"), open=True))
                    page.update()
                    return True
                else:
                    print(f"帳號 {email} 添加到 AccountsManager 失敗。")
                    # 再嘗試一次，使用物件屬性設定的方式
                    print("嘗試使用替代方法添加帳號...")
                    
                    # 直接儲存到JSON檔案
                    try:
                        import json
                        import os
                        
                        # 讀取現有帳號
                        accounts_file = accounts_manager.accounts_file
                        accounts = []
                        if os.path.exists(accounts_file):
                            try:
                                with open(accounts_file, 'r', encoding='utf-8') as f:
                                    accounts = json.load(f)
                            except:
                                print(f"讀取帳號檔案失敗，將創建新檔案")
                        
                        # 檢查是否已存在該帳號
                        for account in accounts:
                            if account.get('email') == email:
                                account['password'] = password
                                account['updated_at'] = current_time
                                print(f"透過直接JSON操作更新現有帳號")
                                break
                        else:
                            # 添加新帳號
                            new_account = {
                                'email': email,
                                'password': password,
                                'created_at': current_time,
                                'updated_at': current_time
                            }
                            accounts.append(new_account)
                            print(f"透過直接JSON操作添加新帳號")
                        
                        # 保存到檔案
                        with open(accounts_file, 'w', encoding='utf-8') as f:
                            json.dump(accounts, f, ensure_ascii=False, indent=2)
                        
                        print(f"通過直接操作JSON成功儲存帳號")
                        refresh_account_list()  # 更新GUI中的帳號列表
                        page.overlay.append(ft.SnackBar(ft.Text(f"帳號 {email} 已成功儲存！"), open=True))
                        page.update()
                        return True
                    except Exception as json_ex:
                        print(f"直接操作JSON檔案失敗: {str(json_ex)}")
                        return False
            except Exception as add_ex:
                print(f"添加帳號到管理器時出錯: {str(add_ex)}")
                return False
        except Exception as ex:
            print(f"直接添加帳號時出錯: {str(ex)}")
            traceback.print_exc() if 'traceback' in sys.modules else None
            return False

    # 停止自動註冊
    def stop_auto_register_action(e): # 新增：停止自動註冊的動作
        global g_keep_alive_process
        
        print("嘗試停止自動註冊流程...")
        
        # 檢查是否存在命令行方式啟動的進程
        if g_keep_alive_process and g_keep_alive_process.poll() is None:
            try:
                g_keep_alive_process.terminate()
                g_keep_alive_process.wait(timeout=5) # 等待最多5秒讓進程結束
                print("自動註冊進程已請求停止。")
                page.overlay.append(ft.SnackBar(ft.Text("自動註冊進程已請求停止。"), open=True))
            except subprocess.TimeoutExpired:
                print("停止進程超時，可能需要手動檢查。")
                page.overlay.append(ft.SnackBar(ft.Text("停止進程超時。"), open=True))
            except Exception as ex_terminate:
                print(f"停止自動註冊進程時出錯: {str(ex_terminate)}")
                page.overlay.append(ft.SnackBar(ft.Text(f"停止進程出錯: {str(ex_terminate)}"), open=True))
            finally:
                # 確保按鈕狀態被重置
                if auto_register_button.disabled:
                    auto_register_button.disabled = False
                    auto_register_button.update()
                if not stop_auto_register_button.disabled:
                    stop_auto_register_button.disabled = True
                    stop_auto_register_button.update()
                g_keep_alive_process = None # 清理全局變數
        else:
            # 無命令行進程，但仍處理UI狀態
            if auto_register_button.disabled:
                print("直接調用方式的註冊無法停止，但已重置UI狀態。")
                auto_register_button.disabled = False
                auto_register_button.update()
            if not stop_auto_register_button.disabled:
                stop_auto_register_button.disabled = True
                stop_auto_register_button.update()
            page.overlay.append(ft.SnackBar(ft.Text("已重置註冊按鈕狀態，但當前註冊流程可能仍在後台運行。"), open=True))
        
        page.update()
    
    # 帳號管理標籤頁
    accounts_view = ft.Column([
        ft.Row([
            ft.Text("當前帳號", size=20, weight=ft.FontWeight.BOLD),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                tooltip="刷新當前帳號",
                on_click=lambda e: refresh_current_account()
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=ft.Colors.BLUE, size=24),
                        current_account_text,
                    ]),
                    ft.Row([
                        current_account_password_field,
                    ], spacing=5),
                ]),
                padding=10,
                width=500
            ),
            margin=ft.margin.only(bottom=10)  # 減少底部間距
        ),
        ft.Row([
            ft.Text("已儲存的帳號", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE,
                    tooltip="添加新帳號",
                    on_click=show_add_account_dialog
                ),
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    tooltip="刷新帳號列表",
                    on_click=lambda e: refresh_account_list()
                )
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(height=1, thickness=1),  # 減少分隔線高度
        ft.Container(
            content=account_list,
            expand=True,  # 確保列表擴展到底部
            padding=0,  # 移除內邊距
            margin=0  # 移除外邊距
        )
    ], 
    spacing=5,  # 減少元素間距
    expand=True,  # 確保整個列擴展填充可用空間
    scroll=ft.ScrollMode.AUTO)

    # --- 設定相關控制項 ---
    # DOMAIN
    domain_field = ft.TextField(label="域名 (DOMAIN)", hint_text="例如：yourdomain.com")

    # 郵箱模式
    email_mode_radio_group = ft.RadioGroup(content=ft.Row([
        ft.Radio(value="temp_mail", label="使用臨時郵箱"),
        ft.Radio(value="imap", label="使用 IMAP 郵箱 (待開發)"),
    ]), value="temp_mail") # 預設選中臨時郵箱

    # 臨時郵箱配置
    temp_mail_ext_field = ft.TextField(label="臨時郵箱地址 (TEMP_MAIL_EXT)", hint_text="請輸入完整的臨時郵箱地址，例如 user123@example.com")
    temp_mail_epin_field = ft.TextField(label="臨時郵箱 PIN 碼 (TEMP_MAIL_EPIN)", password=True, can_reveal_password=True)

    temp_mail_config_column = ft.Column([
        ft.Text("臨時郵箱配置", weight=ft.FontWeight.BOLD),
        temp_mail_ext_field,
        temp_mail_epin_field,
    ])

    # IMAP 配置 (佔位)
    imap_config_column = ft.Column([
        ft.Text("IMAP 郵箱配置 (待開發)", weight=ft.FontWeight.BOLD),
        ft.TextField(label="IMAP 伺服器", disabled=True),
        ft.TextField(label="IMAP 連接埠", disabled=True),
        ft.TextField(label="IMAP 用戶名", disabled=True),
        ft.TextField(label="IMAP 密碼", disabled=True, password=True),
    ], visible=False) # IMAP 初始隱藏

    def on_email_mode_change(e):
        is_temp_mail = email_mode_radio_group.value == "temp_mail"
        temp_mail_config_column.visible = is_temp_mail
        imap_config_column.visible = not is_temp_mail
        temp_mail_config_column.update()
        imap_config_column.update()
        page.update()
    email_mode_radio_group.on_change = on_email_mode_change


    # 瀏覽器模式 (使用 .env 變數 BROWSER_HEADLESS: "True" 為無頭，"false" 為有頭)
    browser_mode_radio_group = ft.RadioGroup(content=ft.Row([
        ft.Radio(value="True", label="無頭瀏覽器"),
        ft.Radio(value="false", label="有頭瀏覽器 (用於偵錯)"),
    ]), value="True")

    env_file_path = ".env"

    def parse_env_file(file_path):
        env_vars = {}
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value_part = line.split("=", 1)
                        
                        # 移除行內註解 (從第一個 # 開始)
                        if "#" in value_part:
                            value_part = value_part.split("#", 1)[0]
                        
                        value = value_part.strip() # 移除值前後的空白
                        
                        # 移除值兩端的引號 (如果有的話)
                        if (value.startswith("'") and value.endswith("'")) or \
                           (value.startswith('"') and value.endswith('"')):
                            value = value[1:-1]
                        
                        env_vars[key.strip()] = value # 儲存處理後的值
        return env_vars

    def load_env_to_gui(e=None):
        try:
            # 我們不再直接依賴 Config() 實例來填充 GUI，因為 Config() 會在找不到 .env 時拋錯
            # 而是直接解析 .env 檔案
            env_vars = parse_env_file(env_file_path)

            domain_field.value = env_vars.get("DOMAIN", "")
            
            # 郵箱模式判斷：如果 TEMP_MAIL 存在且不為 "null"，則認為是臨時郵箱模式
            # 否則，如果 IMAP_SERVER 存在，則為 IMAP 模式 (這部分 IMAP 邏輯先簡化)
            if env_vars.get("TEMP_MAIL") and env_vars.get("TEMP_MAIL").lower() != "null":
                email_mode_radio_group.value = "temp_mail"
            elif env_vars.get("IMAP_SERVER"): # 簡化判斷
                 email_mode_radio_group.value = "imap"
            else:
                email_mode_radio_group.value = "temp_mail" # 預設
            
            temp_mail_ext_field.value = env_vars.get("TEMP_MAIL_EXT", "")
            temp_mail_epin_field.value = env_vars.get("TEMP_MAIL_EPIN", "")
            
            # IMAP (如果後續添加，從 env_vars.get(...) 獲取)

            # 讀取無頭瀏覽器設定，接受 'True'/'false'
            browser_headless = env_vars.get("BROWSER_HEADLESS", "True")
            # 刪除任何引號
            if browser_headless.startswith("'") and browser_headless.endswith("'"):
                browser_headless = browser_headless[1:-1]
            if browser_headless.startswith('"') and browser_headless.endswith('"'):
                browser_headless = browser_headless[1:-1]
            browser_mode_radio_group.value = browser_headless

            # 更新可見性
            on_email_mode_change(None) # 觸發一次以更新顯示

            # 更新所有欄位
            controls_to_update = [
                domain_field, email_mode_radio_group, 
                temp_mail_ext_field, temp_mail_epin_field,
                browser_mode_radio_group
            ]
            for ctrl in controls_to_update:
                ctrl.update()
            
        except Exception as ex:
            print(f"載入 .env 到 GUI 失敗: {str(ex)}")
            page.overlay.append(ft.SnackBar(ft.Text(f"載入設定失敗: {str(ex)}"), open=True))
        page.update()


    def save_gui_to_env(e=None):
        try:
            # 要更新的特定欄位
            target_keys = ["DOMAIN", "TEMP_MAIL", "TEMP_MAIL_EPIN", "TEMP_MAIL_EXT", "BROWSER_HEADLESS"]
            
            # 準備要更新的值
            env_updates = {}
            env_updates["DOMAIN"] = f"'{domain_field.value or 'cheyu0410.ip-ddns.com'}'"
            
            if email_mode_radio_group.value == "temp_mail":
                env_updates["TEMP_MAIL"] = "xxx"
                env_updates["TEMP_MAIL_EXT"] = temp_mail_ext_field.value or "zdaabz@mailto.plus"
                env_updates["TEMP_MAIL_EPIN"] = temp_mail_epin_field.value or "123"
            else:
                env_updates["TEMP_MAIL"] = "null"
            
            # 瀏覽器模式
            browser_headless = browser_mode_radio_group.value or "True"
            env_updates["BROWSER_HEADLESS"] = f"'{browser_headless}'"
            
            # 檢查 .env 檔案是否存在
            if not os.path.exists(env_file_path):
                print(f".env 檔案不存在，將建立新檔案。")
                
                # 建立新的 .env 檔案
                with open(env_file_path, "w", encoding="utf-8") as f:
                    f.write(open("correct_env.txt", "r", encoding="utf-8").read())
                    
            # 讀取現有 .env 檔案的所有行
            with open(env_file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 備份原始檔案
            with open(f"{env_file_path}.bak", "w", encoding="utf-8") as f:
                f.writelines(lines)
                
            # 逐行處理，只更新目標欄位
            updated_lines = []
            updated_keys = set()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    # 保留空行和註釋
                    updated_lines.append(line)
                    continue
                
                # 檢查是否為目標欄位
                found_key = False
                for key in target_keys:
                    if line.startswith(key + "=") or line.startswith(key + " ="):
                        # 更新這個欄位
                        if key in env_updates:
                            updated_lines.append(f"{key}={env_updates[key]}")
                            updated_keys.add(key)
                            found_key = True
                            break
                
                if not found_key:
                    # 保留其他欄位不變
                    updated_lines.append(line)
            
            # 檢查是否有欄位尚未更新（可能不存在於原始檔案）
            for key in target_keys:
                if key in env_updates and key not in updated_keys:
                    if key == "TEMP_MAIL_EPIN":
                        # 在 # 设置的PIN码 下方添加
                        pin_comment_idx = -1
                        for i, line in enumerate(updated_lines):
                            if "PIN" in line and line.startswith("#"):
                                pin_comment_idx = i
                                break
                        
                        if pin_comment_idx >= 0:
                            updated_lines.insert(pin_comment_idx + 1, f"{key}={env_updates[key]}")
                        else:
                            updated_lines.append(f"{key}={env_updates[key]}")
                    else:
                        # 直接添加到檔案末尾
                        updated_lines.append(f"{key}={env_updates[key]}")
            
            # 寫回檔案
            with open(env_file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(updated_lines))
            
            print(f".env 檔案已儲存。")
            
            # 詢問是否重啟應用程式來套用設定
            def show_restart_confirm():
                restart_dialog = ft.AlertDialog(
                    title=ft.Row([
                        ft.Icon(ft.Icons.SAVE, color=ft.Colors.GREEN),
                        ft.Text("設定已儲存", color=ft.Colors.GREEN)
                    ]),
                    content=ft.Column([
                        ft.Text("設定已成功儲存！某些設定可能需要重新啟動應用程式才能生效。"),
                        ft.Text("是否要立即重新啟動？", weight=ft.FontWeight.BOLD)
                    ]),
                    actions=[
                        ft.TextButton("否", on_click=lambda e: close_restart_dialog(e, restart_dialog, False)),
                        ft.ElevatedButton(
                            "是，立即重啟",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda e: close_restart_dialog(e, restart_dialog, True),
                            style=ft.ButtonStyle(
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.BLUE
                            )
                        )
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                    open=True
                )
                
                page.overlay.append(restart_dialog)
                page.update()
            
            def close_restart_dialog(e, dialog, should_restart):
                dialog.open = False
                page.update()
                
                if should_restart:
                    # 在關閉對話框後重啟 GUI，顯示明確的提示
                    page.overlay.append(ft.SnackBar(ft.Text("設定已儲存，正在重啟應用...", weight=ft.FontWeight.BOLD), open=True))
                    page.update()
                    # 延遲一點時間讓提示訊息顯示出來，並確保環境變數能被正確寫入並刷新
                    threading.Timer(1.5, restart_gui_app).start()
                else:
                    # 只顯示已儲存訊息
                    page.overlay.append(ft.SnackBar(ft.Text(".env 已儲存，但須重啟應用才能生效！"), open=True))
            
            show_restart_confirm()
            
        except Exception as ex:
            print(f"儲存 .env 失敗: {str(ex)}")
            traceback.print_exc()
            page.overlay.append(ft.SnackBar(ft.Text(f"儲存 .env 失敗: {str(ex)}"), open=True))
        page.update()


    settings_controls = [
        ft.Text("應用程式設定", size=20, weight=ft.FontWeight.BOLD),
        domain_field,
        ft.Divider(),
        ft.Text("郵箱配置", size=16, weight=ft.FontWeight.BOLD),
        email_mode_radio_group,
        temp_mail_config_column,
        imap_config_column, # IMAP 部分初始隱藏
        ft.Divider(),
        ft.Text("瀏覽器配置", size=16, weight=ft.FontWeight.BOLD),
        browser_mode_radio_group,
        ft.Divider(height=20),
        ft.Row([
            ft.ElevatedButton("儲存設定", icon=ft.Icons.SAVE, on_click=save_gui_to_env, tooltip="將以上設定儲存到 .env 檔案", width=150),
            # ft.ElevatedButton("重新載入設定", icon=ft.Icons.REFRESH, on_click=load_env_to_gui, tooltip="從 .env 檔案重新載入設定", width=180) # 載入在顯示時自動進行
        ], alignment=ft.MainAxisAlignment.END)
    ]

    settings_view = ft.Column(
        controls=settings_controls,
        visible=False,
        expand=True,
        alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        scroll=ft.ScrollMode.ADAPTIVE # 允許設定頁面內部滾動
    )

    def toggle_settings_view(e):
        settings_view.visible = not settings_view.visible
        if settings_view.visible:
            load_env_to_gui() # 載入當前 .env 值到 GUI
        settings_view.update()
        page.update()

    # --- 功能按鈕 ---
        # 下面有重複定義，使用前面的版本

    def clear_log_action(e):
        log_view.controls.clear()
        log_view.update()
        print("日誌已清空")
        
    def export_log_action(e):
        try:
            # 創建一個日誌檔案
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"cursor_log_{timestamp}.txt"
            
            # 獲取日誌內容
            log_content = ""
            for log_item in log_view.controls:
                if isinstance(log_item, ft.Text):
                    log_content += log_item.value + "\n"
            
            # 寫入檔案
            with open(log_filename, "w", encoding="utf-8") as f:
                f.write(log_content)
            
            print(f"日誌已匯出到檔案: {log_filename}")
            page.overlay.append(ft.SnackBar(ft.Text(f"日誌已匯出到: {log_filename}"), open=True))
            page.update()
            
            # 嘗試打開檔案所在目錄
            try:
                import os
                import subprocess
                if os.name == 'nt':  # Windows
                    os.startfile(os.path.dirname(os.path.abspath(log_filename)))
                elif os.name == 'posix':  # macOS 和 Linux
                    subprocess.call(['open', os.path.dirname(os.path.abspath(log_filename))])
            except:
                pass  # 忽略開啟目錄的錯誤
                
        except Exception as ex:
            print(f"匯出日誌時出錯: {str(ex)}")
            page.overlay.append(ft.SnackBar(ft.Text(f"匯出日誌失敗: {str(ex)}"), open=True))
            page.update()
    
    # 定義所有主要按鈕
    auto_register_button = ft.ElevatedButton(
        "自動註冊新帳號", icon=ft.Icons.PERSON_ADD_ALT_1, on_click=auto_register_action, tooltip="執行完整自動註冊流程"
    )
    stop_auto_register_button = ft.ElevatedButton( # 新增：停止註冊按鈕的定義
        "停止註冊",
        icon=ft.Icons.CANCEL,
        on_click=stop_auto_register_action,
        tooltip="停止正在進行的自動註冊流程",
        disabled=True # 初始禁用
    )
    reset_id_button = ft.ElevatedButton(
        "重置機器碼", icon=ft.Icons.COMPUTER, on_click=reset_id_action, tooltip="執行重置機器標識"
    )
    settings_button = ft.IconButton(
        icon=ft.Icons.SETTINGS, tooltip="打開/關閉設定", on_click=toggle_settings_view, icon_size=28
    )
    
    # 更新清空日誌按鈕
    clear_log_button = ft.IconButton(
        icon=ft.Icons.CLEANING_SERVICES, 
        tooltip="清空日誌內容", 
        on_click=clear_log_action, 
        icon_size=28
    )
    
    # 添加匯出日誌按鈕
    export_log_button = ft.IconButton(
        icon=ft.Icons.DOWNLOAD, 
        tooltip="匯出日誌", 
        on_click=export_log_action, 
        icon_size=28
    )
    
    # 更新按鈕區域
    action_buttons_row = ft.Row(
        [auto_register_button, stop_auto_register_button, reset_id_button, 
         ft.Container(expand=True), 
         export_log_button, clear_log_button, settings_button], 
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10
    )

    # --- 查看已設置的環境變數值 ---
    parse_env_file(env_file_path)

    # 添加 logo 和 banner
    logo_image = ft.Image(src="/YuCursor.png", width=50, height=50, fit=ft.ImageFit.CONTAIN) # 調整圖示大小
    banner_text = ft.Text("YuCursor", style=ft.TextStyle( # 修改標題文字
        size=24,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.BLUE_700
    ), text_align=ft.TextAlign.CENTER)

    title_row = ft.Row(
        [logo_image, banner_text],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10
    )

    # 原始頁面內容
    original_content = ft.Column([
        title_row, # 使用包含 logo 和 banner 的 Row
        ft.Row([
            auto_register_button,
            stop_auto_register_button,
            reset_id_button,
            ft.Container(expand=True),
            export_log_button,
            clear_log_button,
            settings_button
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=10),
        settings_view,
        log_container  # 直接使用log_container
    ], 
    spacing=10,  # 減少間距以提供更多的空間給日誌視圖
    expand=True
    )

        # 添加標籤頁切換事件
    def on_tab_change(e):
        if e.control.selected_index == 2:  # 索引已改變，現在帳號管理是第2個標籤頁（從0開始計數）
            refresh_account_list()
            refresh_current_account()
            
        # 創建主頁內容    home_content = ft.Column([        ft.Container(            content=ft.Column([                ft.Row([logo_image, banner_text], alignment=ft.MainAxisAlignment.CENTER),                ft.Divider(),                ft.Text("歡迎使用 YuCursor", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),                ft.Text("一個專為 Cursor 編輯器設計的帳號管理和自動化工具", text_align=ft.TextAlign.CENTER),                ft.Container(height=20),                ft.Text("功能概述:", size=16, weight=ft.FontWeight.BOLD),                ft.Text("• 自動註冊新帳號 - 透過自動化流程創建新的 Cursor 帳號", text_align=ft.TextAlign.LEFT),                ft.Text("• 帳號管理 - 儲存和管理多個 Cursor 帳號，方便快速切換", text_align=ft.TextAlign.LEFT),                ft.Text("• 重置機器碼 - 重置機器識別碼，解決一些登入限制問題", text_align=ft.TextAlign.LEFT),                ft.Container(height=20),                ft.Text("開始使用:", size=16, weight=ft.FontWeight.BOLD),                ft.Text("1. 點擊「功能操作」標籤頁進行各種操作", text_align=ft.TextAlign.LEFT),                ft.Text("2. 點擊「帳號管理」標籤頁查看和管理已儲存的帳號", text_align=ft.TextAlign.LEFT),                ft.Text("3. 使用右上角的設定按鈕配置應用程式參數", text_align=ft.TextAlign.LEFT),            ]),            padding=20,            border=ft.border.all(1, ft.Colors.GREY_300),            border_radius=10,            margin=20        )    ], alignment=ft.MainAxisAlignment.START, expand=True, scroll=ft.ScrollMode.AUTO)        # 創建關於頁面內容    about_content = ft.Column([        ft.Container(            content=ft.Column([                ft.Text("關於 YuCursor", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),                ft.Divider(),                ft.Container(height=10),                ft.Row([                    ft.Image(src="/YuCursor.png", width=50, height=50, fit=ft.ImageFit.CONTAIN),                    ft.Column([                        ft.Text("YuCursor", size=24, weight=ft.FontWeight.BOLD),                        ft.Text("版本 1.0.1", size=16),                        ft.Text("發布日期：2025年5月20日", size=16)                    ])                ], alignment=ft.MainAxisAlignment.CENTER),                ft.Container(height=20),                ft.Text("應用介紹", size=18, weight=ft.FontWeight.BOLD),                ft.Text("YuCursor 是一款專為 Cursor 編輯器設計的帳號管理和自動化工具，幫助用戶輕鬆創建和管理多個 Cursor 帳號。", size=16),                ft.Container(height=10),                ft.Text("開發者資訊", size=18, weight=ft.FontWeight.BOLD),                ft.Text("本應用由 YuTeam 開發團隊開發", size=16),                ft.Container(height=20),                ft.Text("注意事項", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_600),                ft.Text("• 本工具永久免費，請勿從任何渠道購買", size=16),                ft.Text("• 請勿將本工具用於非法用途", size=16),                ft.Text("• 使用本工具所產生的任何後果由使用者自行承擔", size=16),                ft.Container(height=30),                ft.Text("© 2025 YuTeam. 保留所有權利。", size=14, italic=True, text_align=ft.TextAlign.CENTER)            ]),            padding=20,            border=ft.border.all(1, ft.Colors.GREY_300),            border_radius=10,            margin=20        )    ], alignment=ft.MainAxisAlignment.START, expand=True, scroll=ft.ScrollMode.AUTO)

    # 創建更新日誌內容
    changelog_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("更新日誌", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Divider(),
                ft.Container(height=10),
                ft.Text("版本 1.0.2 (2025年5月21日)", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("  - 新增了訂閱類型和用量資訊顯示。", size=16),
                ft.Text("  - 添加了刷新帳號資訊功能按鈕。", size=16),
                ft.Text("  - 增強了帳號詳情對話框，添加進度條顯示用量情況。", size=16),
                ft.Text("  - 新增了自動重啟應用程式的功能。", size=16),
                ft.Container(height=20),
                ft.Text("版本 1.0.1 (2025年5月20日)", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("  - 更新了「關於」頁面中的版本號和日期。", size=16),
                ft.Text("  - 修復了應用程式關閉時可能發生的事件迴圈錯誤。", size=16),
                ft.Container(height=20),
                ft.Text("版本 1.0.0 (2025年5月19日)", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("  - 初始版本發布。", size=16),
            ]),
            padding=20,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            margin=20
        )
    ], alignment=ft.MainAxisAlignment.START, expand=True, scroll=ft.ScrollMode.AUTO)

    

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
                        ft.Text("版本 1.0.2", size=16),
                        ft.Text("發布日期：2025年5月21日", size=16)
                    ])
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=20),
                ft.Text("應用介紹", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("YuCursor 是一款專為 Cursor 編輯器設計的帳號管理和自動化工具，幫助用戶輕鬆創建和管理多個 Cursor 帳號。", size=16),
                ft.Container(height=10),
                ft.Text("開發者資訊", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("本應用由 Yu 開發團隊開發", size=16),
                ft.Container(height=20),
                ft.Text("注意事項", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_600),
                ft.Text("• 本工具永久免費，請勿從任何渠道購買", size=16),
                ft.Text("• 請勿將本工具用於非法用途", size=16),
                ft.Text("• 使用本工具所產生的任何後果由使用者自行承擔", size=16),
                ft.Container(height=30),
                ft.Text("© 2025 Yu. 保留所有權利。", size=14, italic=True, text_align=ft.TextAlign.CENTER)
            ]),
            padding=20,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            margin=20
        )
    ], alignment=ft.MainAxisAlignment.START, expand=True, scroll=ft.ScrollMode.AUTO)

    # 添加標籤頁控件
    tabs = ft.Tabs(
        selected_index=0,  # 預設顯示主頁
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="主頁",
                icon=ft.Icons.HOME,
                content=ft.Container(
                    content=home_content,
                    padding=10,
                    expand=True
                )
            ),
            ft.Tab(
                text="功能操作",
                icon=ft.Icons.BUILD_CIRCLE,
                content=ft.Container(
                    content=original_content,
                    padding=10,
                    expand=True
                )
            ),
            ft.Tab(
                text="帳號管理",
                icon=ft.Icons.ACCOUNT_CIRCLE,
                content=ft.Container(
                    content=accounts_view,
                    padding=5,
                    expand=True
                )
            ),
            ft.Tab(
                text="關於",
                icon=ft.Icons.INFO,
                content=ft.Container(
                    content=about_content,
                    padding=10,
                    expand=True
                )
            ),
            ft.Tab(
                text="更新日誌",
                icon=ft.Icons.HISTORY,
                content=ft.Container(
                    content=changelog_content,
                    padding=10,
                    expand=True
                )
            )
        ],
        expand=True,
        on_change=on_tab_change
    )

    # 初始顯示 (確保在所有標籤頁都添加完畢後)
    page.add(tabs)
    
    # 設置預設標籤頁為「主頁」
    tabs.selected_index = 0
    tabs.update()
    
    # 窗口居中顯示 - 使用正確的方法設置窗口位置
    page.window.center()
    
    # 初始化時刷新帳號列表和當前帳號，並載入設定
    refresh_account_list()
    refresh_current_account()
    load_env_to_gui()
    
    # 自動刷新所有帳號資訊
    def auto_refresh_all_accounts():
        try:
            print("程式啟動，自動刷新所有帳號資訊...")
            # 獲取所有帳號
            all_accounts = accounts_manager.get_accounts()
            if not all_accounts:
                print("沒有帳號需要刷新")
                return
                
            # 建立不重複的郵箱列表
            unique_emails = set()
            for account in all_accounts:
                email = account.get('email')
                if email and email not in unique_emails:
                    unique_emails.add(email)
            
            # 計算需要刷新的帳號數量
            total = len(unique_emails)
            print(f"發現 {total} 個不重複帳號需要刷新")
            
            # 執行刷新任務
            def refresh_task():
                for i, email in enumerate(unique_emails):
                    try:
                        print(f"正在刷新帳號 {i+1}/{total}: {email}")
                        refresh_account_info(email)
                        # 每個帳號刷新後短暫延遲，避免過度頻繁的請求
                        time.sleep(1.5)
                    except Exception as e:
                        print(f"刷新帳號 {email} 時出錯: {str(e)}")
            
            # 在背景執行刷新任務
            threading.Thread(target=refresh_task, daemon=True).start()
            
            # 顯示提示
            page.overlay.append(ft.SnackBar(
                ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2),
                    ft.Text(f"正在背景刷新 {total} 個帳號資訊...")
                ]),
                open=True
            ))
            page.update()
            
        except Exception as e:
            print(f"自動刷新帳號時出錯: {str(e)}")
            traceback.print_exc()
    
    # 延遲幾秒後執行刷新，確保UI已完全載入
    threading.Timer(3.0, auto_refresh_all_accounts).start()
    
    # 顯示啟動提示視窗
    show_welcome_dialog()
    
    def on_window_event(e):
        global _app_is_closing # <--- 確保可以修改全局標誌
        if e.data == "close":
            print("Window close event: Setting _app_is_closing to True.") # Debug log
            _app_is_closing = True
            if hasattr(page, "_ui_log_handler"):
                try:
                    page._ui_log_handler.stop_redirect()
                    print("UI log handler stopped. Destroying window.") # Debug log
                except Exception as ex:
                    print(f"Error stopping UI log handler: {str(ex)}")
            
            # 確保窗口會立即關閉
            try:
                # 給一個短暫的延遲讓事件循環有時間處理最後的事件
                def delayed_close():
                    try:
                        if hasattr(page, "window") and hasattr(page.window, "close"):
                            page.window.close()
                            print("Window closed using page.window.close().")
                        else:
                            print("Window closing method not available.")
                    except Exception as close_ex:
                        print(f"Error during window close: {str(close_ex)}")
                
                threading.Timer(0.1, delayed_close).start()
            except Exception as ex:
                print(f"Error setting up delayed window close: {str(ex)}")
            
            print("Window close event handled.") # Debug log
    
    page.on_window_event = on_window_event

    # 定義檢查認證更新的函數
    def check_auth_update():
        try:
            auth_flag_file = "auth_updated.flag"
            if os.path.exists(auth_flag_file):
                try:
                    with open(auth_flag_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    
                    # 讀取後刪除標記檔案
                    os.remove(auth_flag_file)
                    
                    email = content.split(",")[1] if "," in content else "未知帳號"
                    
                    # 顯示重啟對話框
                    restart_dialog = ft.AlertDialog(
                        title=ft.Row([
                            ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE),
                            ft.Text("認證資訊已更新", color=ft.Colors.BLUE)
                        ]),
                        content=ft.Text(f"帳號 {email} 的認證資訊已更新！為確保所有功能正常運作，建議重新啟動應用程式。是否立即重新啟動？"),
                        actions=[
                            ft.TextButton("稍後", on_click=lambda e: close_restart_dialog(e, restart_dialog, False)),
                            ft.TextButton("立即重啟", on_click=lambda e: close_restart_dialog(e, restart_dialog, True))
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                        open=True
                    )
                    
                    def close_restart_dialog(e, dialog, should_restart):
                        dialog.open = False
                        page.update()
                        
                        if should_restart:
                            # 在關閉對話框後重啟 GUI，顯示明確的提示
                            page.overlay.append(ft.SnackBar(ft.Text("認證資訊已更新，正在重啟應用..."), open=True))
                            page.update()
                            # 延遲一點時間讓提示訊息顯示出來
                            threading.Timer(1.0, restart_gui_app).start()
                    
                    page.overlay.append(restart_dialog)
                    page.update()
                except Exception as e:
                    print(f"處理認證更新檔案時出錯: {str(e)}")
        except Exception as e:
            print(f"檢查認證更新時出錯: {str(e)}")
    
    # 啟動定時檢查認證更新 (每10秒檢查一次)
    def start_auth_check_timer():
        check_auth_update()  # 初次檢查
        threading.Timer(10.0, start_auth_check_timer).start()
    
    # 啟動檢查
    start_auth_check_timer()

# 全局變數用於傳遞手動輸入的驗證碼
manual_verification_code = None
g_keep_alive_process = None # 新增：用於保存 keep_alive 進程

# 新增一個重載帳號管理器的函數
def reload_accounts_manager():
    global accounts_manager, _app_is_closing, _flet_page_instance # <--- 確保訪問全局標誌
    try:
        # 重載帳號管理器實例
        print("重新載入帳號管理器...")
        # 確保模組已導入
        if 'AccountsManager' not in globals():
            from accounts_manager import AccountsManager
        else:
            # 嘗試重新導入模組
            import importlib
            import accounts_manager
            importlib.reload(accounts_manager)
            from accounts_manager import AccountsManager
            
        old_file_path = accounts_manager.accounts_file if accounts_manager else None
        
        # 創建新的實例
        accounts_manager = AccountsManager()
        
        if old_file_path and old_file_path != accounts_manager.accounts_file:
            print(f"警告：帳號檔案路徑已變更，從 {old_file_path} 到 {accounts_manager.accounts_file}")
        
        # 更新 UI - 只在_flet_page_instance存在時執行
        if _flet_page_instance:
            if _app_is_closing: # <--- 在嘗試任何 UI 操作前檢查
                print("reload_accounts_manager: App is closing, skipping UI updates.")
                # 即使 UI 不更新，也打印帳號數量
                print(f"帳號管理器已重新載入 (UI skipped due to app closing)，共載入 {len(accounts_manager.get_accounts())} 個帳號")
                return True # 仍然認為重載本身是成功的

            def _update_ui_after_reload_safe():
                try:
                    if _app_is_closing: # 在執行緒安全的回調中再次檢查
                        print("reload_accounts_manager (_update_ui_after_reload_safe): App is closing, skipping UI.")
                        return

                    if 'refresh_account_list' in globals() and callable(globals()['refresh_account_list']):
                        refresh_account_list() 
                    else:
                        print("reload_accounts_manager: refresh_account_list not found or not callable.")
                    
                    _flet_page_instance.overlay.append(ft.SnackBar(ft.Text("帳號管理器已重新載入"), open=True))
                    _flet_page_instance.update()
                    print(f"帳號管理器已重新載入 (UI updated via run_thread_safe)，共載入 {len(accounts_manager.get_accounts())} 個帳號")

                except RuntimeError as e:
                    print(f"reload_accounts_manager: UI update failed within run_thread_safe (loop likely closed): {str(e)}")
                except Exception as e:
                    print(f"reload_accounts_manager: Unexpected error during UI update within run_thread_safe: {str(e)}")
            
            try:
                # 嘗試使用 run_thread_safe 或 add_to_control_event_queue
                if hasattr(_flet_page_instance, 'run_thread_safe'):
                    _flet_page_instance.run_thread_safe(_update_ui_after_reload_safe)
                elif hasattr(_flet_page_instance, 'add_to_control_event_queue'):
                    _flet_page_instance.add_to_control_event_queue(_update_ui_after_reload_safe)
                else:
                    # 如果都不支持，直接調用
                    _update_ui_after_reload_safe()
            except RuntimeError as e:
                print(f"reload_accounts_manager: Failed to schedule UI updates (loop likely closed): {str(e)}")
            except Exception as e:
                print(f"reload_accounts_manager: Error scheduling UI updates: {str(e)}")
        else:
            print(f"帳號管理器已重新載入，共載入 {len(accounts_manager.get_accounts())} 個帳號")
            print("注意: _flet_page_instance不存在，無法更新UI")
        
        return True
    except Exception as e:
        print(f"重新載入帳號管理器時出錯: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# 添加重啟 GUI 的函數
def restart_gui_app():
    global _app_is_closing
    
    try:
        print("準備重啟 GUI 應用...")
        
        # 設置應用正在關閉的標誌
        _app_is_closing = True
        
        # 獲取當前執行檔案的路徑
        current_path = os.path.abspath(sys.argv[0])
        
        # 獲取 Python 解釋器路徑
        python_exe = sys.executable
        
        # 創建重啟的命令，添加重啟標記參數
        restart_command = [python_exe, current_path, "--restarted"]
        
        # 顯示重啟對話框
        def show_restart_dialog():
            restart_dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.Icons.REFRESH, color=ft.Colors.BLUE),
                    ft.Text("應用正在重啟")
                ]),
                content=ft.Text("應用將在關閉後重新啟動..."),
                open=True
            )
            _flet_page_instance.overlay.append(restart_dialog)
            _flet_page_instance.update()
            
            # 延遲關閉窗口，確保對話框能夠顯示
            threading.Timer(1.0, close_window_and_restart).start()
        
        # 關閉窗口並重啟
        def close_window_and_restart():
            try:
                # 關閉 UI 日誌處理器
                if _flet_page_instance and hasattr(_flet_page_instance, "_ui_log_handler"):
                    _flet_page_instance._ui_log_handler.stop_redirect()
                    print("UI 日誌處理器已停止重定向")
                
                # 先嘗試正常關閉窗口
                if _flet_page_instance:
                    try:
                        print("正在關閉應用視窗...")
                        
                        # 標記窗口將要關閉
                        _app_is_closing = True
                        
                        # 嘗試不同的窗口關閉方法
                        if hasattr(_flet_page_instance, "window") and hasattr(_flet_page_instance.window, "close"):
                            try:
                                # 方法 1: 使用 page.window.close()
                                _flet_page_instance.window.close()
                                print("使用 page.window.close() 關閉窗口")
                            except Exception as e1:
                                print(f"page.window.close() 失敗: {e1}")
                        else:
                            print("page.window.close() 方法不存在")
                        
                        # 給窗口一點時間關閉
                        time.sleep(0.5)
                    except Exception as window_ex:
                        print(f"關閉視窗時出錯: {str(window_ex)}")
                
                # 啟動新進程
                try:
                    # Windows 系統使用特殊方式啟動
                    if os.name == 'nt':
                        # 使用 shell=True 方式啟動，確保引號處理正確
                        # 添加 /b 參數啟動後台進程，避免開啟新控制台
                        cmd = f'cmd /c start /b "YuCursor" "{python_exe}" "{current_path}" --restarted'
                        print(f"使用 shell 命令: {cmd}")
                        os.system(cmd)  # 改用 os.system 以避免複雜的引號處理問題
                    else:
                        # Unix 系統使用標準方式啟動
                        print(f"使用標準方式啟動: {restart_command}")
                        subprocess.Popen(
                            restart_command,
                            start_new_session=True,
                            close_fds=True
                        )
                    
                    print("已啟動新進程")
                except Exception as e:
                    print(f"啟動新進程失敗: {str(e)}")
                    traceback.print_exc()
                
                # 延遲退出，給新進程一些時間完全啟動
                time.sleep(1.0)
                
                # 強制終止此進程
                print("正在終止當前進程...")
                sys.exit(0)
                
            except Exception as e:
                print(f"關閉窗口並重啟時出錯: {str(e)}")
                traceback.print_exc()
                # 如果失敗，仍然嘗試強制退出
                os._exit(0)
        
        # 如果頁面實例存在，顯示對話框
        if _flet_page_instance:
            try:
                # 嘗試使用 run_thread_safe 或 add_to_control_event_queue
                if hasattr(_flet_page_instance, 'run_thread_safe'):
                    _flet_page_instance.run_thread_safe(show_restart_dialog)
                elif hasattr(_flet_page_instance, 'add_to_control_event_queue'):
                    _flet_page_instance.add_to_control_event_queue(show_restart_dialog)
                else:
                    # 如果都不支持，直接調用
                    show_restart_dialog()
            except Exception as e:
                print(f"顯示重啟對話框時出錯: {str(e)}")
                # 如果無法顯示對話框，直接關閉並重啟
                close_window_and_restart()
        else:
            # 如果沒有頁面實例，直接關閉並重啟
            close_window_and_restart()
        
        return True
    except Exception as e:
        print(f"準備重啟應用時出錯: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        # 檢查是否為重啟模式
        is_restarted = "--restarted" in sys.argv
        
        if is_restarted:
            print("檢測到重啟模式，進行特殊初始化...")
            # 如果是重啟模式，確保環境變數重新載入
            time.sleep(0.5)  # 短暫延遲確保資源釋放
            
            # 重新載入關鍵模組
            for module_name in ['config', 'accounts_manager', 'cursor_auth_manager']:
                if module_name in sys.modules:
                    del sys.modules[module_name]
                    print(f"已強制重新載入 {module_name} 模組")
            
            # 不再使用已棄用的 os._environ
            try:
                # 使用替代方法重載環境變數
                import os
                # 載入 .env 檔案內容到環境變數
                if os.path.exists(".env"):
                    with open(".env", "r", encoding="utf-8") as env_file:
                        for line in env_file:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            if "=" in line:
                                key, value = line.split("=", 1)
                                # 移除引號
                                key = key.strip()
                                value = value.strip()
                                if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                                    value = value[1:-1]
                                # 設置環境變數
                                os.environ[key] = value
                    print("已從 .env 檔案重新載入環境變數")
            except Exception as e:
                print(f"重載環境變數時出錯: {str(e)}")
            traceback.print_exc()
        
        # 設置工作目錄
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        print(f"應用路徑: {application_path}")
        os.chdir(application_path)
        
        # 確保資源路徑正確
        icon_path = get_resource_path("YuCursor.png")
        print(f"圖標路徑: {icon_path}")
        
        # 設置 Flet 環境
        os.environ["FLET_FORCE_WEB_VIEW"] = "true"
        os.environ["FLET_VIEW"] = "gui"  # 使用 gui 模式
        
        # 啟動 Flet 應用
        print("啟動 Flet 應用...")
        
        # 檢測可用端口
        def find_available_port(start_port=8500, max_tries=50):
            """尋找可用的端口，避免端口衝突"""
            import socket
            port = start_port
            for _ in range(max_tries):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('127.0.0.1', port))
                        return port
                except OSError:
                    port += 1
            return None
        
        # 找到可用端口
        port = find_available_port()
        if port is None:
            print("警告：找不到可用端口，使用默認端口")
            # 使用明確的 IP 地址而非主機名
            ft.app(target=main, assets_dir=application_path, view=ft.AppView.FLET_APP)
        else:
            print(f"使用端口: {port}")
            # 使用明確的 IP 地址和特定端口
            ft.app(target=main, assets_dir=application_path, view=ft.AppView.FLET_APP, 
                 host="127.0.0.1", port=port)
    except Exception as startup_error:
        print(f"啟動應用時發生錯誤: {str(startup_error)}")
        traceback.print_exc()
        
        # 顯示錯誤訊息對話框
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("啟動錯誤", f"應用啟動失敗:\n{str(startup_error)}\n\n請檢查日誌以獲取更多訊息。")
        except Exception:
            pass  # 無法顯示對話框時，至少確保錯誤已記錄