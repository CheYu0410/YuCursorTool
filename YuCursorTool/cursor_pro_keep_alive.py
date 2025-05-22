import os
import platform
import json
import sys
from colorama import Fore, Style
from enum import Enum
from typing import Optional
import argparse
import base64
import hashlib
import uuid
import requests
import traceback  # 添加缺失的 traceback 導入

from exit_cursor import ExitCursor
from start_cursor import StartCursor
import go_cursor_help
import patch_cursor_get_machine_id
from reset_machine import MachineIDResetter
from disable_auto_update import AutoUpdateDisabler

os.environ["PYTHONVERBOSE"] = "0"
os.environ["PYINSTALLER_VERBOSE"] = "0"

import time
import random
from cursor_auth_manager import CursorAuthManager
import os
from logger import logging
from browser_utils import BrowserManager
from get_email_code import EmailVerificationHandler
from logo import print_logo
from config import Config
from datetime import datetime

# 定义 EMOJI 字典
EMOJI = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}

# 定义URL常量
LOGIN_URL = "https://authenticator.cursor.sh"
SIGN_UP_URL = "https://authenticator.cursor.sh/sign-up"
SETTINGS_URL = "https://www.cursor.com/settings"
MAIL_URL = "https://tempmail.plus"


class VerificationStatus(Enum):
    """验证状态枚举"""

    PASSWORD_PAGE = "@name=password"
    CAPTCHA_PAGE = "@data-index=0"
    ACCOUNT_SETTINGS = "Account Settings"
    SIGN_UP = "sign-up"


class TurnstileError(Exception):
    """Turnstile 验证相关异常"""

    pass


def save_screenshot(tab, stage: str, timestamp: bool = True) -> None:
    """
    保存页面截图

    Args:
        tab: 浏览器标签页对象
        stage: 截图阶段标识
        timestamp: 是否添加时间戳
    """
    try:
        # 创建 screenshots 目录
        screenshot_dir = "screenshots"
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)

        # 生成文件名
        if timestamp:
            filename = f"turnstile_{stage}_{int(time.time())}.png"
        else:
            filename = f"turnstile_{stage}.png"

        filepath = os.path.join(screenshot_dir, filename)

        # 保存截图
        tab.get_screenshot(filepath)
        logging.debug(f"截图已保存: {filepath}")
    except Exception as e:
        logging.warning(f"截图保存失败: {str(e)}")


def check_verification_success(tab) -> Optional[VerificationStatus]:
    """
    检查验证是否成功

    Returns:
        VerificationStatus: 验证成功时返回对应状态，失败返回 None
    """
    for status in VerificationStatus:
        if tab.ele(status.value):
            logging.info(f"验证成功 - 已到达{status.name}页面")
            return status
    return None


def handle_turnstile(tab, max_retries: int = 2, retry_interval: tuple = (1, 2)) -> bool:
    """
    处理 Turnstile 验证

    Args:
        tab: 浏览器标签页对象
        max_retries: 最大重试次数
        retry_interval: 重试间隔时间范围(最小值, 最大值)

    Returns:
        bool: 验证是否成功

    Raises:
        TurnstileError: 验证过程中出现异常
    """
    logging.info("正在检测 Turnstile 验证...")
    save_screenshot(tab, "start")

    retry_count = 0

    try:
        while retry_count < max_retries:
            retry_count += 1
            logging.debug(f"第 {retry_count} 次尝试验证")

            try:
                # 定位验证框元素
                challenge_check = (
                    tab.ele("@id=cf-turnstile", timeout=2)
                    .child()
                    .shadow_root.ele("tag:iframe")
                    .ele("tag:body")
                    .sr("tag:input")
                )

                if challenge_check:
                    logging.info("检测到 Turnstile 验证框，开始处理...")
                    # 随机延时后点击验证
                    time.sleep(random.uniform(1, 3))
                    challenge_check.click()
                    time.sleep(2)

                    # 保存验证后的截图
                    save_screenshot(tab, "clicked")

                    # 检查验证结果
                    if check_verification_success(tab):
                        logging.info("Turnstile 验证通过")
                        save_screenshot(tab, "success")
                        return True

            except Exception as e:
                logging.debug(f"当前尝试未成功: {str(e)}")

            # 检查是否已经验证成功
            if check_verification_success(tab):
                return True

            # 随机延时后继续下一次尝试
            time.sleep(random.uniform(*retry_interval))

        # 超出最大重试次数
        logging.error(f"验证失败 - 已达到最大重试次数 {max_retries}")
        logging.error(
            "请前往开源项目查看更多信息：https://github.com/chengazhen/cursor-auto-free"
        )
        save_screenshot(tab, "failed")
        return False

    except Exception as e:
        error_msg = f"Turnstile 验证过程发生异常: {str(e)}"
        logging.error(error_msg)
        save_screenshot(tab, "error")
        raise TurnstileError(error_msg)


