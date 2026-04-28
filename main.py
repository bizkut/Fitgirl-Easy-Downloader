import os
import re
import requests
import pyperclip
import argparse
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime
from colorama import Fore, Style

class Console:
    def __init__(self) -> None:
        self.colors = {
            "green": Fore.GREEN, "red": Fore.RED, "yellow": Fore.YELLOW, 
            "blue": Fore.BLUE, "magenta": Fore.MAGENTA, "cyan": Fore.CYAN, 
            "white": Fore.WHITE, "black": Fore.BLACK, "reset": Style.RESET_ALL, 
            "lightblack": Fore.LIGHTBLACK_EX, "lightred": Fore.LIGHTRED_EX, 
            "lightgreen": Fore.LIGHTGREEN_EX, "lightyellow": Fore.LIGHTYELLOW_EX, 
            "lightblue": Fore.LIGHTBLUE_EX, "lightmagenta": Fore.LIGHTMAGENTA_EX, 
            "lightcyan": Fore.LIGHTCYAN_EX, "lightwhite": Fore.LIGHTWHITE_EX
        }

    def clear(self):
        os.system("cls" if os.name == "nt" else "clear")

    def timestamp(self):
        return datetime.now().strftime("%H:%M:%S")

    def _log(self, level, color, message, obj):
        print(f"{self.colors['lightblack']}{self.timestamp()} » {self.colors[color]}{level:4} {self.colors['lightblack']}• {self.colors['white']}{message} : {self.colors[color]}{obj}{self.colors['white']} {self.colors['reset']}")

    def success(self, message, obj): self._log("SUCC", "lightgreen", message, obj)
    def error(self, message, obj): self._log("ERRR", "lightred", message, obj)
    def done(self, message, obj): self._log("DONE", "lightmagenta", message, obj)
    def warning(self, message, obj): self._log("WARN", "lightyellow", message, obj)
    def info(self, message, obj): self._log("INFO", "lightblue", message, obj)

log = Console()

HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.5',
    'referer': 'https://fitgirl-repacks.site/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}
def get_fuckingfast_links(url):
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.error("HTTP request failed", f"{url} ({e})")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    links = [
        a["href"]
        for dlinks_div in soup.find_all("div", class_="dlinks")
        for a in dlinks_div.find_all("a", href=True)
        if a["href"].startswith("https://fuckingfast.co/")
    ]
    return links

def download_file(download_url, output_path):
    response = requests.get(download_url, stream=True, headers=HEADERS)
    if response.status_code == 200:
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192

        with open(output_path, 'wb') as f, tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            leave=False
        ) as bar:
            for data in response.iter_content(block_size):
                f.write(data)
                bar.set_description(f"{log.colors['lightblack']}{log.timestamp()} » {log.colors['lightblue']}INFO {log.colors['lightblack']}• {log.colors['white']}Downloading -> {os.path.basename(output_path)[:40]}... {log.colors['reset']}")
                bar.update(len(data))
        log.success("Downloaded", os.path.basename(output_path))
        return True
    else:
        log.error("Failed To Download", response.status_code)
        return False

def process_and_download(links, game_url):
    game_name = urlparse(game_url).path.strip('/').split('--')[0] or "Downloaded_Game"
    downloads_folder = os.path.join("downloads", game_name)
    os.makedirs(downloads_folder, exist_ok=True)
    log.info("Download folder", downloads_folder)

    for link in links:
        log.info("Processing", f"{link[:40]}...")
        try:
            response = requests.get(link, headers=HEADERS)
            if response.status_code != 200:
                log.error("Failed to fetch link page", response.status_code)
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            meta_title = soup.find('meta', attrs={'name': 'title'})
            file_name = meta_title['content'] if meta_title else "file"
            
            script_tags = soup.find_all('script')
            download_url = None
            for script in script_tags:
                if 'function download' in script.text:
                    match = re.search(r'window\.open\(["\'](https?://[^\s"\'\)]+)', script.text)
                    if match:
                        download_url = match.group(1)
                        break
            
            if download_url:
                output_path = os.path.join(downloads_folder, file_name)
                download_file(download_url, output_path)
            else:
                log.error("Download URL not found in page", link)
        except Exception as e:
            log.error("Error processing link", str(e))

def main():
    parser = argparse.ArgumentParser(description="FitGirl Easy Downloader - Combined Link Fetching and Downloading")
    parser.add_argument("url", nargs="?", help="FitGirl Game URL")
    parser.add_argument("-d", "--download", action="store_true", help="Download the links automatically after fetching")
    args = parser.parse_args()

    log.clear()
    url = args.url
    
    # Check if input.txt exists and has content if no URL is provided
    if not url and os.path.exists('input.txt'):
        with open('input.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
            if lines:
                url = lines[0]
                log.info("Using URL from input.txt", url)

    if not url:
        url = input(f"{log.colors['lightblack']}{log.timestamp()} » {log.colors['lightcyan']}INPUT   {log.colors['lightblack']}• {log.colors['white']}Enter Fitgirl Game Link: {log.colors['reset']}")

    if not url:
        log.error("No URL provided", "Exiting...")
        return
    ff_links = get_fuckingfast_links(url)

    if not ff_links:
        log.error("No fuckingfast.co links found", "Exiting...")
        return

    output = "\n".join(ff_links)
    print(f"\n🔗 {log.colors['lightmagenta']}Matching URLs:{log.colors['reset']}")
    print(output)
    pyperclip.copy(output)
    log.success("All Links Copied To Clipboard", len(ff_links))

    if args.download:
        log.info("Auto-download switch enabled", "Starting downloads...")
        process_and_download(ff_links, url)
    else:
        log.warning("Auto-download not enabled", "Use -d or --download to download automatically")

if __name__ == "__main__":
    main()
