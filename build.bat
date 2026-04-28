@echo off
echo Building FitGirl Easy Downloader (GUI) for Windows...

:: Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

:: Run PyInstaller
pyinstaller --noconfirm --onedir --windowed --name "FitGirl Downloader" gui.py

echo.
echo Build complete! Your Windows executable is located in the 'dist\FitGirl Downloader' folder.
pause
