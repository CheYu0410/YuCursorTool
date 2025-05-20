from config import Config
import os

try:
    c = Config()
    print("PIN碼:", c.get_temp_mail_epin())
    print("臨時郵箱:", c.get_temp_mail_ext())
    print("域名:", c.get_domain())
    
    # 嘗試直接從環境變數檔案讀取
    if os.path.exists(".env"):
        print("\n直接讀取 .env 檔案:")
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "TEMP_MAIL_EPIN" in line:
                    print(f"  {line}")
except Exception as e:
    print(f"錯誤: {str(e)}") 