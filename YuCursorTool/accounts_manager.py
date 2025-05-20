import os
import json
import sys
import datetime
from typing import List, Dict, Optional

# 直接使用 datetime.datetime 而不是創建別名
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return super().default(obj)

class AccountsManager:
    """管理 Cursor 帳號資訊"""

    def __init__(self):
        # 獲取應用程式的根目錄路徑
        if getattr(sys, "frozen", False):
            # 如果是打包後的可執行檔
            application_path = os.path.dirname(sys.executable)
        else:
            # 如果是開發環境
            application_path = os.path.dirname(os.path.abspath(__file__))

        # 指定儲存帳號資訊的檔案路徑
        self.accounts_file = os.path.join(application_path, "cursor_accounts.json")
        
        # 初始化帳號列表
        self.accounts = self._load_accounts()

    def _load_accounts(self) -> List[Dict]:
        """從檔案載入帳號列表，並清理時間戳欄位"""
        if not os.path.exists(self.accounts_file):
            return []
        
        loaded_accounts = []
        try:
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                loaded_accounts = json.load(f)
        except Exception as e:
            print(f"載入帳號列表檔案 ({self.accounts_file}) 失敗 ({type(e).__name__}): {str(e)}")
            return [] # 如果檔案讀取或JSON解析失敗，返回空列表

        cleaned_accounts = []
        current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for account in loaded_accounts:
            if not isinstance(account, dict):
                print(f"警告: 在 accounts 檔案中發現非字典類型的條目，已跳過: {account}")
                continue

            # 清理 created_at
            created_at = account.get('created_at')
            if isinstance(created_at, str):
                try:
                    datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    account['created_at'] = created_at # 格式正確，保留
                except ValueError:
                    print(f"警告: 帳號 {account.get('email')} 的 created_at 格式錯誤 ('{created_at}')，已重設為當前時間。")
                    account['created_at'] = current_time_str
            else:
                print(f"警告: 帳號 {account.get('email')} 的 created_at 不是字串 ('{type(created_at)}')，已重設為當前時間。")
                account['created_at'] = current_time_str
            
            # 清理 updated_at
            updated_at = account.get('updated_at')
            if isinstance(updated_at, str):
                try:
                    datetime.datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
                    account['updated_at'] = updated_at # 格式正確，保留
                except ValueError:
                    print(f"警告: 帳號 {account.get('email')} 的 updated_at 格式錯誤 ('{updated_at}')，已重設為當前時間。")
                    account['updated_at'] = current_time_str
            else:
                print(f"警告: 帳號 {account.get('email')} 的 updated_at 不是字串 ('{type(updated_at)}')，已重設為當前時間。")
                account['updated_at'] = current_time_str
            
            cleaned_accounts.append(account)
        
        if loaded_accounts and not cleaned_accounts and os.path.exists(self.accounts_file):
             # 如果原始列表有內容，但清理後為空（可能都是無效條目），且檔案確實存在
             print(f"警告: {self.accounts_file} 中所有帳號條目格式似乎都有問題。請檢查檔案內容。")

        return cleaned_accounts

    def _save_accounts(self) -> bool:
        """儲存帳號列表到檔案"""
        try:
            # 簡化診斷輸出
            print(f"正在儲存帳號資訊...")
            
            with open(self.accounts_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
            print(f"帳號資訊已成功儲存至 {self.accounts_file}")
            return True
        except Exception as e:
            print(f"儲存帳號列表失敗 ({type(e).__name__}): {str(e)}")
            return False

    def add_account(self, email: str, password: str, access_token: str = None, 
                   refresh_token: str = None, user_id: str = None, 
                   cookie: str = None, membership: Dict = None,
                   account_status: str = None, usage: Dict = None,
                   created_at_override: str = None) -> bool:
        """新增帳號到列表
        
        Args:
            email: 帳號郵箱
            password: 帳號密碼
            access_token: 存取令牌（可選）
            refresh_token: 刷新令牌（可選）
            user_id: 用戶ID（可選）
            cookie: 認證Cookie（可選）
            membership: 會員資訊（可選）
            account_status: 帳號狀態 (可選)
            usage: 使用情況 (可選)
            created_at_override: 覆蓋創建時間 (可選, 格式 YYYY-MM-DD HH:MM:SS)
            
        Returns:
            bool: 是否成功添加
        """
        try:
            # 移除ANSI終端控制碼
            def remove_ansi_codes(text):
                if not text:
                    return text
                import re
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                return ansi_escape.sub('', text) if isinstance(text, str) else text
            
            # 過濾所有輸入參數中的ANSI控制碼
            email = remove_ansi_codes(email)
            password = remove_ansi_codes(password)
            access_token = remove_ansi_codes(access_token)
            refresh_token = remove_ansi_codes(refresh_token)
            user_id = remove_ansi_codes(user_id)
            cookie = remove_ansi_codes(cookie)
            if created_at_override:
                created_at_override = remove_ansi_codes(created_at_override)
            
            print(f"處理帳號: {email}")
            
            # 檢查是否已存在相同郵箱的帳號
            for account in self.accounts:
                if account.get('email') == email:
                    # 更新現有帳號資訊
                    account['password'] = password
                    if access_token is not None:
                        account['access_token'] = access_token
                    if refresh_token is not None:
                        account['refresh_token'] = refresh_token
                    if user_id is not None:
                        account['user'] = user_id
                    if cookie is not None:
                        account['cookie'] = cookie
                    if membership is not None:
                        account['membership'] = membership
                    if account_status is not None:
                        account['account_status'] = account_status
                    if usage is not None:
                        account['usage'] = usage
                    
                    if created_at_override:
                        try:
                            datetime.datetime.strptime(created_at_override, "%Y-%m-%d %H:%M:%S")
                            account['created_at'] = str(created_at_override) # 確保是字串
                        except ValueError:
                            print(f"警告: 提供的 created_at_override ({created_at_override}) 格式不正確，將忽略。")
                    
                    account['updated_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"已更新現有帳號: {email}")
                    return self._save_accounts()
            
            # 添加新帳號
            current_datetime_obj = datetime.datetime.now()
            current_time_str = current_datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
            
            final_created_at_str = current_time_str
            if created_at_override:
                try:
                    datetime.datetime.strptime(created_at_override, "%Y-%m-%d %H:%M:%S")
                    final_created_at_str = str(created_at_override) # 確保是字串
                except ValueError:
                    print(f"警告: 提供的 created_at_override ({created_at_override}) 格式不正確，將使用當前時間。")

            new_account = {
                'email': email,
                'password': password,
                'created_at': final_created_at_str,
                'updated_at': current_time_str
            }
            if access_token is not None:
                new_account['access_token'] = access_token
            if refresh_token is not None:
                new_account['refresh_token'] = refresh_token
            if user_id is not None:
                new_account['user'] = user_id
            if cookie is not None:
                new_account['cookie'] = cookie
            if membership is not None:
                new_account['membership'] = membership
            if account_status is not None:
                new_account['account_status'] = account_status
            if usage is not None:
                new_account['usage'] = usage
                
            self.accounts.append(new_account)
            print(f"已新增帳號: {email}")
            return self._save_accounts()
        except Exception as e:
            print(f"添加帳號失敗: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def get_accounts(self) -> List[Dict]:
        """獲取所有儲存的帳號
        
        Returns:
            List[Dict]: 帳號列表
        """
        return self.accounts

    def get_account(self, email: str) -> Optional[Dict]:
        """獲取指定郵箱的帳號資訊
        
        Args:
            email: 帳號郵箱
            
        Returns:
            Optional[Dict]: 帳號資訊，如果不存在則返回 None
        """
        for account in self.accounts:
            if account.get('email') == email:
                return account
        return None

    def delete_account(self, email: str) -> bool:
        """刪除指定郵箱的帳號
        
        Args:
            email: 帳號郵箱
            
        Returns:
            bool: 是否成功刪除
        """
        for i, account in enumerate(self.accounts):
            if account.get('email') == email:
                self.accounts.pop(i)
                return self._save_accounts()
        return False

    def update_account_token(self, email: str, access_token: str = None, 
                            refresh_token: str = None, user_id: str = None, 
                            cookie: str = None, membership: Dict = None,
                            account_status: str = None, usage: Dict = None) -> bool:
        """更新帳號的令牌與資訊
        
        Args:
            email: 帳號郵箱
            access_token: 存取令牌（可選）
            refresh_token: 刷新令牌（可選）
            user_id: 用戶ID（可選）
            cookie: 認證Cookie（可選）
            membership: 會員資訊（可選）
            account_status: 帳號狀態 (可選)
            usage: 使用情況 (可選)
            
        Returns:
            bool: 是否成功更新
        """
        for account in self.accounts:
            if account.get('email') == email:
                if access_token is not None:
                    account['access_token'] = access_token
                if refresh_token is not None:
                    account['refresh_token'] = refresh_token
                if user_id is not None:
                    account['user'] = user_id
                if cookie is not None:
                    account['cookie'] = cookie
                if membership is not None:
                    account['membership'] = membership
                if account_status is not None:
                    account['account_status'] = account_status
                if usage is not None:
                    account['usage'] = usage
                
                account['updated_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return self._save_accounts()
        return False

    def display_accounts(self) -> str:
        """顯示所有帳號的郵箱和密碼
        
        Returns:
            str: 格式化的帳號資訊字串
        """
        if not self.accounts:
            return "目前沒有儲存任何帳號。"
        
        result = "=== Cursor 帳號列表 ===\n"
        for i, account in enumerate(self.accounts, 1):
            email = account.get('email', '未知郵箱')
            password = account.get('password', '未知密碼')
            created_at = account.get('created_at', '未知時間')
            result += f"{i}. 郵箱: {email}\n   密碼: {password}\n   建立時間: {created_at}\n"
            
            # 顯示帳號狀態（如果有）
            if 'account_status' in account:
                result += f"   狀態: {account['account_status']}\n"
                
            # 顯示會員資訊（如果有）
            if 'membership' in account and isinstance(account['membership'], dict):
                membership = account['membership']
                if 'type' in membership:
                    result += f"   會員類型: {membership['type']}\n"
                if 'expiresAt' in membership:
                    result += f"   到期日期: {membership['expiresAt']}\n"
            
            result += "\n"
        
        return result 