def get_cursor_session_token(tab, max_attempts=3, retry_interval=2):
    """
    获取Cursor会话token和完整cookie
    :param tab: 浏览器标签页
    :param max_attempts: 最大尝试次数
    :param retry_interval: 重试间隔(秒)
    :return: dict 包含 token 和 full_cookie 或 None
    """
    logging.info("开始获取Cursor会话令牌")
    
    # 生成授權參數
    params = generate_auth_params()
    url = f"https://www.cursor.com/cn/loginDeepControl?challenge={params['n']}&uuid={params['r']}&mode=login"
    logging.info(f"正在访问登入頁面: {url}")
    tab.get(url)
    
    # 等待頁面加載
    attempts = 0
    logged_in = False
    
    while attempts < max_attempts and not logged_in:
        # 檢查是否到達登入界面
        try:
            # 嘗試找到"You're currently logged in as:"文本
            login_status = tab.ele("You're currently logged in as:")
            if login_status:
                logged_in = True
                logging.info("已檢測到登入狀態頁面")
                break
        except:
            pass
            
        attempts += 1
        
        if attempts < max_attempts:
            logging.info(f"等待頁面加載，重試 {attempts}/{max_attempts}...")
            time.sleep(retry_interval)
    
    # 確保頁面完全加載
    time.sleep(2)
    
    # 點擊登入按鈕
    logging.info("嘗試點擊登入按鈕")
    click_result = tab.run_js("""
        try {
            const button = document.querySelectorAll(".min-h-screen")[1].querySelectorAll(".gap-4")[1].querySelectorAll("button")[1];
            if (button) {
                button.click();
                return true;
            } else {
                return false;
            }
        } catch (e) {
            console.error("選擇器錯誤:", e);
            return false;
        }
    """)
    
    if click_result:
        logging.info("成功點擊登入按鈕")
    else:
        logging.info("未找到或點擊登入按鈕失敗，嘗試通過cookie獲取token")
    
    # 輪詢登入結果
    auth_id, access_token, refresh_token = poll_for_login_result(params["r"], params["s"])
    
    # 如果輪詢獲取成功
    if access_token and refresh_token:
        logging.info("通過輪詢API成功獲取token")
        # 同時獲取cookie以備用
        result = {"token": access_token, "full_cookie": None, "user_id": auth_id}
        
        # 獲取完整cookie
        try:
            full_cookie = []
            cookies = tab.cookies()
            for cookie in cookies:
                cookie_str = f"{cookie.get('name')}={cookie.get('value')}"
                full_cookie.append(cookie_str)
                
            # 保存完整cookie字符串
            result["full_cookie"] = "; ".join(full_cookie)
        except Exception as e:
            logging.error(f"獲取cookie失敗: {str(e)}")
        
        return result
    
    # 如果輪詢失敗，嘗試從cookie中獲取token (舊方式備用)
    logging.info("輪詢API獲取token失敗，嘗試從cookie中獲取")
    attempts = 0
    result = {"token": None, "full_cookie": None, "user_id": None}

    while attempts < max_attempts:
        try:
            full_cookie = []
            cookies = tab.cookies()
            for cookie in cookies:
                cookie_str = f"{cookie.get('name')}={cookie.get('value')}"
                full_cookie.append(cookie_str)
                if cookie.get("name") == "WorkosCursorSessionToken":
                    # 提取令牌和用户ID
                    token = cookie["value"].split("%3A%3A")[1]
                    # 尝试从令牌中提取用户ID
                    try:
                        token_parts = cookie["value"].split("%3A%3A")[0]
                        if token_parts and token_parts.startswith("user_"):
                            result["user_id"] = token_parts
                    except Exception as e:
                        logging.error(f"无法从令牌中提取用户ID: {str(e)}")
                    result["token"] = token

            # 保存完整cookie字符串
            result["full_cookie"] = "; ".join(full_cookie)

            if result["token"]:
                logging.info("從cookie中成功獲取token")
                return result

            attempts += 1
            if attempts < max_attempts:
                logging.warning(
                    f"第 {attempts} 次尝试未获取到CursorSessionToken，{retry_interval}秒后重试..."
                )
                time.sleep(retry_interval)
            else:
                logging.error(
                    f"已达到最大尝试次数({max_attempts})，获取CursorSessionToken失败"
                )

        except Exception as e:
            logging.error(f"获取cookie失败: {str(e)}")
            attempts += 1
            if attempts < max_attempts:
                logging.info(f"将在 {retry_interval} 秒后重试...")
                time.sleep(retry_interval)

    return None


