from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 收集 flet 模組的所有數據文件
datas = collect_data_files('flet')

# 收集 flet 的所有子模組
hiddenimports = collect_submodules('flet')
hiddenimports.extend([
    'httpx',
    'anyio',
    'sniffio',
    'repath',
    'oauthlib'
]) 