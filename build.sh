#!/bin/bash
echo "Building FitGirl Easy Downloader (GUI) for macOS..."

echo "Installing runtime dependencies..."
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install requirements."
    exit 1
fi

python3 -c "import libtorrent as lt; print('libtorrent', lt.__version__)"
if [ $? -ne 0 ]; then
    echo "libtorrent is required for internal torrent downloads."
    exit 1
fi

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller not found. Installing..."
    python3 -m pip install pyinstaller
fi

# Run PyInstaller
pyinstaller --noconfirm --clean --onedir --windowed --additional-hooks-dir hooks --add-data "img:img" --hidden-import libtorrent --collect-all libtorrent --icon "img/icon.jpg" --name "FitGirl Downloader" gui.py

echo ""
echo "Build complete! Your macOS App is located in the 'dist' folder."