def update_cursor_auth(email=None, access_token=None, refresh_token=None):
    """
    更新Cursor身份驗證信息
    
    Args:
        email: 電子郵件
        access_token: 存取令牌
        refresh_token: 刷新令牌
        
    Returns:
        bool: 是否更新成功
    """
    try:
        # 移除可能的ANSI控制碼
        def remove_ansi_codes(text):
            if not text:
                return text
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            return ansi_escape.sub('', text) if isinstance(text, str) else text
        
        # 清理輸入資料
        email = remove_ansi_codes(email)
        access_token = remove_ansi_codes(access_token)
        refresh_token = remove_ansi_codes(refresh_token)
        
        auth_manager = CursorAuthManager()
        result = auth_manager.update_auth(email, access_token, refresh_token)
        
        if result:
            logging.info("認證資訊已更新")
            # 除錯輸出
            logging.debug(f"已使用以下資訊更新認證:")
            logging.debug(f"Email: {email}")
            logging.debug(f"Access Token: {access_token[:10]}..." if access_token else "無")
            logging.debug(f"Refresh Token: {refresh_token[:10]}..." if refresh_token else "無")
            
            # 將結果寫入特殊標記檔案，以便GUI可以檢測到認證更新
            try:
                with open("auth_updated.flag", "w", encoding="utf-8") as f:
                    f.write(f"認證資訊已更新,{email}")
            except Exception as write_err:
                logging.error(f"無法寫入認證更新標記: {str(write_err)}")
        else:
            logging.error("認證資訊更新失敗")
            
        return result
    except Exception as e:
        logging.error(f"更新認證資訊時發生錯誤: {str(e)}")
        return False


def sign_up_account(browser, tab, account, password, first_name, last_name, email_handler):
    """
    註冊新帳號
    
    Args:
        browser: 瀏覽器實例
        tab: 瀏覽器標籤頁
        account: 電子郵件地址
        password: 密碼
        first_name: 名字
        last_name: 姓氏
        email_handler: 郵件處理器實例
    
    Returns:
        bool: 是否註冊成功
    """
    logging.info("=== 開始註冊帳號流程 ===")
    logging.info(f"正在訪問註冊頁面: {SIGN_UP_URL}")
    tab.get(SIGN_UP_URL)

    # 首次註冊需要驗證
    if not tab.ele(VerificationStatus.SIGN_UP.value):
        handle_turnstile(tab)

    try:
        if tab.ele("@name=first_name"):
            logging.info("填寫個人資訊")
            tab.actions.click("@name=first_name").input(first_name)
            logging.info(f"輸入名字: {first_name}")
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@name=last_name").input(last_name)
            logging.info(f"輸入姓氏: {last_name}")
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@name=email").input(account)
            logging.info(f"輸入註冊郵箱: {account}")
            if hasattr(email_handler, 'receive_email') and email_handler.receive_email != account:
                logging.info(f"驗證碼將發送至: {email_handler.receive_email}")
            time.sleep(random.uniform(1, 3))

            logging.info("提交個人資訊")
            tab.actions.click("@type=submit")

    except Exception as e:
        logging.error(f"訪問註冊頁面失敗: {str(e)}")
        return False

    handle_turnstile(tab)

    try:
        if tab.ele("@name=password"):
            logging.info("設置密碼")
            tab.ele("@name=password").input(password)
            time.sleep(random.uniform(1, 3))

            logging.info("提交密碼")
            tab.ele("@type=submit").click()
            logging.info("密碼設置完成")

    except Exception as e:
        logging.error(f"設置密碼失敗: {str(e)}")
        return False

    if tab.ele("This email is not available."):
        logging.error("註冊失敗：郵箱已被使用")
        return False

    handle_turnstile(tab)

    while True:
        try:
            if tab.ele("Account Settings"):
                logging.info("註冊成功")
                break
            if tab.ele("@data-index=0"):
                logging.info("獲取郵箱驗證碼")
                code = email_handler.get_verification_code()
                if not code:
                    logging.error("獲取驗證碼失敗")
                    return False

                logging.info(f"成功獲取驗證碼: {code}")
                logging.info("正在輸入驗證碼")
                i = 0
                for digit in code:
                    tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(random.uniform(0.1, 0.3))
                    i += 1
                logging.info("驗證碼輸入完成")
                break
        except Exception as e:
            logging.error(f"驗證碼處理過程錯誤: {str(e)}")

    handle_turnstile(tab)
    wait_time = random.randint(3, 6)
    for i in range(wait_time):
        logging.info(f"等待系統處理，還剩 {wait_time-i} 秒")
        time.sleep(1)

    logging.info("獲取帳號資訊")
    tab.get(SETTINGS_URL)
    try:
        usage_selector = (
            "css:div.col-span-2 > div > div > div > div > "
            "div:nth-child(1) > div.flex.items-center.justify-between.gap-2 > "
            "span.font-mono.text-sm\\/\\[0\\.875rem\\]"
        )
        usage_ele = tab.ele(usage_selector)
        if usage_ele:
            usage_info = usage_ele.text
            total_usage = usage_info.split("/")[-1].strip()
            logging.info(f"帳號使用限制: {total_usage}")
            logging.info(
                "Please visit the open source project for more information: https://github.com/wangffei/wf-cursor-auto-free.git"
            )
    except Exception as e:
        logging.error(f"獲取帳號使用資訊失敗: {str(e)}")

    logging.info("註冊完成")
    account_info = f"Cursor 帳號資訊:\n郵箱: {account}\n密碼: {password}"
    logging.info(account_info)
    time.sleep(5)
    return True


