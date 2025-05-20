import os
import platform
import json
import sys
from colorama import Fore, Style
from enum import Enum
from typing import Optional, Dict, Any, Tuple, List, Union, Callable
import traceback
import secrets
import base64
import hmac
import hashlib
import uuid
import requests
from disable_auto_update import AutoUpdateDisabler 

from exit_cursor import ExitCursor
from start_cursor import StartCursor
import go_cursor_help
import patch_cursor_get_machine_id
from reset_machine import MachineIDResetter
from language import language, get_translation

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

# 定义URL常量
LOGIN_URL = "https://authenticator.cursor.sh"
SIGN_UP_URL = "https://authenticator.cursor.sh/sign-up"
SETTINGS_URL = "https://www.cursor.com/settings"
MAIL_URL = "https://tempmail.plus"

# Define EMOJI dictionary
EMOJI = {"ERROR": get_translation("error"), "WARNING": get_translation("warning"), "INFO": get_translation("info")}

index = 0

class VerificationStatus(Enum):
    """Verification status enum"""
    SIGN_UP = "@name=first_name"
    PASSWORD_PAGE = "@name=password"
    CAPTCHA_PAGE = "@data-index=0"
    ACCOUNT_SETTINGS = "Account Settings"
    TOKEN_REFRESH = "You're currently logged in as:"


class TurnstileError(Exception):
    """Turnstile verification related exception"""
    pass


