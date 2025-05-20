import sqlite3
import os
import sys
import json


class CursorAuthManager:
    """Cursor认证信息管理器"""

    def __init__(self):
        # 判断操作系统
        if sys.platform == "win32":  # Windows
            appdata = os.getenv("APPDATA")
            if appdata is None:
                raise EnvironmentError("APPDATA 环境变量未设置")
            self.db_path = os.path.join(
                appdata, "Cursor", "User", "globalStorage", "state.vscdb"
            )
        elif sys.platform == "darwin": # macOS
            self.db_path = os.path.abspath(os.path.expanduser(
                "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
            ))
        elif sys.platform == "linux" : # Linux 和其他类Unix系统
            self.db_path = os.path.abspath(os.path.expanduser(
                "~/.config/Cursor/User/globalStorage/state.vscdb"
            ))
        else:
            raise NotImplementedError(f"不支持的操作系统: {sys.platform}")
            
    def get_current_auth(self):
        """
        獲取當前的認證信息
        :return: dict 包含郵箱地址、訪問令牌、刷新令牌、用戶ID和cookie
        """
        conn = None
        auth_info = {
            'email': None,
            'access_token': None,
            'refresh_token': None,
            'user_id': None,
            'cookie': None
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 獲取郵箱地址
            cursor.execute("SELECT value FROM itemTable WHERE key = ?", ("cursorAuth/cachedEmail",))
            result = cursor.fetchone()
            if result:
                auth_info['email'] = result[0]
                
            # 獲取訪問令牌
            cursor.execute("SELECT value FROM itemTable WHERE key = ?", ("cursorAuth/accessToken",))
            result = cursor.fetchone()
            if result:
                auth_info['access_token'] = result[0]
                
            # 獲取刷新令牌
            cursor.execute("SELECT value FROM itemTable WHERE key = ?", ("cursorAuth/refreshToken",))
            result = cursor.fetchone()
            if result:
                auth_info['refresh_token'] = result[0]
                
            # 獲取用戶ID
            cursor.execute("SELECT value FROM itemTable WHERE key = ?", ("cursorAuth/userId",))
            result = cursor.fetchone()
            if result:
                auth_info['user_id'] = result[0]
                
            # 獲取認證cookie
            cursor.execute("SELECT value FROM itemTable WHERE key = ?", ("cursorAuth/sessionCookie",))
            result = cursor.fetchone()
            if result:
                auth_info['cookie'] = result[0]
                
            return auth_info
            
        except sqlite3.Error as e:
            print("數據庫錯誤:", str(e))
            return auth_info
        except Exception as e:
            print("發生錯誤:", str(e))
            return auth_info
        finally:
            if conn:
                conn.close()

    def update_auth(self, email=None, access_token=None, refresh_token=None, user_id=None, cookie=None):
        """
        更新Cursor的认证信息
        :param email: 新的邮箱地址
        :param access_token: 新的访问令牌
        :param refresh_token: 新的刷新令牌
        :param user_id: 新的用户ID
        :param cookie: 新的认证cookie
        :return: bool 是否成功更新
        """
        updates = []
        # 登录状态
        updates.append(("cursorAuth/cachedSignUpType", "Auth_0"))

        if email is not None:
            updates.append(("cursorAuth/cachedEmail", email))
        if access_token is not None:
            updates.append(("cursorAuth/accessToken", access_token))
        if refresh_token is not None:
            updates.append(("cursorAuth/refreshToken", refresh_token))
        if user_id is not None:
            updates.append(("cursorAuth/userId", user_id))
        if cookie is not None:
            updates.append(("cursorAuth/sessionCookie", cookie))

        if not updates:
            print("没有提供任何要更新的值")
            return False

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for key, value in updates:

                # 如果没有更新任何行,说明key不存在,执行插入
                # 检查 accessToken 是否存在
                check_query = f"SELECT COUNT(*) FROM itemTable WHERE key = ?"
                cursor.execute(check_query, (key,))
                if cursor.fetchone()[0] == 0:
                    insert_query = "INSERT INTO itemTable (key, value) VALUES (?, ?)"
                    cursor.execute(insert_query, (key, value))
                else:
                    update_query = "UPDATE itemTable SET value = ? WHERE key = ?"
                    cursor.execute(update_query, (value, key))

                if cursor.rowcount > 0:
                    print(f"成功更新 {key.split('/')[-1]}")
                else:
                    print(f"未找到 {key.split('/')[-1]} 或值未变化")

            conn.commit()
            return True

        except sqlite3.Error as e:
            print("数据库错误:", str(e))
            return False
        except Exception as e:
            print("发生错误:", str(e))
            return False
        finally:
            if conn:
                conn.close()
                
    def update_from_saved_account(self, account_info):
        """
        從已保存的帳號資訊更新認證信息
        :param account_info: dict 包含郵箱地址、訪問令牌、刷新令牌、用戶ID和cookie
        :return: bool 是否成功更新
        """
        email = account_info.get('email')
        access_token = account_info.get('access_token')
        refresh_token = account_info.get('refresh_token')
        user_id = account_info.get('user')  # 注意這裡用的是 'user' 而非 'user_id'
        cookie = account_info.get('cookie')
        
        # 從cookie中提取 WorkosCursorSessionToken (如果存在)
        session_token = None
        if cookie and 'WorkosCursorSessionToken=' in cookie:
            try:
                # 提取 WorkosCursorSessionToken 值
                start = cookie.find('WorkosCursorSessionToken=') + len('WorkosCursorSessionToken=')
                end = cookie.find(';', start) if ';' in cookie[start:] else len(cookie)
                session_token = cookie[start:end]
                
                # 如果提取失敗，使用完整cookie
                if not session_token:
                    session_token = cookie
            except:
                session_token = cookie
                
        # 使用 session_token 如果有，否則使用原始 cookie
        return self.update_auth(email, access_token, refresh_token, user_id, session_token or cookie)
