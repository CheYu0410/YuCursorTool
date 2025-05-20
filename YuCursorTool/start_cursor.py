import os
import subprocess
import sys
import time
import platform
from logger import logging

def StartCursor():
    """
    啟動Cursor應用
    
    嘗試啟動Cursor應用，並返回啟動進程
    
    Returns:
        subprocess.Popen: 啟動的進程對象，如果失敗則返回None
    """
    try:
        logging.info("正在啟動Cursor...")
        
        # 獲取操作系統類型
        os_type = platform.system()
        
        # 根據不同操作系統執行相應的啟動命令
        if os_type == "Windows":
            # Windows系統下的Cursor路徑
            cursor_path = os.path.expandvars("%LOCALAPPDATA%\\Programs\\Cursor\\Cursor.exe")
            
            # 檢查Cursor可執行文件是否存在
            if not os.path.exists(cursor_path):
                logging.error(f"找不到Cursor可執行文件：{cursor_path}")
                return None
                
            # 使用subprocess啟動Cursor
            process = subprocess.Popen(
                [cursor_path],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
        elif os_type == "Darwin":  # macOS
            # macOS系統下的Cursor路徑
            cursor_path = "/Applications/Cursor.app"
            
            if not os.path.exists(cursor_path):
                logging.error(f"找不到Cursor應用：{cursor_path}")
                return None
                
            # 使用open命令啟動macOS應用
            process = subprocess.Popen(
                ["open", cursor_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
        elif os_type == "Linux":
            # Linux系統下的Cursor路徑（假設）
            cursor_path = os.path.expanduser("~/.local/share/cursor/cursor")
            
            if not os.path.exists(cursor_path):
                logging.error(f"找不到Cursor可執行文件：{cursor_path}")
                return None
                
            process = subprocess.Popen(
                [cursor_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
        else:
            logging.error(f"不支持的操作系統：{os_type}")
            return None
            
        logging.info("Cursor已成功啟動")
        time.sleep(2)  # 等待應用程序啟動
        return process
        
    except Exception as e:
        logging.error(f"啟動Cursor時出錯：{str(e)}")
        return None 