class CursorProKeepAlive:
    """主类，封装所有Cursor相关操作"""
    
    def __init__(self):
        """初始化CursorProKeepAlive实例"""
        self.browser_manager = None
        self.browser = None
        self.tab = None
        self.email_generator = None
        self.email_handler = None
        self.account = None
        self.password = None
        self.first_name = None
        self.last_name = None
        self.access_token = None
        self.refresh_token = None
        self.greater_than_0_45 = self.check_cursor_version()
        
    def init_browser(self) -> bool:
        """初始化浏览器实例"""
        try:
            logging.info(get_translation("initializing_browser"))
            
            # 获取用户代理
            user_agent = self.get_user_agent()
            if not user_agent:
                logging.error(get_translation("get_user_agent_failed"))
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            
            # 移除"HeadlessChrome"
            user_agent = user_agent.replace("HeadlessChrome", "Chrome")
            
            # 初始化浏览器
            self.browser_manager = BrowserManager()
            self.browser = self.browser_manager.init_browser(user_agent)
            self.tab = self.browser.latest_tab
            
            # 验证用户代理设置成功
            actual_user_agent = self.tab.run_js("return navigator.userAgent")
            logging.debug(f"Browser user agent: {actual_user_agent}")
            
            return True
        except Exception as e:
            logging.error(f"Browser initialization failed: {str(e)}")
            return False
    
    def cleanup(self):
        """清理浏览器资源"""
        if self.browser_manager:
            logging.info(get_translation("closing_browser"))
            self.browser_manager.quit()
    
    def get_user_agent(self) -> Optional[str]:
        """获取用户代理字符串"""
        try:
            # 使用JavaScript获取用户代理
            temp_browser_manager = BrowserManager()
            temp_browser = temp_browser_manager.init_browser()
            user_agent = temp_browser.latest_tab.run_js("return navigator.userAgent")
            temp_browser_manager.quit()
            return user_agent
        except Exception as e:
            logging.error(f"Failed to get user agent: {str(e)}")
            return None
    
    def check_cursor_version(self) -> bool:
        """检查Cursor版本"""
        pkg_path, main_path = patch_cursor_get_machine_id.get_cursor_paths()
        with open(pkg_path, "r", encoding="utf-8") as f:
            version = json.load(f)["version"]
        return patch_cursor_get_machine_id.version_check(version, min_version="0.45.0")
    
    def reset_machine_id(self) -> bool:
        """重置机器ID"""
        try:
            logging.info(get_translation("resetting_machine_code"))
            if self.greater_than_0_45:
                # 提示手动执行脚本
                go_cursor_help.go_cursor_help()
            else:
                MachineIDResetter().reset_machine_ids()
            logging.info(get_translation("machine_code_reset_complete"))
            return True
        except Exception as e:
            logging.error(f"Failed to reset machine ID: {str(e)}")
            return False
    
    def disable_auto_update(self) -> bool:
        """禁用自动更新"""
        try:
            logging.info(get_translation("disabling_auto_update"))
            AutoUpdateDisabler().disable_auto_update()
            logging.info(get_translation("auto_update_disabled"))
            return True
        except Exception as e:
            logging.error(f"Failed to disable auto update: {str(e)}")
            return False
    
    def update_cursor_auth(self, email: str = None, access_token: str = None, refresh_token: str = None) -> bool:
        """更新Cursor身份验证信息"""
        try:
            email = email or self.account
            access_token = access_token or self.access_token
            refresh_token = refresh_token or self.refresh_token
            
            auth_manager = CursorAuthManager()
            result = auth_manager.update_auth(email, access_token, refresh_token)
            
            if result:
                logging.info(get_translation("auth_info_updated"))
            else:
                logging.error(get_translation("auth_update_failed"))
                
            return result
        except Exception as e:
            logging.error(f"Failed to update auth info: {str(e)}")
            return False
    
    def start_cursor(self) -> None:
        """启动Cursor"""
        if os.getenv("BROWSER_HEADLESS", "True").lower() == "true":
            StartCursor()
    
    def generate_account(self) -> Dict[str, str]:
        """生成随机账号信息"""
        try:
            logging.info(get_translation("generating_random_account"))
            
            self.email_generator = EmailGenerator()
            self.first_name = self.email_generator.default_first_name
            self.last_name = self.email_generator.default_last_name
            self.account = self.email_generator.generate_email()
            self.password = self.email_generator.default_password
            
            logging.info(get_translation("generated_email_account", email=self.account))
            
            # 初始化邮件验证处理器
            self.email_handler = EmailVerificationHandler(self.account)
            
            return {
                "email": self.account,
                "password": self.password,
                "first_name": self.first_name,
                "last_name": self.last_name
            }
        except Exception as e:
            logging.error(f"Failed to generate account: {str(e)}")
            return {}
    
    def print_end_message(self) -> None:
        """打印结束消息"""
        logging.info("\n\n\n\n\n")
        logging.info("=" * 30)
        logging.info(get_translation("all_operations_completed"))
        logging.info("\n=== Get More Information ===")
        logging.info("🔥 WeChat Official Account: wf5569")
        logging.info("=" * 30)
        logging.info(
            "Please visit the open source project for more information: https://github.com/wangffei/wf-cursor-auto-free.git"
        )

    def save_account_info(self, email: str = None, password: str = None, 
                         access_token: str = None, refresh_token: str = None) -> bool:
        """
        将账号信息保存为JSON文件
        
        Args:
            email: 注册邮箱
            password: 账号密码
            access_token: 访问令牌
            refresh_token: 刷新令牌
        """
        email = email or self.account
        password = password or self.password
        access_token = access_token or self.access_token
        refresh_token = refresh_token or self.refresh_token
        
        logging.info(get_translation("saving_account_info"))
        
        # 创建accounts目录（如果不存在）
        accounts_dir = "accounts"
        if not os.path.exists(accounts_dir):
            os.makedirs(accounts_dir)
        
        # 生成文件名（使用时间戳确保唯一性）
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"cursor_account_{timestamp}.json"
        filepath = os.path.join(accounts_dir, filename)
        
        # 创建账号信息字典
        account_info = {
            "email": email,
            "password": password,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "created_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 写入JSON文件
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(account_info, f, indent=4, ensure_ascii=False)
            logging.info(get_translation("account_saved_successfully", path=filepath))
            # 在控制台打印账号信息和保存路径
            print("\n" + "="*50)
            print(f"📁 {get_translation('account_saved_successfully', path=filepath)}")
            print(f"📧 Email: {email}")
            print(f"🔑 Password: {password}")
            print("="*50 + "\n")
            return True
        except Exception as e:
            logging.error(get_translation("account_save_failed", error=str(e)))
            return False
            
    def list_and_apply_saved_accounts(self) -> bool:
        """
        列出保存的账号并允许用户选择一个应用
        """
        accounts_dir = "accounts"
        if not os.path.exists(accounts_dir):
            logging.error(get_translation("accounts_dir_not_found", dir=accounts_dir))
            return False
        
        # 获取所有JSON文件
        account_files = [f for f in os.listdir(accounts_dir) if f.endswith('.json')]
        if not account_files:
            logging.error(get_translation("no_account_files_found", dir=accounts_dir))
            return False
        
        # 排序按照创建时间（文件名中包含的时间戳）
        account_files.sort(reverse=True)
        
        # 显示账号列表
        print(get_translation("saved_accounts_title"))
        for i, filename in enumerate(account_files):
            try:
                filepath = os.path.join(accounts_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    account_data = json.load(f)
                    email = account_data.get('email', 'N/A')
                    created_time = account_data.get('created_time', get_translation("account_created_time"))
                    print(f"{i+1}. {email} ({get_translation('account_created_time')}: {created_time})")
            except Exception as e:
                print(f"{i+1}. {filename} [{get_translation('reading_error')}: {str(e)}]")
        
        # 用户选择
        print(f"\n0. {get_translation('return_to_main_menu')}")
        while True:
            try:
                choice = int(input(f"{get_translation('select_account_number')}: ").strip())
                if choice == 0:
                    return False
                elif 1 <= choice <= len(account_files):
                    selected_file = account_files[choice-1]
                    return self.apply_account_from_file(os.path.join(accounts_dir, selected_file))
                else:
                    print(get_translation("invalid_selection"))
            except ValueError:
                print(get_translation("please_enter_number"))

    def apply_account_from_file(self, filepath: str) -> bool:
        """
        从文件中加载账号信息并应用
        
        Args:
            filepath: 账号信息文件路径
        
        Returns:
            bool: 是否成功应用
        """
        try:
            logging.info(get_translation("loading_account_info", path=filepath))
            
            with open(filepath, 'r', encoding='utf-8') as f:
                account_data = json.load(f)
            
            email = account_data.get('email')
            access_token = account_data.get('access_token')
            refresh_token = account_data.get('refresh_token')
            
            if not email or not access_token or not refresh_token:
                logging.error(get_translation("incomplete_account_info"))
                return False
            
            # 更新实例变量
            self.account = email
            self.access_token = access_token
            self.refresh_token = refresh_token
            
            logging.info(get_translation("using_account", email=email))
            logging.info(get_translation("updating_auth_info"))
            
            result = self.update_cursor_auth()
            
            if result:
                logging.info(
                    "Please visit the open source project for more information: https://github.com/wangffei/wf-cursor-auto-free.git"
                )
                self.reset_machine_id()
                logging.info(get_translation("all_operations_completed"))
                self.print_end_message()
                self.start_cursor()
                return True
            else:
                logging.error(get_translation("apply_account_failed"))
                return False
                
        except Exception as e:
            logging.error(get_translation("apply_account_error", error=str(e)))
            return False

    # 主要操作函数封装
    def option_reset_machine_id(self) -> bool:
        """选项1: 仅重置机器码"""
        try:
            ExitCursor()
            result = self.reset_machine_id()
            self.print_end_message()
            return result
        except Exception as e:
            logging.error(f"Failed to reset machine ID: {str(e)}")
            return False
            
    def option_disable_auto_update(self) -> bool:
        """选项4: 禁用自动更新"""
        try:
            ExitCursor()
            return self.disable_auto_update()
        except Exception as e:
            logging.error(f"Failed to disable auto update: {str(e)}")
            return False
            
    def option_apply_saved_account(self) -> bool:
        """选项5: 选择并应用已保存的账号"""
        try:
            ExitCursor()
            return self.list_and_apply_saved_accounts()
        except Exception as e:
            logging.error(f"Failed to apply saved account: {str(e)}")
            return False

    def handle_turnstile(self, tab=None, max_retries: int = 2, retry_interval: tuple = (1, 2)) -> bool:
        """
        处理Turnstile验证
        
        Args:
            tab: 浏览器标签对象
            max_retries: 最大重试次数
            retry_interval: 重试间隔范围(最小值, 最大值)
            
        Returns:
            bool: 验证是否成功
            
        Raises:
            TurnstileError: 验证过程中的异常
        """
        tab = tab or self.tab
        
        logging.info(get_translation("detecting_turnstile"))
        save_screenshot(tab, "start")
        
        retry_count = 0
        
        try:
            while retry_count < max_retries:
                retry_count += 1
                logging.debug(get_translation("retry_verification", count=retry_count))
                
                try:
                    element = None
                    try:
                        element = (
                            tab.ele(".main-content")  # 找到 .main-content 元素
                            .ele("tag:div")        # 找到第一个子 div
                            .ele("tag:div")        # 找到第二个子 div
                            .ele("tag:div")        # 找到第三个子 div
                        )
                    except Exception as e:
                        pass
                    if element:
                        # Locate verification frame element
                        challenge_check = (
                            element
                            .shadow_root.ele("tag:iframe")
                            .ele("tag:body")
                            .sr("tag:input")
                        )
                    else:
                        # Locate verification frame element
                        challenge_check = (
                            tab.ele("@id=cf-turnstile", timeout=2)
                            .child()
                            .shadow_root.ele("tag:iframe")
                            .ele("tag:body")
                            .sr("tag:input")
                        )
                        
                    if challenge_check:
                        logging.info(get_translation("detected_turnstile"))
                        # Random delay before clicking verification
                        time.sleep(random.uniform(1, 3))
                        challenge_check.click()
                        time.sleep(2)
                        
                        # Save screenshot after verification
                        save_screenshot(tab, "clicked")
                        
                        # Check verification result
                        if check_verification_success(tab):
                            save_screenshot(tab, "success")
                            return True
                        
                except Exception as e:
                    logging.debug(f"Current attempt unsuccessful: {str(e)}")
                    
                # Check if already verified
                if check_verification_success(tab):
                    return True
                    
                # Random delay before next attempt
                time.sleep(random.uniform(*retry_interval))
                
            # Exceeded maximum retries
            logging.error(get_translation("verification_failed_max_retries", max_retries=max_retries))
            logging.error(
                "Please visit the open source project for more information: https://github.com/wangffei/wf-cursor-auto-free.git"
            )
            save_screenshot(tab, "failed")
            return False
            
        except Exception as e:
            error_msg = get_translation("turnstile_exception", error=str(e))
            logging.error(error_msg)
            save_screenshot(tab, "error")
            raise TurnstileError(error_msg)
    
    def generate_auth_params(self) -> Dict[str, str]:
        """
        生成身份验证参数
        
        Returns:
            Dict[str, str]: 包含验证参数的字典
        """
        # 1. 生成 code_verifier (t) - 32字节随机数
        t = os.urandom(32)  # 等效于 JS 的 crypto.getRandomValues(new Uint8Array(32))
        
        # 2. 生成 s: 对 t 进行 Base64 URL 安全编码
        def tb(data):
            # Base64 URL 安全编码（替换 +/ 为 -_，去除末尾的 =）
            return base64.urlsafe_b64encode(data).decode().rstrip('=')
        
        s = tb(t)  # 对应 JS 的 this.tb(t)
        
        # 3. 生成 n: 对 s 进行 SHA-256 哈希 + Base64 URL 编码
        def ub(s_str):
            # 等效于 JS 的 TextEncoder().encode(s) + SHA-256
            return hashlib.sha256(s_str.encode()).digest()
        
        hashed = ub(s)
        n = tb(hashed)  # 对应 JS 的 this.tb(new Uint8Array(hashed))
        
        # 4. 生成 r: UUID v4
        r = str(uuid.uuid4())  # 对应 JS 的 $t()
        
        return {
            "t": t.hex(),      # 原始字节转十六进制字符串（方便查看）
            "s": s,
            "n": n,
            "r": r
        }
    
    def poll_for_login_result(self, uuid: str, challenge: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        轮询获取登录结果
        
        Args:
            uuid: 身份验证UUID
            challenge: 验证挑战码
            
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
            logging.info(get_translation("polling_login_result"))
            try:
                response = requests.get(poll_url, headers=headers)
                
                if response.status_code == 404:
                    logging.info(get_translation("login_not_completed"))
                elif response.status_code == 200:
                    data = response.json()
                    
                    if "authId" in data and "accessToken" in data and "refreshToken" in data:
                        logging.info(get_translation("login_successful"))
                        logging.debug(f"Auth ID: {data['authId']}")
                        logging.debug(f"Access Token: {data['accessToken'][:10]}...")
                        logging.debug(f"Refresh Token: {data['refreshToken'][:10]}...")
                        return data['authId'], data['accessToken'], data['refreshToken']
                
            except Exception as e:
                logging.error(f"Error during polling: {e}")
                
            attempt += 1
            time.sleep(2)  # 每 2 秒轮询一次
            
        if attempt >= max_attempts:
            logging.error(get_translation("polling_timed_out"))
            
        return None, None, None
    
    def get_cursor_session_token(self, tab=None, max_attempts=3, retry_interval=2) -> Tuple[Optional[str], Optional[str]]:
        """
        获取Cursor会话令牌
        
        Args:
            tab: 浏览器标签对象
            max_attempts: 最大尝试次数
            retry_interval: 重试间隔(秒)
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (accessToken, refreshToken)
        """
        tab = tab or self.tab
        
        params = self.generate_auth_params()
        url = f"https://www.cursor.com/cn/loginDeepControl?challenge={params['n']}&uuid={params['r']}&mode=login"
        tab.get(url)
        
        attempts = 0
        
        while attempts < max_attempts:
            # 检查是否到达登录界面
            status = check_verification_success(tab, VerificationStatus.TOKEN_REFRESH)
            if status:
                break
                
            attempts += 1
            
            if attempts < max_attempts:
                time.sleep(retry_interval)
                
        time.sleep(2)
        
        # 使用精确的CSS选择器在Python中查找元素并点击
        tab.run_js("""
            try {
                const button = document.querySelectorAll(".min-h-screen")[1].querySelectorAll(".gap-4")[1].querySelectorAll("button")[1];
                if (button) {
                    button.click();
                    return true;
                } else {
                    return false;
                }
            } catch (e) {
                console.error("选择器错误:", e);
                return false;
            }
        """)
        
        _, access_token, refresh_token = self.poll_for_login_result(params["r"], params["s"])
        
        # 更新实例变量
        if access_token and refresh_token:
            self.access_token = access_token
            self.refresh_token = refresh_token
            
        return access_token, refresh_token
    
    def sign_up_account(self, browser=None, tab=None) -> bool:
        """
        注册新账号
        
        Args:
            browser: 浏览器实例
            tab: 浏览器标签对象
            
        Returns:
            bool: 是否成功注册
        """
        browser = browser or self.browser
        tab = tab or self.tab
        
        logging.info(get_translation("start_account_registration"))
        logging.info(get_translation("visiting_registration_page", url=SIGN_UP_URL))
        tab.get(SIGN_UP_URL)
        
        # 首次注册需要验证的
        if not tab.ele(VerificationStatus.SIGN_UP.value):
            self.handle_turnstile(tab)
            
        try:
            if tab.ele("@name=first_name"):
                logging.info(get_translation("filling_personal_info"))
                tab.actions.click("@name=first_name").input(self.first_name)
                logging.info(get_translation("input_first_name", name=self.first_name))
                time.sleep(random.uniform(1, 3))
                
                tab.actions.click("@name=last_name").input(self.last_name)
                logging.info(get_translation("input_last_name", name=self.last_name))
                time.sleep(random.uniform(1, 3))
                
                tab.actions.click("@name=email").input(self.account)
                logging.info(get_translation("input_email", email=self.account))
                time.sleep(random.uniform(1, 3))
                
                logging.info(get_translation("submitting_personal_info"))
                tab.actions.click("@type=submit")
                
        except Exception as e:
            logging.error(get_translation("registration_page_access_failed", error=str(e)))
            return False
            
        self.handle_turnstile(tab)
        
        try:
            if tab.ele("@name=password"):
                logging.info(get_translation("setting_password"))
                tab.ele("@name=password").input(self.password)
                time.sleep(random.uniform(1, 3))
                
                logging.info(get_translation("submitting_password"))
                tab.ele("@type=submit").click()
                logging.info(get_translation("password_setup_complete"))
                
        except Exception as e:
            logging.error(get_translation("password_setup_failed", error=str(e)))
            return False
            
        if tab.ele("This email is not available."):
            logging.error(get_translation("registration_failed_email_used"))
            return False
            
        self.handle_turnstile(tab)
        
        while True:
            try:
                if tab.ele("Account Settings"):
                    logging.info(get_translation("registration_success"))
                    break
                if tab.ele("@data-index=0"):
                    logging.info(get_translation("getting_email_verification"))
                    code = self.email_handler.get_verification_code()
                    if not code:
                        logging.error(get_translation("verification_code_failure"))
                        return False
                        
                    logging.info(get_translation("verification_code_success", code=code))
                    logging.info(get_translation("inputting_verification_code"))
                    i = 0
                    for digit in code:
                        tab.ele(f"@data-index={i}").input(digit)
                        time.sleep(random.uniform(0.1, 0.3))
                        i += 1
                    logging.info(get_translation("verification_code_input_complete"))
                    break
            except Exception as e:
                logging.error(get_translation("verification_code_process_error", error=str(e)))
                
        self.handle_turnstile(tab)
        wait_time = random.randint(3, 6)
        for i in range(wait_time):
            logging.info(get_translation("waiting_system_processing", seconds=wait_time-i))
            time.sleep(1)
            
        logging.info(get_translation("getting_account_info"))
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
                logging.info(get_translation("account_usage_limit", limit=total_usage))
                logging.info(
                    "Please visit the open source project for more information: https://github.com/wangffei/wf-cursor-auto-free.git"
                )
        except Exception as e:
            logging.error(get_translation("account_usage_info_failure", error=str(e)))
            
        logging.info(get_translation("registration_complete"))
        account_info = get_translation("cursor_account_info", email=self.account, password=self.password)
        logging.info(account_info)
        time.sleep(5)
        return True

    def option_sign_up_only(self) -> bool:
        """选项3: 仅注册账号"""
        try:
            if not self.init_browser():
                return False
                
            self.generate_account()
            
            # 准备浏览器
            self.tab.run_js("try { turnstile.reset() } catch(e) { }")
            
            logging.info(get_translation("starting_registration"))
            logging.info(get_translation("visiting_login_page", url=LOGIN_URL))
            self.tab.get(LOGIN_URL)
            
            if self.sign_up_account():
                logging.info(get_translation("getting_session_token"))
                access_token, refresh_token = self.get_cursor_session_token()
                
                # 将账号密码写入一个json文件中
                if access_token and refresh_token:
                    if self.save_account_info():
                        logging.info(get_translation("account_info_saved"))
                        self.print_end_message()
                    else:
                        logging.error(get_translation("failed_to_save_account_info"))
                else:
                    logging.error(get_translation("session_token_failed"))
                    # 即使没有token，也保存账号和密码信息
                    self.save_account_info(access_token="", refresh_token="")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to sign up account: {str(e)}")
            return False
        finally:
            self.cleanup()
            
    def option_complete_registration(self) -> bool:
        """选项2: 完整注册流程"""
        try:
            ExitCursor()
            
            if not self.init_browser():
                return False
                
            self.generate_account()
            
            # 准备浏览器
            self.tab.run_js("try { turnstile.reset() } catch(e) { }")
            
            logging.info(get_translation("starting_registration"))
            logging.info(get_translation("visiting_login_page", url=LOGIN_URL))
            self.tab.get(LOGIN_URL)
            
            if self.sign_up_account():
                logging.info(get_translation("getting_session_token"))
                access_token, refresh_token = self.get_cursor_session_token()
                
                if access_token and refresh_token:
                    logging.info(get_translation("updating_auth_info"))
                    self.update_cursor_auth()
                    
                    logging.info(
                        "Please visit the open source project for more information: https://github.com/wangffei/wf-cursor-auto-free.git"
                    )
                    
                    self.reset_machine_id()
                    logging.info(get_translation("all_operations_completed"))
                    self.print_end_message()
                    
                    # 注册完成，启动cursor
                    self.start_cursor()
                    return True
                else:
                    logging.error(get_translation("session_token_failed"))
                    return False
            return False
        except Exception as e:
            logging.error(f"Failed to complete registration: {str(e)}")
            return False
        finally:
            self.cleanup()

def save_screenshot(tab, stage: str, timestamp: bool = True) -> None:
    """
    Save a screenshot of the page

    Args:
        tab: Browser tab object
        stage: Stage identifier for the screenshot
        timestamp: Whether to add a timestamp
    """
    try:
        # Create screenshots directory
        screenshot_dir = "screenshots"
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)

        # Generate filename
        if timestamp:
            filename = f"turnstile_{stage}_{int(time.time())}.png"
        else:
            filename = f"turnstile_{stage}.png"

        filepath = os.path.join(screenshot_dir, filename)

        # Save screenshot
        tab.get_screenshot(filepath)
        logging.debug(f"Screenshot saved: {filepath}")
    except Exception as e:
        logging.warning(f"Failed to save screenshot: {str(e)}")

def check_verification_success(tab, default_status=None) -> Optional[VerificationStatus]:
    global index
    """
    Check if verification was successful

    Returns:
        VerificationStatus: The corresponding status if successful, None if failed
    """
    if default_status:
        if tab.ele(default_status.value):
            logging.info(get_translation("verification_success", status=default_status.name))
            return default_status
        else:
            return None
    for idx,status in enumerate(VerificationStatus):
        if(idx == 0 and index != 0):
            continue
        if tab.ele(status.value):
            index = index + 1
            logging.info(get_translation("verification_success", status=status.name))
            return status
    return None

def handle_turnstile(tab, max_retries: int = 2, retry_interval: tuple = (1, 2)) -> bool:
    """
    Handle Turnstile verification

    Args:
        tab: Browser tab object
        max_retries: Maximum number of retries
        retry_interval: Retry interval range (min, max)

    Returns:
        bool: Whether verification was successful

    Raises:
        TurnstileError: Exception during verification process
    """
    logging.info(get_translation("detecting_turnstile"))
    save_screenshot(tab, "start")

    retry_count = 0

    try:
        while retry_count < max_retries:
            retry_count += 1
            logging.debug(get_translation("retry_verification", count=retry_count))

            try:
                element = None
                try:
                    element = (
                        tab.ele(".main-content")  # 找到 .main-content 元素
                        .ele("tag:div")        # 找到第一个子 div
                        .ele("tag:div")        # 找到第二个子 div
                        .ele("tag:div")        # 找到第三个子 div
                    )
                except Exception as e:
                    pass
                if element:
                    # Locate verification frame element
                    challenge_check = (
                        element
                        .shadow_root.ele("tag:iframe")
                        .ele("tag:body")
                        .sr("tag:input")
                    )
                else:
                    # Locate verification frame element
                    challenge_check = (
                        tab.ele("@id=cf-turnstile", timeout=2)
                        .child()
                        .shadow_root.ele("tag:iframe")
                        .ele("tag:body")
                        .sr("tag:input")
                    )

                if challenge_check:
                    logging.info(get_translation("detected_turnstile"))
                    # Random delay before clicking verification
                    time.sleep(random.uniform(1, 3))
                    challenge_check.click()
                    time.sleep(2)

                    # Save screenshot after verification
                    save_screenshot(tab, "clicked")

                    # Check verification result
                    if check_verification_success(tab):
                        logging.info(get_translation("turnstile_verification_passed"))
                        save_screenshot(tab, "success")
                        return True

            except Exception as e:
                # exc_type, exc_value, exc_traceback = sys.exc_info()
                # traceback.print_tb(exc_traceback)
                logging.debug(f"Current attempt unsuccessful: {str(e)}")

            # Check if already verified
            if check_verification_success(tab):
                return True

            # Random delay before next attempt
            time.sleep(random.uniform(*retry_interval))

        # Exceeded maximum retries
        logging.error(get_translation("verification_failed_max_retries", max_retries=max_retries))
        logging.error(
            "Please visit the open source project for more information: https://github.com/wangffei/wf-cursor-auto-free.git"
        )
        save_screenshot(tab, "failed")
        return False

    except Exception as e:
        error_msg = get_translation("turnstile_exception", error=str(e))
        logging.error(error_msg)
        save_screenshot(tab, "error")
        raise TurnstileError(error_msg)


def get_cursor_session_token(tab, max_attempts=3, retry_interval=2):
    """
    Get Cursor session token with retry mechanism
    :param tab: Browser tab
    :param max_attempts: Maximum number of attempts
    :param retry_interval: Retry interval (seconds)
    :return: Session token or None
    """
    # logging.info(get_translation("getting_cookie"))
    # attempts = 0

    # while attempts < max_attempts:
    #     try:
    #         cookies = tab.cookies()
    #         for cookie in cookies:
    #             if cookie.get("name") == "WorkosCursorSessionToken":
    #                 return cookie["value"].split("%3A%3A")[1]

    #         attempts += 1
    #         if attempts < max_attempts:
    #             logging.warning(
    #                 get_translation("cookie_attempt_failed", attempts=attempts, retry_interval=retry_interval)
    #             )
    #             time.sleep(retry_interval)
    #         else:
    #             logging.error(
    #                 get_translation("cookie_max_attempts", max_attempts=max_attempts)
    #             )

    #     except Exception as e:
    #         logging.error(get_translation("cookie_failure", error=str(e)))
    #         attempts += 1
    #         if attempts < max_attempts:
    #             logging.info(get_translation("retry_in_seconds", seconds=retry_interval))
    #             time.sleep(retry_interval)


    params = generate_auth_params()
    url = "https://www.cursor.com/cn/loginDeepControl?challenge="+params["n"] +"&uuid="+params["r"]+"&mode=login"
    tab.get(url)

    attempts = 0

    while attempts < max_attempts:
        # 检查是否到达登录界面
        status = check_verification_success(tab, VerificationStatus.TOKEN_REFRESH)
        if status:
            break

        attempts += 1

        if attempts < max_attempts:
            time.sleep(retry_interval)

    time.sleep(2)

    # 使用精确的CSS选择器在Python中查找元素并点击
    tab.run_js("""
        try {
            const button = document.querySelectorAll(".min-h-screen")[1].querySelectorAll(".gap-4")[1].querySelectorAll("button")[1];
            if (button) {
                button.click();
                return true;
            } else {
                return false;
            }
        } catch (e) {
            console.error("选择器错误:", e);
            return false;
        }
    """)

    _,accessToken,refreshToken = poll_for_login_result(params["r"], params["s"])

    return accessToken,refreshToken


def update_cursor_auth(email=None, access_token=None, refresh_token=None):
    """
    Update Cursor authentication information
    """
    auth_manager = CursorAuthManager()
    return auth_manager.update_auth(email, access_token, refresh_token)

def generate_auth_params():
    # 1. 生成 code_verifier (t) - 32字节随机数
    t = os.urandom(32)  # 等效于 JS 的 crypto.getRandomValues(new Uint8Array(32))

    # 2. 生成 s: 对 t 进行 Base64 URL 安全编码
    def tb(data):
        # Base64 URL 安全编码（替换 +/ 为 -_，去除末尾的 =）
        return base64.urlsafe_b64encode(data).decode().rstrip('=')
    
    s = tb(t)  # 对应 JS 的 this.tb(t)

    # 3. 生成 n: 对 s 进行 SHA-256 哈希 + Base64 URL 编码
    def ub(s_str):
        # 等效于 JS 的 TextEncoder().encode(s) + SHA-256
        return hashlib.sha256(s_str.encode()).digest()
    
    hashed = ub(s)
    n = tb(hashed)  # 对应 JS 的 this.tb(new Uint8Array(hashed))

    # 4. 生成 r: UUID v4
    r = str(uuid.uuid4())  # 对应 JS 的 $t()

    return {
        "t": t.hex(),      # 原始字节转十六进制字符串（方便查看）
        "s": s,
        "n": n,
        "r": r
    }

def poll_for_login_result(uuid, challenge):
        """轮询获取登录结果"""
        poll_url = f"https://api2.cursor.sh/auth/poll?uuid={uuid}&verifier={challenge}"
        headers = {
            "Content-Type": "application/json"
        }
        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            print("Polling for login result...")
            try:
                response = requests.get(poll_url, headers=headers)

                if response.status_code == 404:
                    print("Login not completed yet.")
                elif response.status_code == 200:
                    data = response.json()

                    if "authId" in data and "accessToken" in data and "refreshToken" in data:
                        print("Login successful!")
                        print(f"Auth ID: {data['authId']}")
                        print(f"Access Token: {data['accessToken']}")
                        print(f"Refresh Token: {data['refreshToken']}")
                        return data['authId'],data['accessToken'],data['refreshToken']

            except Exception as e:
                print(f"Error during polling: {e}")

            attempt += 1
            time.sleep(2)  # 每 2 秒轮询一次

        if attempt >= max_attempts:
            print("Polling timed out.")

        return None, None, None

def sign_up_account(browser, tab):
    logging.info(get_translation("start_account_registration"))
    logging.info(get_translation("visiting_registration_page", url=sign_up_url))
    tab.get(sign_up_url)

    # 首次注册需要验证的
    if not tab.ele(VerificationStatus.SIGN_UP.value):
        handle_turnstile(tab)

    try:
        if tab.ele("@name=first_name"):
            logging.info(get_translation("filling_personal_info"))
            tab.actions.click("@name=first_name").input(first_name)
            logging.info(get_translation("input_first_name", name=first_name))
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@name=last_name").input(last_name)
            logging.info(get_translation("input_last_name", name=last_name))
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@name=email").input(account)
            logging.info(get_translation("input_email", email=account))
            time.sleep(random.uniform(1, 3))

            logging.info(get_translation("submitting_personal_info"))
            tab.actions.click("@type=submit")

    except Exception as e:
        logging.error(get_translation("registration_page_access_failed", error=str(e)))
        return False

    handle_turnstile(tab)

    try:
        if tab.ele("@name=password"):
            logging.info(get_translation("setting_password"))
            tab.ele("@name=password").input(password)
            time.sleep(random.uniform(1, 3))

            logging.info(get_translation("submitting_password"))
            tab.ele("@type=submit").click()
            logging.info(get_translation("password_setup_complete"))

    except Exception as e:
        logging.error(get_translation("password_setup_failed", error=str(e)))
        return False

    if tab.ele("This email is not available."):
        logging.error(get_translation("registration_failed_email_used"))
        return False

    handle_turnstile(tab)

    while True:
        try:
            if tab.ele("Account Settings"):
                logging.info(get_translation("registration_success"))
                break
            if tab.ele("@data-index=0"):
                logging.info(get_translation("getting_email_verification"))
                code = email_handler.get_verification_code()
                if not code:
                    logging.error(get_translation("verification_code_failure"))
                    return False

                logging.info(get_translation("verification_code_success", code=code))
                logging.info(get_translation("inputting_verification_code"))
                i = 0
                for digit in code:
                    tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(random.uniform(0.1, 0.3))
                    i += 1
                logging.info(get_translation("verification_code_input_complete"))
                break
        except Exception as e:
            logging.error(get_translation("verification_code_process_error", error=str(e)))

    handle_turnstile(tab)
    wait_time = random.randint(3, 6)
    for i in range(wait_time):
        logging.info(get_translation("waiting_system_processing", seconds=wait_time-i))
        time.sleep(1)

    logging.info(get_translation("getting_account_info"))
    tab.get(settings_url)
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
            logging.info(get_translation("account_usage_limit", limit=total_usage))
            logging.info(
                "Please visit the open source project for more information: https://github.com/wangffei/wf-cursor-auto-free.git"
            )
    except Exception as e:
        logging.error(get_translation("account_usage_info_failure", error=str(e)))

    logging.info(get_translation("registration_complete"))
    account_info = get_translation("cursor_account_info", email=account, password=password)
    logging.info(account_info)
    time.sleep(5)
    return True


class EmailGenerator:
    """邮箱生成器类"""
    
    def __init__(
        self,
        password="".join(
            random.choices(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",
                k=12,
            )
        ),
    ):
        """
        初始化邮箱生成器
        
        Args:
            password: 可选的默认密码
        """
        configInstance = Config()
        configInstance.print_config()
        self.domain = configInstance.get_domain()
        self.names = self.load_names()
        self.default_password = password
        self.default_first_name = self.generate_random_name()
        self.default_last_name = self.generate_random_name()

    def load_names(self) -> List[str]:
        """
        加载随机名称数据集
        
        Returns:
            List[str]: 名称列表
        """
        try:
            with open("names-dataset.txt", "r") as file:
                return file.read().split()
        except FileNotFoundError:
            logging.warning(get_translation("names_file_not_found"))
            # 如果找不到文件，使用默认名称集
            return ["John", "Jane", "Alex", "Emma", "Michael", "Olivia", "William", "Sophia", 
                    "James", "Isabella", "Robert", "Mia", "David", "Charlotte", "Joseph", "Amelia"]

    def generate_random_name(self) -> str:
        """
        生成随机用户名
        
        Returns:
            str: 随机名称
        """
        return random.choice(self.names)

    def generate_email(self, length=4) -> str:
        """
        生成随机邮箱地址
    
    Args:
            length: 时间戳位数
            
        Returns:
            str: 生成的邮箱地址
        """
        length = random.randint(0, length)  # 生成0到length之间的随机整数
        timestamp = str(int(time.time()))[-length:]  # 使用时间戳的最后length位
        return f"{self.default_first_name}{timestamp}@{self.domain}"
        
    def get_account_info(self) -> Dict[str, str]:
        """
        获取完整的账号信息
    
    Returns:
            Dict[str, str]: 账号信息字典
        """
        return {
            "email": self.generate_email(),
            "password": self.default_password,
            "first_name": self.default_first_name,
            "last_name": self.default_last_name,
        }


def main():
    """主函数入口"""
    print_logo()
    
    # 添加语言选择
    print("\n")
    # language.select_language_prompt()
    
    cursor_pro = CursorProKeepAlive()
    
    try:
        logging.info(get_translation("initializing_program"))

        # 提示用户选择操作模式
        print(get_translation("select_operation_mode"))
        print(get_translation("reset_machine_code_only"))
        print(get_translation("complete_registration"))
        print(get_translation("only_sign_up"))
        print(get_translation("disable_auto_update"))
        print(get_translation("select_saved_account"))

        while True:
            try:
                choice = int(input(get_translation("enter_option")).strip())
                if choice in [1, 2, 3, 4, 5]:
                    break
                else:
                    print(get_translation("invalid_option"))
            except ValueError:
                print(get_translation("enter_valid_number"))

        # 根据用户选择执行不同的操作
        if choice == 1:  # 仅重置机器码
            cursor_pro.option_reset_machine_id()
        elif choice == 2:  # 完整注册
            cursor_pro.option_complete_registration()
        elif choice == 3:  # 仅注册
            cursor_pro.option_sign_up_only()
        elif choice == 4:  # 禁用自动更新
            cursor_pro.option_disable_auto_update()
        elif choice == 5:  # 选择已保存的账号
            cursor_pro.option_apply_saved_account()
                
    except Exception as e:
        logging.error(get_translation("program_error", error=str(e)))
    finally:
        cursor_pro.cleanup()
        input(get_translation("program_exit_message"))


# 添加API接口函数，直接放在main()函数前面

def api_reset_machine_id():
    """API: 仅重置机器码"""
    cursor_pro = CursorProKeepAlive()
    return cursor_pro.option_reset_machine_id()
    
def api_complete_registration():
    """API: 完整注册流程"""
    cursor_pro = CursorProKeepAlive()
    return cursor_pro.option_complete_registration()
    
def api_sign_up_only():
    """API: 仅注册账号"""
    cursor_pro = CursorProKeepAlive()
    return cursor_pro.option_sign_up_only()
    
def api_disable_auto_update():
    """API: 禁用自动更新"""
    cursor_pro = CursorProKeepAlive()
    return cursor_pro.option_disable_auto_update()
    
def api_apply_saved_account(account_file_path=None):
    """
    API: 应用已保存的账号
    
    Args:
        account_file_path: 账号文件路径，如果为None则显示选择界面
        
    Returns:
        bool: 操作是否成功
    """
    cursor_pro = CursorProKeepAlive()
    if account_file_path:
        return cursor_pro.apply_account_from_file(account_file_path)
    else:
        return cursor_pro.option_apply_saved_account()
    
def api_get_account_info():
    """
    API: 生成账号信息但不进行注册
    
    Returns:
        Dict[str, str]: 包含账号信息的字典
    """
    email_generator = EmailGenerator()
    return email_generator.get_account_info()
    
def api_save_account_info(email, password, access_token="", refresh_token=""):
    """
    API: 保存账号信息到文件
    
    Args:
        email: 邮箱地址
        password: 密码
        access_token: 访问令牌
        refresh_token: 刷新令牌
        
    Returns:
        bool: 操作是否成功
    """
    cursor_pro = CursorProKeepAlive()
    return cursor_pro.save_account_info(email, password, access_token, refresh_token)
    
def api_update_cursor_auth(email, access_token, refresh_token):
    """
    API: 更新Cursor身份验证信息
    
    Args:
        email: 邮箱地址
        access_token: 访问令牌
        refresh_token: 刷新令牌
        
    Returns:
        bool: 操作是否成功
    """
    cursor_pro = CursorProKeepAlive()
    return cursor_pro.update_cursor_auth(email, access_token, refresh_token)

def api_start_cursor():
    """API: 启动Cursor"""
    cursor_pro = CursorProKeepAlive()
    cursor_pro.start_cursor()
    
# 现在其他Python程序可以直接导入并调用这些函数
# 例如: from cursor_pro_keep_alive import api_reset_machine_id

if __name__ == "__main__":
    main()
