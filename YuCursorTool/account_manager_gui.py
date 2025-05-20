#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
from accounts_manager import AccountsManager

class AccountManagerGUI:
    """Cursor帳號管理系統的GUI界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Cursor 帳號管理系統")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # 初始化帳號管理器
        self.account_manager = AccountsManager()
        
        # 創建界面
        self.create_ui()
        
        # 加載帳號數據
        self.refresh_account_list()
    
    def create_ui(self):
        """創建GUI界面"""
        # 主佈局 - 分為左右兩部分
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側 - 帳號列表
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=2)
        
        # 右側 - 操作面板
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        # 左側 - 帳號列表區域
        list_frame = ttk.LabelFrame(left_frame, text="帳號列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 帳號列表樹形視圖
        columns = ("email", "password", "created_at", "status")
        self.account_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # 設置列標題
        self.account_tree.heading("email", text="郵箱")
        self.account_tree.heading("password", text="密碼")
        self.account_tree.heading("created_at", text="創建時間")
        self.account_tree.heading("status", text="狀態")
        
        # 設置列寬度
        self.account_tree.column("email", width=150)
        self.account_tree.column("password", width=120)
        self.account_tree.column("created_at", width=120)
        self.account_tree.column("status", width=80)
        
        # 添加滾動條
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.account_tree.yview)
        self.account_tree.configure(yscroll=scrollbar.set)
        
        # 佈局樹形視圖和滾動條
        self.account_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 綁定選擇事件
        self.account_tree.bind("<<TreeviewSelect>>", self.on_account_select)
        
        # 左側底部 - 刷新按鈕
        refresh_btn = ttk.Button(left_frame, text="刷新帳號列表", command=self.refresh_account_list)
        refresh_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # 右側 - 帳號詳情
        details_frame = ttk.LabelFrame(right_frame, text="帳號詳情")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 郵箱輸入
        ttk.Label(details_frame, text="郵箱:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(details_frame, textvariable=self.email_var, width=30)
        self.email_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 密碼輸入
        ttk.Label(details_frame, text="密碼:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(details_frame, textvariable=self.password_var, width=30)
        self.password_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 狀態輸入
        ttk.Label(details_frame, text="狀態:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.status_var = tk.StringVar()
        self.status_entry = ttk.Entry(details_frame, textvariable=self.status_var, width=30)
        self.status_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 按鈕區域
        btn_frame = ttk.Frame(details_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        # 添加/更新按鈕
        save_btn = ttk.Button(btn_frame, text="添加/更新帳號", command=self.save_account)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # 刪除按鈕
        delete_btn = ttk.Button(btn_frame, text="刪除帳號", command=self.delete_account)
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        # 清空按鈕
        clear_btn = ttk.Button(btn_frame, text="清空表單", command=self.clear_form)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 進階詳情區域
        advanced_frame = ttk.LabelFrame(right_frame, text="進階詳情")
        advanced_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 使用文本區域顯示完整帳號詳情
        self.details_text = scrolledtext.ScrolledText(advanced_frame, wrap=tk.WORD, height=10)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 底部狀態欄
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10)
        
        self.status_var = tk.StringVar()
        self.status_var.set("就緒")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W)
        status_label.pack(side=tk.LEFT, fill=tk.X)
        
        # 顯示總帳號數
        self.count_var = tk.StringVar()
        count_label = ttk.Label(status_frame, textvariable=self.count_var, anchor=tk.E)
        count_label.pack(side=tk.RIGHT)
    
    def refresh_account_list(self):
        """刷新帳號列表"""
        # 清空現有資料
        for item in self.account_tree.get_children():
            self.account_tree.delete(item)
        
        # 獲取所有帳號
        accounts = self.account_manager.get_accounts()
        
        # 更新計數
        self.count_var.set(f"總計 {len(accounts)} 個帳號")
        
        # 填充樹形視圖
        for account in accounts:
            email = account.get('email', '')
            password = account.get('password', '')
            created_at = account.get('created_at', '')
            status = account.get('account_status', '')
            
            self.account_tree.insert('', tk.END, values=(email, password, created_at, status))
        
        self.status_var.set("帳號列表已刷新")
    
    def on_account_select(self, event):
        """當選擇帳號列表中的項目時"""
        selected_items = self.account_tree.selection()
        if not selected_items:
            return
        
        # 獲取選定項的值
        item = selected_items[0]
        email = self.account_tree.item(item, 'values')[0]
        
        # 獲取完整帳號資訊
        account = self.account_manager.get_account(email)
        if not account:
            return
        
        # 填充表單
        self.email_var.set(account.get('email', ''))
        self.password_var.set(account.get('password', ''))
        self.status_var.set(account.get('account_status', ''))
        
        # 顯示完整詳情
        details = self.format_account_details(account)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, details)
    
    def format_account_details(self, account):
        """格式化帳號詳情"""
        details = f"郵箱: {account.get('email', '')}\n"
        details += f"密碼: {account.get('password', '')}\n"
        details += f"創建時間: {account.get('created_at', '')}\n"
        details += f"更新時間: {account.get('updated_at', '')}\n"
        
        if 'account_status' in account:
            details += f"帳號狀態: {account['account_status']}\n"
        
        if 'user' in account:
            details += f"用戶ID: {account['user']}\n"
        
        if 'membership' in account and isinstance(account['membership'], dict):
            details += "\n會員資訊:\n"
            for key, value in account['membership'].items():
                details += f"  {key}: {value}\n"
        
        if 'usage' in account and isinstance(account['usage'], dict):
            details += "\n使用情況:\n"
            for key, value in account['usage'].items():
                details += f"  {key}: {value}\n"
        
        return details
    
    def save_account(self):
        """保存帳號資訊"""
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()
        status = self.status_var.get().strip()
        
        if not email or not password:
            messagebox.showerror("錯誤", "郵箱和密碼不能為空！")
            return
        
        # 添加或更新帳號
        kwargs = {
            'account_status': status if status else None
        }
        
        if self.account_manager.add_account(email, password, **kwargs):
            messagebox.showinfo("成功", f"帳號 {email} 已成功保存！")
            self.refresh_account_list()
            self.clear_form()
        else:
            messagebox.showerror("錯誤", f"保存帳號 {email} 失敗！")
    
    def delete_account(self):
        """刪除帳號"""
        email = self.email_var.get().strip()
        
        if not email:
            messagebox.showerror("錯誤", "請選擇要刪除的帳號！")
            return
        
        if messagebox.askyesno("確認刪除", f"確定要刪除帳號 {email} 嗎？"):
            if self.account_manager.delete_account(email):
                messagebox.showinfo("成功", f"帳號 {email} 已成功刪除！")
                self.refresh_account_list()
                self.clear_form()
            else:
                messagebox.showerror("錯誤", f"刪除帳號 {email} 失敗！")
    
    def clear_form(self):
        """清空表單"""
        self.email_var.set("")
        self.password_var.set("")
        self.status_var.set("")
        self.details_text.delete(1.0, tk.END)

def main():
    root = tk.Tk()
    app = AccountManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 