class EmailGenerator:
    def __init__(
        self,
        password="".join(
            random.choices(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",
                k=12,
            )
        ),
    ):
        configInstance = Config()
        configInstance.print_config()
        self.domain = configInstance.get_domain()
        self.names = self.load_names()
        self.default_password = password
        self.default_first_name = self.generate_random_name()
        self.default_last_name = self.generate_random_name()

    def load_names(self):
        with open("names-dataset.txt", "r") as file:
            return file.read().split()

    def generate_random_name(self):
        """生成随机用户名"""
        return random.choice(self.names)

    def generate_email(self, length=4):
        """生成随机邮箱地址，用於註冊Cursor帳號
        
        Args:
            length: 時間戳位數
            
        Returns:
            str: 生成的郵箱地址
        """
        # 使用域名生成註冊用郵箱
        length = random.randint(1, length)  # 生成1到length之间的随机整数
        timestamp = str(int(time.time()))[-length:]  # 使用时间戳的最后length位
        return f"{self.default_first_name}{timestamp}@{self.domain}"

    def get_account_info(self):
        """获取完整的账号信息"""
        return {
            "email": self.generate_email(),
            "password": self.default_password,
            "first_name": self.default_first_name,
            "last_name": self.default_last_name,
        }


def get_user_agent():
    """获取user_agent"""
    try:
        # 使用JavaScript获取user agent
        browser_manager = BrowserManager()
        browser = browser_manager.init_browser()
        user_agent = browser.latest_tab.run_js("return navigator.userAgent")
        browser_manager.quit()
        return user_agent
    except Exception as e:
        logging.error(f"获取user agent失败: {str(e)}")
        return None


def check_cursor_version():
    """
    檢查Cursor版本
    
    Returns:
        bool: 如果版本大於等於0.45.0則返回True，否則返回False
    """
    try:
        # 獲取Cursor路徑
        pkg_path, main_path = patch_cursor_get_machine_id.get_cursor_paths()
        
        # 讀取package.json獲取版本信息
        with open(pkg_path, "r", encoding="utf-8") as f:
            version = json.load(f)["version"]
            
        # 檢查版本是否≥0.45.0
        return patch_cursor_get_machine_id.version_check(version, min_version="0.45.0")
    except Exception as e:
        logging.error(f"檢查Cursor版本時出錯: {str(e)}")
        # 默認假設版本大於0.45.0，以確保使用安全的重置方法
        return True


def reset_machine_id(greater_than_0_45=True):
    """
    重置機器碼
    
    Args:
        greater_than_0_45: 是否為0.45.0或更高版本
        
    Returns:
        bool: 是否成功重置機器碼
    """
    try:
        logging.info("正在重置機器碼...")
        
        if greater_than_0_45:
            # ≥0.45.0版本，使用幫助模式
            logging.info("檢測到Cursor版本 ≥ 0.45.0，使用新的重置方法")
            go_cursor_help.go_cursor_help()
        else:
            # <0.45.0版本，使用直接重置
            logging.info("檢測到Cursor版本 < 0.45.0，使用舊的重置方法")
            MachineIDResetter().reset_machine_ids()
            
        logging.info("機器碼重置完成")
        return True
    except Exception as e:
        logging.error(f"重置機器碼時出錯: {str(e)}")
        return False


