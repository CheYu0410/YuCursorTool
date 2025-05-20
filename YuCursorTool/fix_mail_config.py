import os
import random
import string

def generate_random_prefix(length=6):
    """生成隨機字母前綴"""
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

def fix_env_file():
    """修改 .env 檔案以使用隨機域名郵箱"""
    env_path = ".env"
    if not os.path.exists(env_path):
        print("錯誤: .env 檔案不存在")
        return False
    
    # 備份原始檔案
    with open(env_path, "r", encoding="utf-8") as f:
        original_content = f.read()
    
    with open(f"{env_path}.bak", "w", encoding="utf-8") as f:
        f.write(original_content)
        print(f"已備份原始 .env 檔案到 {env_path}.bak")
    
    # 解析出域名
    domain = None
    lines = original_content.split("\n")
    for line in lines:
        if line.startswith("DOMAIN="):
            domain_part = line.split("=", 1)[1].strip()
            # 移除引號和註釋
            if domain_part.startswith("'") and "'" in domain_part[1:]:
                domain = domain_part[1:].split("'", 1)[0]
            elif domain_part.startswith('"') and '"' in domain_part[1:]:
                domain = domain_part[1:].split('"', 1)[0]
            else:
                domain = domain_part.split("#", 1)[0].strip()
            break
    
    if not domain:
        print("錯誤: 無法從 .env 檔案中解析域名")
        return False
    
    # 生成隨機郵箱前綴
    prefix = generate_random_prefix()
    
    # 修改內容
    modified_lines = []
    for line in lines:
        if line.startswith("TEMP_MAIL="):
            # 將 TEMP_MAIL 設置為 null
            modified_lines.append("TEMP_MAIL=null   # 设置为 null 使用随机域名邮箱")
        elif line.startswith("TEMP_MAIL_EXT="):
            # 設置郵箱後綴為域名
            modified_lines.append(f"TEMP_MAIL_EXT=@{domain}  # 使用域名作为邮箱后缀")
        else:
            modified_lines.append(line)
    
    # 寫入修改後的檔案
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(modified_lines))
    
    print(f"已成功修改 .env 檔案")
    print(f"下次註冊將使用隨機生成的郵箱地址，例如: {prefix}@{domain}")
    return True

if __name__ == "__main__":
    print("開始修復郵箱配置...")
    if fix_env_file():
        print("修復完成！請重新執行 gui_app.py")
    else:
        print("修復失敗，請手動檢查 .env 檔案") 