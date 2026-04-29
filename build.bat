@echo off
echo Building FitGirl Easy Downloader (GUI) for Windows...

:: Install all runtime dependencies, including the internal torrent engine.
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install requirements.
    exit /b 1
)

python -c "import libtorrent as lt; print('libtorrent', lt.__version__)"
if %errorlevel% neq 0 (
    echo libtorrent is required for internal torrent downloads.
    exit /b 1
)

:: Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

:: Run PyInstaller
pyinstaller --noconfirm --clean --onedir --windowed --additional-hooks-dir hooks --add-data "img;img" --hidden-import libtorrent --collect-all libtorrent --icon "img\icon.jpg" --name "FitGirl Downloader" gui.py

echo.
echo Build complete! Your Windows executable is located in the 'dist\FitGirl Downloader' folder.
pause
