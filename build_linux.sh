#!/bin/bash
echo "Building FitGirl Easy Downloader (GUI) for Linux..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Run PyInstaller
pyinstaller --noconfirm --onedir --windowed --add-data "img:img" --icon "img/icon.jpg" --name "FitGirl Downloader" gui.py

echo ""
echo "Build complete! Your Linux executable is located in the 'dist' folder."
echo "You can run it from dist/FitGirl Downloader/FitGirl Downloader"
