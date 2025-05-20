import os

# 創建備份
file_path = 'gui_app.py'
backup_path = 'gui_app.py.bak'

# 備份原始文件
if not os.path.exists(backup_path):
    with open(file_path, 'r', encoding='utf-8') as source:
        with open(backup_path, 'w', encoding='utf-8') as target:
            target.write(source.read())
    print(f"Backup created at {backup_path}")

# 讀取文件內容
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到 about_content 結束和 tabs 定義的區域
about_content_end_index = -1
tabs_start_index = -1
tabs_end_index = -1
page_add_index = -1

for i, line in enumerate(lines):
    if "], alignment=ft.MainAxisAlignment.START, expand=True, scroll=ft.ScrollMode.AUTO)" in line and about_content_end_index == -1:
        about_content_end_index = i
    
    if "# 添加標籤頁控件" in line:
        tabs_start_index = i
    
    if "tabs = ft.Tabs(" in line:
        tabs_def_index = i

    if "page.add(tabs)" in line:
        page_add_index = i
        break

# 簡單檢查是否找到所有需要的索引
if -1 in [about_content_end_index, tabs_start_index, tabs_def_index, page_add_index]:
    print("Error: Could not find all required indexes in the file")
    print(f"about_content_end_index: {about_content_end_index}")
    print(f"tabs_start_index: {tabs_start_index}")
    print(f"tabs_def_index: {tabs_def_index}")
    print(f"page_add_index: {page_add_index}")
    exit(1)

# 構建新的文件內容
new_content = []

# 1. 添加 about_content_end_index 之前的部分
new_content.extend(lines[:about_content_end_index+1])

# 2. 添加更新日誌內容
new_content.extend([
    "\n",
    "    # 創建更新日誌內容\n",
    "    changelog_content = ft.Column([\n",
    "        ft.Container(\n",
    "            content=ft.Column([\n",
    "                ft.Text(\"更新日誌\", size=30, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),\n",
    "                ft.Divider(),\n",
    "                ft.Container(height=10),\n",
    "                ft.Text(\"版本 1.0.1 (2025年5月20日)\", size=20, weight=ft.FontWeight.BOLD),\n",
    "                ft.Text(\"  - 更新了「關於」頁面中的版本號和日期。\", size=16),\n",
    "                ft.Text(\"  - 修復了應用程式關閉時可能發生的事件迴圈錯誤。\", size=16),\n",
    "                ft.Container(height=20),\n",
    "                ft.Text(\"版本 1.0.0 (2025年5月19日)\", size=20, weight=ft.FontWeight.BOLD),\n",
    "                ft.Text(\"  - 初始版本發布。\", size=16),\n",
    "            ]),\n",
    "            padding=20,\n",
    "            border=ft.border.all(1, ft.Colors.GREY_300),\n",
    "            border_radius=10,\n",
    "            margin=20\n",
    "        )\n",
    "    ], alignment=ft.MainAxisAlignment.START, expand=True, scroll=ft.ScrollMode.AUTO)\n",
    "\n"
])

# 3. 添加 tabs 定義部分
new_content.append("    # 添加標籤頁控件\n")
new_content.append("    tabs = ft.Tabs(\n")
new_content.append("        selected_index=0,  # 預設顯示主頁\n")
new_content.append("        animation_duration=300,\n")
new_content.append("        tabs=[\n")
new_content.append("            ft.Tab(\n")
new_content.append("                text=\"主頁\",\n")
new_content.append("                icon=ft.Icons.HOME,\n")
new_content.append("                content=ft.Container(\n")
new_content.append("                    content=home_content,\n")
new_content.append("                    padding=10,\n")
new_content.append("                    expand=True\n")
new_content.append("                )\n")
new_content.append("            ),\n")
new_content.append("            ft.Tab(\n")
new_content.append("                text=\"功能操作\",\n")
new_content.append("                icon=ft.Icons.BUILD_CIRCLE,\n")
new_content.append("                content=ft.Container(\n")
new_content.append("                    content=original_content,\n")
new_content.append("                    padding=10,\n")
new_content.append("                    expand=True\n")
new_content.append("                )\n")
new_content.append("            ),\n")
new_content.append("            ft.Tab(\n")
new_content.append("                text=\"帳號管理\",\n")
new_content.append("                icon=ft.Icons.ACCOUNT_CIRCLE,\n")
new_content.append("                content=ft.Container(\n")
new_content.append("                    content=accounts_view,\n")
new_content.append("                    padding=5,\n")
new_content.append("                    expand=True\n")
new_content.append("                )\n")
new_content.append("            ),\n")
new_content.append("            ft.Tab(\n")
new_content.append("                text=\"關於\",\n")
new_content.append("                icon=ft.Icons.INFO,\n")
new_content.append("                content=ft.Container(\n")
new_content.append("                    content=about_content,\n")
new_content.append("                    padding=10,\n")
new_content.append("                    expand=True\n")
new_content.append("                )\n")
new_content.append("            ),\n")
new_content.append("            ft.Tab(\n")
new_content.append("                text=\"更新日誌\",\n")
new_content.append("                icon=ft.Icons.HISTORY,\n")
new_content.append("                content=ft.Container(\n")
new_content.append("                    content=changelog_content,\n")
new_content.append("                    padding=10,\n")
new_content.append("                    expand=True\n")
new_content.append("                )\n")
new_content.append("            )\n")
new_content.append("        ],\n")
new_content.append("        expand=True,\n")
new_content.append("        on_change=on_tab_change\n")
new_content.append("    )\n")
new_content.append("\n")
new_content.append("    # 初始顯示 (確保在所有標籤頁都添加完畢後)\n")
new_content.append("    page.add(tabs)\n")

# 4. 添加剩餘部分
new_content.extend(lines[page_add_index+1:])

# 寫入修改後的內容
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_content)

print('File updated successfully') 