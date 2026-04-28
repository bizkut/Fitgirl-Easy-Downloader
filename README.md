# Fitgirl-Easy-Downloader

This Tool Helps To Download Multiple Files Easily From fitgirl-repacks.site Through fuckingfast.co

## Prerequisites

Ensure you have the following installed before running the script :

`Python 3.8+`

```bash
pip install -r requirements.txt
```

## Usage

### Option 1: All-in-One Command (Recommended)
You can fetch links and start downloading immediately using `main.py`:
- **Fetch links only**:
  ```bash
  python main.py <game_url>
  ```
- **Fetch and Download automatically**:
  ```bash
  python main.py <game_url> -d
  ```
- **Custom Download Folder**:
  ```bash
  python main.py <game_url> -d -o "D:\Games"
  ```

### Option 2: Manual (Old Method)
1. **Get Direct Download Links**: Run `get_links.py`, enter the Fitgirl game page URL, and all FuckingFast links will be copied to your clipboard automatically.
   ```bash
   python get_links.py
   ```
2. **Prepare Input Links**: Paste the copied links into `input.txt`, one per line.
3. **Run the Script**:
   ```bash
   python main.py
   ```

## Windows Executable
To create a standalone `.exe` for Windows:
1. Install requirements: `pip install -r requirements.txt`
2. Run: `pyinstaller --onefile --name "FitGirlDownloader" main.py`
3. Find your executable in the `dist/` folder.

## Features
- Extracts links even from modern list-based layouts.
- Automatically uses the real game name for folder creation.
- Sanitizes folder names for Windows compatibility.
- Auto-copies links to clipboard.

## Disclaimer

This tool is created for educational purposes and ethical use only. Any misuse of this tool for malicious purposes is not condoned. The developers of this tool are not responsible for any illegal or unethical activities carried out using this tool.

[![Star History Chart](https://api.star-history.com/svg?repos=JoyNath1337/Fitgirl-Easy-Downloader&type=Date)](https://star-history.t9t.io/#JoyNath1337/Fitgirl-Easy-Downloader&Date)