def disable_auto_update():
    """
    禁用自動更新
    
    Returns:
        bool: 是否成功禁用自動更新
    """
    try:
        logging.info("正在禁用自動更新...")
        AutoUpdateDisabler().disable_auto_update()
        logging.info("自動更新已禁用")
        return True
    except Exception as e:
        logging.error(f"禁用自動更新時出錯: {str(e)}")
        return False


def print_end_message():
    # 簡化結束訊息
    logging.info("=" * 30)
    logging.info("所有操作已完成")


def generate_auth_params():
    """
    生成身份驗證所需的參數
    
    Returns:
        Dict[str, str]: 包含驗證參數的字典
    """
    # 1. 生成 code_verifier (t) - 32字節隨機數
    t = os.urandom(32)  # 等效於 JS 的 crypto.getRandomValues(new Uint8Array(32))
    
    # 2. 生成 s: 對 t 進行 Base64 URL 安全編碼
    def tb(data):
        # Base64 URL 安全編碼（替換 +/ 為 -_，去除末尾的 =）
        return base64.urlsafe_b64encode(data).decode().rstrip('=')
    
    s = tb(t)  # 對應 JS 的 this.tb(t)
    
    # 3. 生成 n: 對 s 進行 SHA-256 哈希 + Base64 URL 編碼
    def ub(s_str):
        # 等效於 JS 的 TextEncoder().encode(s) + SHA-256
        return hashlib.sha256(s_str.encode()).digest()
    
    hashed = ub(s)
    n = tb(hashed)  # 對應 JS 的 this.tb(new Uint8Array(hashed))
    
    # 4. 生成 r: UUID v4
    r = str(uuid.uuid4())  # 對應 JS 的 $t()
    
    return {
        "t": t.hex(),      # 原始字節轉十六進制字符串（方便查看）
        "s": s,
        "n": n,
        "r": r
    }

def poll_for_login_result(uuid, challenge):
    """
    輪詢獲取登入結果
    
    Args:
        uuid: 身份驗證UUID
        challenge: 驗證挑戰碼
        
    Returns:
        Tuple[Optional[str], Optional[str], Optional[str]]: (authId, accessToken, refreshToken)
    """
    poll_url = f"https://api2.cursor.sh/auth/poll?uuid={uuid}&verifier={challenge}"
    headers = {
        "Content-Type": "application/json"
    }
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        logging.info("正在輪詢登入結果...")
        try:
            response = requests.get(poll_url, headers=headers)
            
            if response.status_code == 404:
                logging.info("登入尚未完成")
            elif response.status_code == 200:
                data = response.json()
                
                if "authId" in data and "accessToken" in data and "refreshToken" in data:
                    logging.info("登入成功!")
                    logging.debug(f"Auth ID: {data['authId']}")
                    logging.debug(f"Access Token: {data['accessToken'][:10]}...")
                    logging.debug(f"Refresh Token: {data['refreshToken'][:10]}...")
                    return data['authId'], data['accessToken'], data['refreshToken']
            
        except Exception as e:
            logging.error(f"輪詢過程中出錯: {e}")
            
        attempt += 1
        time.sleep(2)  # 每 2 秒輪詢一次
        
    if attempt >= max_attempts:
        logging.error("輪詢超時")
        
    return None, None, None


