#!/usr/bin/env python
# -*- coding: utf-8 -*-

from accounts_manager import AccountsManager

def main():
    """展示帳號管理功能的簡單示例"""
    # 初始化帳號管理器
    account_manager = AccountsManager()
    
    # 顯示現有帳號
    print("\n=== 顯示現有帳號 ===")
    accounts_display = account_manager.display_accounts()
    print(accounts_display)
    
    # 模擬添加或更新操作
    while True:
        print("\n=== 帳號管理選項 ===")
        print("1. 添加/更新帳號")
        print("2. 刪除帳號")
        print("3. 顯示所有帳號")
        print("4. 退出")
        
        choice = input("請選擇操作 (1-4): ")
        
        if choice == '1':
            # 添加/更新帳號
            email = input("請輸入郵箱: ")
            password = input("請輸入密碼: ")
            
            success = account_manager.add_account(email, password)
            if success:
                print(f"帳號 {email} 已成功添加/更新！")
            else:
                print(f"帳號 {email} 添加/更新失敗！")
                
        elif choice == '2':
            # 刪除帳號
            email = input("請輸入要刪除的帳號郵箱: ")
            
            if account_manager.get_account(email):
                confirm = input(f"確定要刪除帳號 {email}？(y/n): ")
                if confirm.lower() == 'y':
                    success = account_manager.delete_account(email)
                    if success:
                        print(f"帳號 {email} 已成功刪除！")
                    else:
                        print(f"帳號 {email} 刪除失敗！")
            else:
                print(f"找不到帳號 {email}！")
                
        elif choice == '3':
            # 顯示所有帳號
            accounts_display = account_manager.display_accounts()
            print(accounts_display)
            
        elif choice == '4':
            # 退出
            print("感謝使用帳號管理功能，再見！")
            break
            
        else:
            print("無效選擇，請重新輸入！")

if __name__ == "__main__":
    main() 