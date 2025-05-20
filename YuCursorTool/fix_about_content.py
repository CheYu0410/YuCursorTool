import os

# 創建備份
file_path = 'gui_app.py'
backup_path = 'gui_app.py.about_bak'

# 如果還沒有備份，則創建備份
if not os.path.exists(backup_path):
    with open(file_path, 'r', encoding='utf-8') as source:
        with open(backup_path, 'w', encoding='utf-8') as target:
            target.write(source.read())
    print(f"備份創建於 {backup_path}")

# 讀取文件內容
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要插入關於內容的位置
home_content_end_index = -1

for i, line in enumerate(lines):
    if "], alignment=ft.MainAxisAlignment.START, expand=True, scroll=ft.ScrollMode.AUTO)" in line and "home_content" in lines[i-5:i]:
        home_content_end_index = i
        break

if home_content_end_index == -1:
    print("無法找到插入位置！")
    exit(1)

# 生成關於頁面的內容
about_content_code = """
    # 創建關於頁面內容
    about_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("關於 YuCursor", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Divider(),
                ft.Container(height=10),
                ft.Row([
                    ft.Image(src="/YuCursor.png", width=50, height=50, fit=ft.ImageFit.CONTAIN),
                    ft.Column([
                        ft.Text("YuCursor", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("版本 1.0.1", size=16),
                        ft.Text("發布日期：2025年5月20日", size=16)
                    ])
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=20),
                ft.Text("應用介紹", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("YuCursor 是一款專為 Cursor 編輯器設計的帳號管理和自動化工具，幫助用戶輕鬆創建和管理多個 Cursor 帳號。", size=16),
                ft.Container(height=10),
                ft.Text("開發者資訊", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("本應用由 YuTeam 開發團隊開發", size=16),
                ft.Container(height=20),
                ft.Text("注意事項", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_600),
                ft.Text("• 本工具永久免費，請勿從任何渠道購買", size=16),
                ft.Text("• 請勿將本工具用於非法用途", size=16),
                ft.Text("• 使用本工具所產生的任何後果由使用者自行承擔", size=16),
                ft.Container(height=30),
                ft.Text("© 2025 YuTeam. 保留所有權利。", size=14, italic=True, text_align=ft.TextAlign.CENTER)
            ]),
            padding=20,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            margin=20
        )
    ], alignment=ft.MainAxisAlignment.START, expand=True, scroll=ft.ScrollMode.AUTO)
"""

# 插入關於頁面的定義
new_lines = lines[:home_content_end_index+1] + [about_content_code] + lines[home_content_end_index+1:]

# 寫入更新後的內容
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("成功添加 about_content 定義！") 