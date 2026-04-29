# Fitgirl-Easy-Downloader

This Tool Helps To Download Multiple Files Easily From fitgirl-repacks.site Through fuckingfast.co — now with a **built-in torrent client** for concurrent downloads!

## Prerequisites

Ensure you have the following installed before running the script :

`Python 3.9+`

```bash
pip install -r requirements.txt
```

## Usage

### Option 1: GUI Mode (Recommended)
Enjoy a fully interactive cross-platform Desktop Application with queue management, game info fetching, **built-in torrent client**, and seamless resume support!
```bash
python gui.py
```
Or simply run the standalone executable after building (see below).

#### Built-in Torrent Client
The GUI includes a built-in torrent client powered by [libtorrent](https://libtorrent.org/). When you fetch a game page, click **⚡ Torrent Download** to download via torrent directly inside the app — no external torrent client needed.
- **Concurrent downloads**: Multiple torrents download simultaneously.
- **Live progress**: Speed, peers, ETA, and seed ratio displayed in the queue.
- **Pause/Resume/Cancel**: Full control over each torrent.
- **Auto-seeding**: Seeds up to a configurable ratio (default 1.0x), then auto-stops.
- **Internal-only torrent downloads**: `libtorrent==2.0.11` is installed and bundled for Windows, macOS, and Linux builds. Windows builds also include `libtorrent-windows-dll` for libtorrent's OpenSSL DLLs. If the torrent engine is missing, the app reports the dependency error instead of opening an external torrent client.

### Option 2: CLI All-in-One Command
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

### Option 3: Manual (Old Method)
1. **Get Direct Download Links**: Run `get_links.py`, enter the Fitgirl game page URL, and all FuckingFast links will be copied to your clipboard automatically.
   ```bash
   python get_links.py
   ```
2. **Prepare Input Links**: Paste the copied links into `input.txt`, one per line.
3. **Run the Script**:
   ```bash
   python main.py
   ```

## Standalone Executables (GUI)
Pre-built binaries are available for every release — no Python required.

### Download (Recommended)
Head to the [Releases](../../releases/latest) page and download the archive for your OS:
- **Windows**: `fitgirl-downloader-windows.zip` → extract and run `FitGirl Downloader.exe`
- **macOS**: `fitgirl-downloader-macos.zip` → extract and open `FitGirl Downloader.app`
- **Linux**: `fitgirl-downloader-linux.tar.gz` → extract and run `FitGirl Downloader`, or grab `fitgirl-downloader.AppImage` → `chmod +x` and run

> **macOS note**: The app is ad-hoc signed (no Apple Developer certificate). On first launch, right-click → **Open** to bypass the Gatekeeper warning. Alternatively, run:
> ```bash
> xattr -dr com.apple.quarantine "FitGirl Downloader.app"
> ```

### Build from Source
1. Install requirements: `pip install -r requirements.txt`
2. Run the build script for your OS:
   - **Windows**: Run `build.bat`
   - **macOS**: Run `./build.sh`
   - **Linux**: Run `./build_linux.sh`
3. Find your standalone Desktop Application in the `dist/` folder!

### Windows libtorrent DLL errors
If a Windows build reports a libtorrent DLL load error, rebuild from a clean environment with the current `build.bat`. The Windows requirements include `libtorrent-windows-dll`, which supplies `libcrypto-1_1-x64.dll` and `libssl-1_1-x64.dll`, and the PyInstaller hook bundles those DLLs with the app. Windows releases use PyInstaller `onedir` with `--contents-directory "."`, so the support files sit beside the exe instead of in an `_internal` folder.

## Features
- **Cross-platform GUI Application** with live queue management.
- **Built-in Torrent Client**: Download via magnet links directly in the app — concurrent multi-torrent downloads with live speed, peers, ETA, and seed ratio.
- **Smart Resume**: Automatically skips downloaded files and resumes partially downloaded files via HTTP Range.
- Fetches full Game Information, Thumbnail, and Descriptions.
- Extracts links even from modern list-based layouts.
- Automatically uses the real game name for folder creation.
- Sanitizes folder names for OS compatibility.
- Auto-copies links to clipboard (CLI mode).

## Disclaimer

This tool is created for educational purposes and ethical use only. Any misuse of this tool for malicious purposes is not condoned. The developers of this tool are not responsible for any illegal or unethical activities carried out using this tool.

[![Star History Chart](https://api.star-history.com/svg?repos=JoyNath1337/Fitgirl-Easy-Downloader&type=Date)](https://star-history.t9t.io/#JoyNath1337/Fitgirl-Easy-Downloader&Date)
