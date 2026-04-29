from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

binaries = []
datas = []

for package in ("libtorrent", "libtorrent_windows_dll"):
    try:
        binaries += collect_dynamic_libs(package)
        datas += collect_data_files(package, includes=["*.dll"])
    except Exception:
        pass
