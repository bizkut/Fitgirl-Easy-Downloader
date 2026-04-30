import argparse
import os
from datetime import datetime

import pyperclip
import requests
from colorama import Fore, Style
from tqdm import tqdm

from ff_utils import HEADERS, get_game_links_and_name, resolve_fuckingfast_download


class Console:
    def __init__(self) -> None:
        self.colors = {
            "green": Fore.GREEN, "red": Fore.RED, "yellow": Fore.YELLOW,
            "blue": Fore.BLUE, "magenta": Fore.MAGENTA, "cyan": Fore.CYAN,
            "white": Fore.WHITE, "black": Fore.BLACK, "reset": Style.RESET_ALL,
            "lightblack": Fore.LIGHTBLACK_EX, "lightred": Fore.LIGHTRED_EX,
            "lightgreen": Fore.LIGHTGREEN_EX, "lightyellow": Fore.LIGHTYELLOW_EX,
            "lightblue": Fore.LIGHTBLUE_EX, "lightmagenta": Fore.LIGHTMAGENTA_EX,
            "lightcyan": Fore.LIGHTCYAN_EX, "lightwhite": Fore.LIGHTWHITE_EX,
        }

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def timestamp(self):
        return datetime.now().strftime("%H:%M:%S")

    def _log(self, level, color, message, obj):
        print(
            f"{self.colors['lightblack']}{self.timestamp()} >> "
            f"{self.colors[color]}{level:4} {self.colors['lightblack']}- "
            f"{self.colors['white']}{message} : {self.colors[color]}{obj}"
            f"{self.colors['white']} {self.colors['reset']}"
        )

    def success(self, message, obj):
        self._log("SUCC", "lightgreen", message, obj)

    def error(self, message, obj):
        self._log("ERRR", "lightred", message, obj)

    def done(self, message, obj):
        self._log("DONE", "lightmagenta", message, obj)

    def warning(self, message, obj):
        self._log("WARN", "lightyellow", message, obj)

    def info(self, message, obj):
        self._log("INFO", "lightblue", message, obj)


log = Console()


def get_game_info(url):
    try:
        links, game_name, _ = get_game_links_and_name(url)
        return links, game_name
    except requests.exceptions.RequestException as e:
        log.error("HTTP request failed", f"{url} ({e})")
        return [], "Downloaded_Game"


def download_file(download_url, output_path):
    response = requests.get(download_url, stream=True, headers=HEADERS, timeout=60)
    if response.status_code == 200:
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192

        with open(output_path, 'wb') as f, tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            leave=False,
        ) as bar:
            for data in response.iter_content(block_size):
                f.write(data)
                bar.set_description(
                    f"{log.colors['lightblack']}{log.timestamp()} >> "
                    f"{log.colors['lightblue']}INFO {log.colors['lightblack']}- "
                    f"{log.colors['white']}Downloading -> {os.path.basename(output_path)[:40]}... "
                    f"{log.colors['reset']}"
                )
                bar.update(len(data))
        log.success("Downloaded", os.path.basename(output_path))
        return True

    log.error("Failed To Download", response.status_code)
    return False


def process_and_download(links, game_url, game_name, custom_folder=None):
    if custom_folder:
        downloads_folder = os.path.join(custom_folder, game_name)
    else:
        downloads_folder = os.path.join("downloads", game_name)

    os.makedirs(downloads_folder, exist_ok=True)
    log.info("Download folder", downloads_folder)

    for idx, link in enumerate(links):
        log.info("Processing", f"{link[:40]}...")
        try:
            plan_item = resolve_fuckingfast_download(
                link,
                download_dir=downloads_folder,
                idx=idx,
                fetch_size=False
            )
            if plan_item:
                download_file(plan_item['download_url'], plan_item['output_path'])
            else:
                log.error("Download URL not found in page", link)
        except Exception as e:
            log.error("Error processing link", str(e))


def main():
    parser = argparse.ArgumentParser(description="FitGirl Easy Downloader - Combined Link Fetching and Downloading")
    parser.add_argument("url", nargs="?", help="FitGirl Game URL")
    parser.add_argument("-d", "--download", action="store_true", help="Download the links automatically after fetching")
    parser.add_argument("-o", "--output", help="Custom download destination folder")
    args = parser.parse_args()

    log.clear()
    url = args.url

    if not url and os.path.exists('input.txt'):
        with open('input.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
            if lines:
                url = lines[0]
                log.info("Using URL from input.txt", url)

    if not url:
        url = input(
            f"{log.colors['lightblack']}{log.timestamp()} >> "
            f"{log.colors['lightcyan']}INPUT   {log.colors['lightblack']}- "
            f"{log.colors['white']}Enter Fitgirl Game Link: {log.colors['reset']}"
        )

    if not url:
        log.error("No URL provided", "Exiting...")
        return

    ff_links, game_name = get_game_info(url)

    if not ff_links:
        log.error("No fuckingfast.co links found", "Exiting...")
        return

    output = "\n".join(ff_links)
    print(f"\n{log.colors['lightmagenta']}Matching URLs:{log.colors['reset']}")
    print(output)
    pyperclip.copy(output)
    log.success("All Links Copied To Clipboard", len(ff_links))
    log.info("Game Name", game_name)

    if args.download:
        log.info("Auto-download switch enabled", "Starting downloads...")
        process_and_download(ff_links, url, game_name, custom_folder=args.output)
    else:
        log.warning("Auto-download not enabled", "Use -d or --download to download automatically")


if __name__ == "__main__":
    main()
