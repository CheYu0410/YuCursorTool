import os
import json
import platform
import sys
from logger import logging

class AutoUpdateDisabler:
    """禁用Cursor自動更新的類"""
    
    def __init__(self):
        """初始化更新禁用器"""
        self.os_type = platform.system()
        self.settings_path = self._get_settings_path()
        
    def _get_settings_path(self):
        """獲取Cursor設定檔案路徑"""
        try:
            if self.os_type == "Windows":
                # Windows系統下的設定檔案路徑
                path = os.path.expandvars("%APPDATA%\\cursor\\settings.json")
            elif self.os_type == "Darwin":  # macOS
                # macOS系統下的設定檔案路徑
                path = os.path.expanduser("~/Library/Application Support/cursor/settings.json")
            elif self.os_type == "Linux":
                # Linux系統下的設定檔案路徑（假設）
                path = os.path.expanduser("~/.config/cursor/settings.json")
            else:
                logging.error(f"不支持的操作系統：{self.os_type}")
                return None
                
            # 確保目錄存在
            directory = os.path.dirname(path)
            if not os.path.exists(directory):
                os.makedirs(directory)
                
            return path
        except Exception as e:
            logging.error(f"獲取設定檔案路徑時出錯：{str(e)}")
            return None
    
    def disable_auto_update(self):
        """禁用Cursor自動更新"""
        try:
            if not self.settings_path:
                logging.error("無法獲取設定檔案路徑")
                return False
                
            # 讀取現有設定（如果存在）
            settings = {}
            if os.path.exists(self.settings_path):
                try:
                    with open(self.settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                except Exception as e:
                    logging.warning(f"讀取設定檔案時出錯：{str(e)}，將創建新檔案")
            
            # 添加或更新禁用自動更新的設定
            settings["updatePolicy"] = "manual"
            
            # 保存設定檔案
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
                
            logging.info(f"已禁用Cursor自動更新，設定已保存到：{self.settings_path}")
            return True
            
        except Exception as e:
            logging.error(f"禁用自動更新時出錯：{str(e)}")
            return False
            
    def enable_auto_update(self):
        """啟用Cursor自動更新（恢復默認設定）"""
        try:
            if not self.settings_path:
                logging.error("無法獲取設定檔案路徑")
                return False
                
            # 讀取現有設定（如果存在）
            settings = {}
            if os.path.exists(self.settings_path):
                try:
                    with open(self.settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                except Exception as e:
                    logging.warning(f"讀取設定檔案時出錯：{str(e)}，將創建新檔案")
            
            # 恢復自動更新設定
            if "updatePolicy" in settings:
                settings["updatePolicy"] = "auto"
            
            # 保存設定檔案
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
                
            logging.info(f"已啟用Cursor自動更新，設定已保存到：{self.settings_path}")
            return True
            
        except Exception as e:
            logging.error(f"啟用自動更新時出錯：{str(e)}")
            return False 