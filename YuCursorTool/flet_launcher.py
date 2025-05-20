import os
import sys
import subprocess

def main():
    try:
        print("啟動 YuCursor 應用程式...")
        
        # 獲取當前腳本所在目錄
        if getattr(sys, 'frozen', False):
            # 如果是打包後的版本
            current_dir = os.path.dirname(sys.executable)
        else:
            # 如果是源碼運行
            current_dir = os.path.dirname(os.path.abspath(__file__))
        
        os.chdir(current_dir)
        
        # 設置環境變數
        os.environ["FLET_FORCE_WEB_VIEW"] = "true"
        
        # 在當前環境中運行 gui_app.py
        if getattr(sys, 'frozen', False):
            # 直接使用 YuCursor.exe
            result = subprocess.run(["YuCursor.exe"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True, 
                                   encoding='utf-8')
        else:
            # 使用 Python 運行 gui_app.py
            python_exe = sys.executable
            result = subprocess.run([python_exe, "gui_app.py"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True, 
                                   encoding='utf-8')
        
        print("程式執行結果:", result.returncode)
        if result.stdout:
            print("標準輸出:", result.stdout)
        if result.stderr:
            print("錯誤輸出:", result.stderr)
        
        return 0
    except Exception as e:
        print(f"啟動 YuCursor 應用程式時出錯: {str(e)}")
        import traceback
        traceback.print_exc()
        input("按 Enter 鍵退出...")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 