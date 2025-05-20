import os
import sys
import time
import subprocess
import webbrowser
import psutil
import requests
import signal

def kill_process_by_name(process_name):
    """根據進程名稱殺死進程"""
    for proc in psutil.process_iter(['pid', 'name']):
        if process_name.lower() in proc.info['name'].lower():
            try:
                process = psutil.Process(proc.info['pid'])
                process.terminate()
                print(f"已終止進程: {proc.info['name']} (PID: {proc.info['pid']})")
            except Exception as e:
                print(f"終止進程時出錯: {e}")

def main():
    """主函數"""
    try:
        print("啟動 YuCursor 直接啟動器...")
        
        # 獲取當前目錄
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        os.chdir(application_path)
        
        # 殺死可能已運行的 flet 或 YuCursor 進程
        kill_process_by_name("flet")
        kill_process_by_name("YuCursor")
        
        # 設置環境變數
        os.environ["FLET_FORCE_WEB_VIEW"] = "true"
        os.environ["FLET_VIEW"] = "gui"
        
        # 啟動 YuCursor.exe，不顯示控制台窗口
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        process = subprocess.Popen(
            "YuCursor.exe", 
            shell=True,
            startupinfo=startupinfo
        )
        
        print(f"已啟動 YuCursor 進程，PID: {process.pid}")
        
        # 等待 5 秒
        print("等待應用程式初始化...")
        time.sleep(5)
        
        # 嘗試打開瀏覽器直接訪問 flet 服務
        try:
            # 嘗試幾個可能的端口
            ports = [8550, 3000, 8000, 8080]
            for port in ports:
                url = f"http://localhost:{port}"
                try:
                    response = requests.get(url, timeout=1)
                    if response.status_code == 200:
                        print(f"發現 flet 服務於 {url}")
                        webbrowser.open(url)
                        break
                except:
                    continue
        except Exception as e:
            print(f"嘗試打開瀏覽器時出錯: {e}")
        
        # 等待用戶關閉程式
        print("YuCursor 已啟動，此窗口可以關閉")
        process.wait()
        
        return 0
    except Exception as e:
        print(f"啟動 YuCursor 時出錯: {e}")
        import traceback
        traceback.print_exc()
        input("按 Enter 鍵退出...")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 