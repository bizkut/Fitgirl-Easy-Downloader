#!/bin/bash
echo "Building FitGirl Easy Downloader (GUI) for macOS..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Run PyInstaller
pyinstaller --noconfirm --onedir --windowed --name "FitGirl Downloader" gui.py

echo ""
echo "Build complete! Your macOS App is located in the 'dist' folder."