def save_account_info(email=None, password=None, 
                   access_token=None, refresh_token=None,
                   user_id=None, cookie=None, membership=None, account_status=None, usage=None) -> bool:
    """
    將帳號資訊保存為JSON檔案
    
    Args:
        email: 註冊郵箱
        password: 帳號密碼
        access_token: 訪問令牌
        refresh_token: 刷新令牌
        user_id: 用戶ID
        cookie: 完整cookie
        membership: 會員資訊
        account_status: 帳號狀態
        usage: 用量資訊
    
    Returns:
        bool: 是否成功保存
    """
    try:
        # 移除可能的ANSI控制碼
        def remove_ansi_codes(text):
            if not text:
                return text
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            return ansi_escape.sub('', text) if isinstance(text, str) else text
        
        # 清理輸入資料
        email = remove_ansi_codes(email)
        password = remove_ansi_codes(password)
        access_token = remove_ansi_codes(access_token)
        refresh_token = remove_ansi_codes(refresh_token)
        user_id = remove_ansi_codes(user_id)
        cookie = remove_ansi_codes(cookie)
        membership = remove_ansi_codes(membership)
        account_status = remove_ansi_codes(account_status)
        usage = remove_ansi_codes(usage)
        
        logging.info("保存帳號資訊")
        
        # 創建accounts目錄（如果不存在）
        accounts_dir = "accounts"
        if not os.path.exists(accounts_dir):
            os.makedirs(accounts_dir)
        
        # 生成檔案名（使用時間戳確保唯一性）
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"cursor_account_{timestamp}.json"
        filepath = os.path.join(accounts_dir, filename)
        
        # 創建帳號資訊字典
        account_info = {
            "email": email,
            "password": password,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": user_id,
            "cookie": cookie,
            "membership": membership,
            "account_status": account_status,
            "usage": usage,
            "created_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 寫入JSON檔案
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(account_info, f, indent=4, ensure_ascii=False)
        
        logging.info(f"帳號資訊已成功保存到 {filepath}")
        
        # 在控制台打印帳號資訊和保存路徑
        print("\n" + "="*50)
        print(f"📁 帳號資訊已成功保存到 {filepath}")
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")
        print("="*50 + "\n")
        
        # 嘗試將資訊添加到帳號管理器
        try:
            from accounts_manager import AccountsManager
            accounts_manager = AccountsManager()
            
            # 使用更可靠的方法添加帳號
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            success = accounts_manager.add_account(
                email=email,
                password=password,
                access_token=access_token,
                refresh_token=refresh_token,
                user_id=user_id,
                membership=membership,
                account_status=account_status,
                usage=usage,
                created_at_override=current_time
            )
            
            if success:
                logging.info("帳號已新增到帳號管理器")
            else:
                logging.warning("通過帳號管理器API添加帳號失敗，嘗試直接操作JSON")
                
                # 直接操作JSON作為備用方案
                try:
                    accounts_file = accounts_manager.accounts_file
                    accounts = []
                    if os.path.exists(accounts_file):
                        try:
                            with open(accounts_file, 'r', encoding='utf-8') as f:
                                accounts = json.load(f)
                        except Exception as read_ex:
                            logging.warning(f"讀取帳號檔案失敗: {str(read_ex)}，將創建新檔案")
                    
                    # 檢查是否已存在該帳號
                    found = False
                    for account in accounts:
                        if account.get('email') == email:
                            account['password'] = password
                            if access_token is not None:
                                account['access_token'] = access_token
                            if refresh_token is not None:
                                account['refresh_token'] = refresh_token
                            if user_id is not None:
                                account['user'] = user_id
                            if membership is not None:
                                account['membership'] = membership
                            if account_status is not None:
                                account['account_status'] = account_status
                            if usage is not None:
                                account['usage'] = usage
                            account['updated_at'] = current_time
                            found = True
                            logging.info(f"透過直接JSON操作更新現有帳號")
                            break
                    
                    if not found:
                        # 添加新帳號
                        new_account = {
                            'email': email,
                            'password': password,
                            'created_at': current_time,
                            'updated_at': current_time
                        }
                        if access_token is not None:
                            new_account['access_token'] = access_token
                        if refresh_token is not None:
                            new_account['refresh_token'] = refresh_token
                        if user_id is not None:
                            new_account['user'] = user_id
                        if membership is not None:
                            new_account['membership'] = membership
                        if account_status is not None:
                            new_account['account_status'] = account_status
                        if usage is not None:
                            new_account['usage'] = usage
                        
                        accounts.append(new_account)
                        logging.info(f"透過直接JSON操作添加新帳號")
                    
                    # 保存到檔案
                    with open(accounts_file, 'w', encoding='utf-8') as f:
                        json.dump(accounts, f, ensure_ascii=False, indent=2)
                    
                    logging.info(f"通過直接操作JSON成功儲存帳號到 {accounts_file}")
                
                except Exception as json_ex:
                    logging.error(f"直接操作JSON檔案失敗: {str(json_ex)}")
        except Exception as e:
            logging.warning(f"無法新增帳號到帳號管理器: {str(e)}")
        
        return True
    except Exception as e:
        logging.error(f"保存帳號資訊失敗: {str(e)}")
        return False


def sign_up_and_save(headless=True):
    """
    完整的註冊流程：註冊帳號並儲存帳號資訊
    
    Args:
        headless: 是否使用無頭模式
        
    Returns:
        bool: 是否註冊成功
    """
    try:
        logging.info("開始註冊流程")
        
        # 退出可能運行的Cursor實例
        ExitCursor()
        
        # 獲取Cursor版本
        greater_than_0_45 = check_cursor_version()
        
        # 創建瀏覽器管理器
        browser_manager = BrowserManager()
        
        # 設置環境變數以控制無頭模式，而不是直接調用不存在的 use_headless 方法
        if not headless:
            os.environ["BROWSER_HEADLESS"] = "false"
        else:
            os.environ["BROWSER_HEADLESS"] = "True"
        
        # 初始化瀏覽器
        browser = browser_manager.init_browser()
        tab = browser.latest_tab
        
        # 生成隨機帳號
        email_generator = EmailGenerator()
        account = email_generator.generate_email()
        password = email_generator.default_password
        first_name = email_generator.default_first_name
        last_name = email_generator.default_last_name
        
        # 創建郵件處理器
        email_handler = EmailVerificationHandler(account)
        
        # 重置turnstile
        tab.run_js("try { turnstile.reset() } catch(e) { }")
        
        # 註釋掉這行日誌輸出
        # logging.info(f"開始註冊帳號: {account}")
        logging.info(f"訪問登入頁面: {LOGIN_URL}")
        tab.get(LOGIN_URL)
        
        # 執行註冊流程
        if sign_up_account(browser, tab, account, password, first_name, last_name, email_handler):
            logging.info("獲取session token")
            token_info = get_cursor_session_token(tab)
            
            if token_info and token_info["token"]:
                # 在儲存前獲取帳號的用量和會員資訊
                logging.info("獲取帳號用量和會員資訊...")
                membership_info = None
                usage_info = None
                
                try:
                    # 使用 cursor_acc_info 中的方法獲取用量資訊
                    import cursor_acc_info
                    token = token_info["token"]
                    
                    # 獲取用量資訊
                    logging.info(f"獲取用量資訊...")
                    usage_info = cursor_acc_info.UsageManager.get_usage(token)
                    if usage_info:
                        logging.info(f"成功獲取用量資訊: {usage_info}")
                    else:
                        logging.warning("無法獲取用量資訊，將使用預設值")
                        usage_info = {
                            "premium_usage": 0, 
                            "max_premium_usage": 50, 
                            "basic_usage": 0, 
                            "max_basic_usage": "No Limit"
                        }
                    
                    # 獲取會員資訊
                    logging.info(f"獲取會員資訊...")
                    membership_info = cursor_acc_info.UsageManager.get_stripe_profile(token)
                    if membership_info:
                        logging.info(f"成功獲取會員資訊: {membership_info}")
                        account_status = cursor_acc_info.format_subscription_type(membership_info)
                    else:
                        logging.warning("無法獲取會員資訊，將使用預設值")
                        membership_info = {
                            "membershipType": "free",
                            "daysRemainingOnTrial": 0,
                            "verifiedStudent": False
                        }
                        account_status = "Free"
                except Exception as e:
                    logging.error(f"獲取用量和會員資訊時出錯: {str(e)}")
                    traceback.print_exc()
                    # 使用預設值
                    usage_info = {
                        "premium_usage": 0, 
                        "max_premium_usage": 50, 
                        "basic_usage": 0, 
                        "max_basic_usage": "No Limit"
                    }
                    membership_info = {
                        "membershipType": "free",
                        "daysRemainingOnTrial": 0,
                        "verifiedStudent": False
                    }
                    account_status = "Free"
                
                # 儲存帳號資訊
                save_account_info(
                    email=account,
                    password=password,
                    access_token=token_info["token"],
                    refresh_token=token_info["token"],
                    user_id=token_info["user_id"],
                    cookie=token_info["full_cookie"],
                    membership=membership_info,
                    account_status=account_status,
                    usage=usage_info
                )
                
                # 更新認證資訊
                update_cursor_auth(
                    email=account,
                    access_token=token_info["token"],
                    refresh_token=token_info["token"]
                )
                
                # 重置機器碼
                reset_machine_id(greater_than_0_45)
                logging.info("註冊完成")
                print_end_message()
                
                # 啟動Cursor
                if headless:
                    StartCursor()
                
                return True
            else:
                logging.error("獲取會話令牌失敗，註冊流程未完成")
                return False
        else:
            logging.error("註冊帳號失敗")
            return False
    except Exception as e:
        logging.error(f"註冊流程出錯: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        # 關閉瀏覽器
        if 'browser_manager' in locals():
            browser_manager.quit()


def main():
    """主函數入口"""
    print_logo()
    
    try:
        logging.info("初始化程序")

        # 提示用戶選擇操作模式
        print("請選擇操作模式：")
        print("1. 僅重置機器碼")
        print("2. 完整註冊流程")
        print("3. 僅註冊帳號")
        print("4. 禁用自動更新")
        print("5. 選擇已保存的帳號")

        while True:
            try:
                choice = int(input("請輸入選項 (1-5): ").strip())
                if choice in [1, 2, 3, 4, 5]:
                    break
                else:
                    print("無效的選項，請重新輸入")
            except ValueError:
                print("請輸入有效的數字")

        # 根據用戶選擇執行不同的操作
        if choice == 1:  # 僅重置機器碼
            ExitCursor()
            greater_than_0_45 = check_cursor_version()
            reset_machine_id(greater_than_0_45)
            print_end_message()
            
        elif choice == 2:  # 完整註冊流程
            sign_up_and_save(headless=False)
            
        elif choice == 3:  # 僅註冊帳號
            sign_up_and_save(headless=True)
            
        elif choice == 4:  # 禁用自動更新
            disable_auto_update()
            
        elif choice == 5:  # 選擇已保存的帳號
            # 列出並應用已保存的帳號
            list_and_select_accounts()
                
    except Exception as e:
        logging.error(f"程序錯誤: {str(e)}")
        traceback.print_exc()
    finally:
        input("按 Enter 鍵退出...")


def list_and_select_accounts():
    """
    列出所有已保存的帳號，讓用戶選擇一個應用
    
    Returns:
        bool: 是否成功應用帳號
    """
    # 檢查accounts目錄是否存在
    accounts_dir = "accounts"
    if not os.path.exists(accounts_dir):
        logging.error(f"未找到帳號目錄：{accounts_dir}")
        print(f"錯誤：未找到帳號目錄 {accounts_dir}")
        return False
    
    # 獲取所有JSON文件
    account_files = [f for f in os.listdir(accounts_dir) if f.endswith('.json')]
    if not account_files:
        logging.error(f"在 {accounts_dir} 中未找到帳號文件")
        print(f"錯誤：在 {accounts_dir} 中未找到帳號文件")
        return False
    
    # 按創建時間排序（文件名中的時間戳）
    account_files.sort(reverse=True)
    
    # 顯示帳號列表
    print("\n=== 已保存的帳號 ===")
    for i, filename in enumerate(account_files):
        try:
            filepath = os.path.join(accounts_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                account_data = json.load(f)
                email = account_data.get('email', '未知')
                created_time = account_data.get('created_time', '未知時間')
                print(f"{i+1}. {email} (創建時間: {created_time})")
        except Exception as e:
            print(f"{i+1}. {filename} [讀取錯誤: {str(e)}]")
    
    # 用戶選擇
    print("\n0. 返回主菜單")
    
    while True:
        try:
            choice = int(input("請選擇帳號編號: ").strip())
            if choice == 0:
                return False
            elif 1 <= choice <= len(account_files):
                selected_file = account_files[choice-1]
                return apply_account_from_file(os.path.join(accounts_dir, selected_file))
            else:
                print("無效的選擇，請重試")
        except ValueError:
            print("請輸入數字")

def apply_account_from_file(filepath):
    """
    從文件中讀取帳號資訊並應用
    
    Args:
        filepath: 帳號信息文件路徑
    
    Returns:
        bool: 是否成功應用
    """
    try:
        logging.info(f"正在從 {filepath} 加載帳號資訊")
        
        # 讀取帳號資訊
        with open(filepath, 'r', encoding='utf-8') as f:
            account_data = json.load(f)
        
        email = account_data.get('email')
        password = account_data.get('password')
        access_token = account_data.get('access_token')
        refresh_token = account_data.get('refresh_token')
        user_id = account_data.get('user_id')
        
        if not email or not access_token or not refresh_token:
            logging.error("帳號資訊不完整")
            print("錯誤：帳號資訊不完整，缺少必要資訊")
            return False
        
        logging.info(f"使用帳號: {email}")
        logging.info("正在更新認證資訊")
        
        # 退出可能運行的Cursor實例
        ExitCursor()
        
        # 更新認證資訊
        result = update_cursor_auth(
            email=email,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        if result:
            logging.info("認證資訊已更新")
            
            # 獲取Cursor版本
            greater_than_0_45 = check_cursor_version()
            
            # 重置機器碼
            reset_machine_id(greater_than_0_45)
            
            logging.info("所有操作已完成")
            print_end_message()
            
            # 啟動Cursor
            StartCursor()
            
            return True
        else:
            logging.error("應用帳號失敗")
            print("錯誤：應用帳號失敗，認證資訊更新失敗")
            return False
    
    except Exception as e:
        logging.error(f"應用帳號時出錯: {str(e)}")
        print(f"錯誤：應用帳號時出錯: {str(e)}")
        return False


if __name__ == "__main__":
    main()
