import os
import shutil
import sys
import subprocess
from pathlib import Path

# 應用程式設定
APP_NAME = "YuCursor"
MAIN_SCRIPT = "gui_app.py"
ICON_FILE = "YuCursor.png"

# 需要包含的文件
INCLUDE_FILES = [
    "YuCursor.png",
    "settings_icon.png",
    ".env",
    "correct_env.txt",
    "names-dataset.txt",
    "cursor_accounts.json",
    "requirements.txt",
    "accounts_manager.py",
    "cursor_auth_manager.py",
    "cursor_pro_keep_alive.py",
    "config.py",
    "reset_machine.py",
    "exit_cursor.py",
    "browser_utils.py",
    "get_email_code.py",
    "logger.py",
    "hook-flet.py"
]

# 需要包含的 Python 模組
REQUIRED_MODULES = [
    "flet",
    "selenium",
    "pyautogui",
    "pyperclip"
]

def copy_files_to_dist(dist_dir):
    """複製所需文件到 dist 目錄"""
    print("複製文件到 dist 目錄...")
    
    for file in INCLUDE_FILES:
        src = Path(file)
        if src.exists():
            dst = dist_dir / src.name
            print(f"  - 複製 {src} 到 {dst}")
            shutil.copy2(src, dst)
        else:
            print(f"  - 警告: {file} 不存在")
    
    # 複製 Python 腳本
    for file in os.listdir('.'):
        if file.endswith('.py') and file != MAIN_SCRIPT and file != "flet_build.py" and Path(file).is_file():
            src = Path(file)
            dst = dist_dir / src.name
            print(f"  - 複製 Python 腳本 {src} 到 {dst}")
            shutil.copy2(src, dst)
    
    # 複製子目錄
    for folder in os.listdir('.'):
        if os.path.isdir(folder) and folder not in ['__pycache__', 'build', 'dist', 'venv', '.git', '.github']:
            src = Path(folder)
            dst = dist_dir / folder
            if dst.exists():
                shutil.rmtree(dst)
            print(f"  - 複製目錄 {src} 到 {dst}")
            shutil.copytree(src, dst)

def build_app():
    """使用 flet build 打包應用程式"""
    print(f"開始打包 {APP_NAME}...")
    
    # 創建輸出目錄
    output_dir = Path("dist") / APP_NAME
    if output_dir.exists():
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # 構建命令
    build_cmd = [
        sys.executable, "-m", "flet", "build", 
        "windows", 
        "--product-name", APP_NAME,
        "--product-version", "1.0.0",
        "--icon", ICON_FILE,
        "--add-files", MAIN_SCRIPT
    ]
    
    # 執行打包命令
    print("執行打包命令: " + " ".join(build_cmd))
    try:
        process = subprocess.Popen(
            build_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # 顯示輸出
        for line in process.stdout:
            print(line.strip())
        
        process.wait()
        if process.returncode != 0:
            print("打包過程出錯:")
            for line in process.stderr:
                print(line.strip())
            return False
        
        # 如果成功，複製其他必要文件
        dist_dir = Path("build") / "windows" / "runner" / "Release"
        if dist_dir.exists():
            copy_files_to_dist(dist_dir)
            
            # 將打包好的文件移至 dist 目錄
            final_dir = Path("dist") / APP_NAME
            if final_dir.exists():
                shutil.rmtree(final_dir)
            
            print(f"移動打包好的文件到 {final_dir}")
            shutil.copytree(dist_dir, final_dir)
            
            print(f"打包完成！可執行檔位於: {final_dir}")
            return True
        else:
            print(f"錯誤: 無法找到打包輸出目錄 {dist_dir}")
            return False
    
    except Exception as e:
        print(f"打包過程中出現錯誤: {str(e)}")
        return False

if __name__ == "__main__":
    build_app() 