import os
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.5',
    'referer': 'https://fitgirl-repacks.site/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}


def sanitize_filename(name, fallback="file"):
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", name or "").strip()
    return cleaned or fallback


def sanitize_game_name(name, fallback="Downloaded_Game"):
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name or "").strip()
    return cleaned or fallback


def extract_fuckingfast_links(soup):
    return [
        a["href"]
        for a in soup.find_all("a", href=True)
        if a["href"].startswith("https://fuckingfast.co/")
    ]


def extract_game_name(soup, url=None, fallback="Downloaded_Game"):
    entry_title = soup.find("h1", class_="entry-title")
    if entry_title:
        raw_name = entry_title.get_text()
        for separator in ("\u00e2\u20ac\u201c", "\u2013", "\u2014", "-"):
            raw_name = raw_name.split(separator)[0]
        return sanitize_game_name(raw_name, fallback=fallback)

    if url:
        raw_name = urlparse(url).path.strip('/').split('--')[0]
        return sanitize_game_name(raw_name, fallback=fallback)

    return fallback


def fetch_game_page(url, timeout=30):
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_game_links_and_name(url, timeout=30):
    soup = fetch_game_page(url, timeout=timeout)
    return extract_fuckingfast_links(soup), extract_game_name(soup, url=url), soup


def extract_direct_download_url(soup):
    for script in soup.find_all('script'):
        if 'function download' in script.text:
            match = re.search(r'window\.open\(["\'](https?://[^\s"\'\)]+)', script.text)
            if match:
                return match.group(1)
    return None


def resolve_fuckingfast_download(link, download_dir=None, idx=0, timeout=30, fetch_size=True):
    response = requests.get(link, headers=HEADERS, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    meta_title = soup.find('meta', attrs={'name': 'title'})
    file_name = sanitize_filename(
        meta_title['content'] if meta_title else f"part_{idx + 1}.rar",
        fallback=f"part_{idx + 1}.rar"
    )

    download_url = extract_direct_download_url(soup)
    if not download_url:
        return None

    output_path = os.path.join(download_dir, file_name) if download_dir else file_name
    file_mode = 'wb'
    existing_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
    remote_size = 0

    if fetch_size:
        head_response = requests.head(download_url, headers=HEADERS, allow_redirects=True, timeout=15)
        remote_size = int(head_response.headers.get('content-length', 0))
        if remote_size > 0 and existing_size < remote_size:
            file_mode = 'ab'

    return {
        'download_url': download_url,
        'output_path': output_path,
        'file_name': file_name,
        'file_mode': file_mode,
        'existing_size': existing_size,
        'remote_size': remote_size,
        'part_idx': idx + 1,
    }
