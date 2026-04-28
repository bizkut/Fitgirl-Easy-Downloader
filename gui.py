import os
import sys
import subprocess
import json
import threading
import queue
import re
import time
import requests
import webbrowser
import shutil
from io import BytesIO
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

# Built-in torrent client (graceful fallback if libtorrent not installed)
try:
    from torrent_client import TorrentManager
    HAS_LIBTORRENT = True
except ImportError:
    HAS_LIBTORRENT = False

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

CONFIG_FILE = "config.json"
HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.5',
    'referer': 'https://fitgirl-repacks.site/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get_download_dir(self):
        return self.config.get("download_dir", "")

    def set_download_dir(self, directory):
        self.config["download_dir"] = directory
        self.save_config()

    def get_torrent_config(self):
        """Get torrent-specific configuration with defaults."""
        defaults = {
            "port_range": [6881, 6891],
            "max_download_speed": 0,
            "max_upload_speed": 0,
            "seed_after_download": True,
            "seed_ratio_limit": 1.0,
            "encryption": True
        }
        torrent_cfg = self.config.get("torrent", {})
        # Merge defaults with saved config
        for key, val in defaults.items():
            if key not in torrent_cfg:
                torrent_cfg[key] = val
        return torrent_cfg

    def save_queue(self, queue_items, torrent_queue_items):
        """Save the current queue to config."""
        serialized_queue = []
        for item in queue_items.values():
            # Copy to avoid modifying the live item
            item_copy = item.copy()
            # Remove tree_id as it's not stable
            item_copy.pop('tree_id', None)
            serialized_queue.append(item_copy)
            
        serialized_torrent_queue = []
        for item in torrent_queue_items.values():
            item_copy = item.copy()
            item_copy.pop('torrent_id', None) # libtorrent handles are not persistent
            serialized_torrent_queue.append(item_copy)
            
        self.config["queue"] = serialized_queue
        self.config["torrent_queue"] = serialized_torrent_queue
        self.save_config()

    def get_queue(self):
        """Load the saved queue from config."""
        return self.config.get("queue", []), self.config.get("torrent_queue", [])

class FitGirlDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FitGirl Easy Downloader GUI")
        self.root.geometry("900x650")
        self.root.minsize(800, 600)
        
        self.config_manager = ConfigManager()
        self.check_first_run()
        
        self.queue_items = {}
        self.current_download_id = None
        self.abort_flag = False
        self.is_downloading = False
        
        # Torrent client (concurrent downloads)
        self.torrent_manager = None
        self.torrent_queue_items = {}  # tree_id -> {torrent_id, name, ...}
        if HAS_LIBTORRENT:
            try:
                torrent_cfg = self.config_manager.get_torrent_config()
                self.torrent_manager = TorrentManager(config=torrent_cfg)
            except Exception as e:
                print(f"[WARN] Failed to initialize torrent client: {e}")
        
        self.setup_ui()
        self.start_download_worker()
        self.check_clipboard()
        
        # Load saved queue
        self.root.after(100, self.load_saved_queue)
        
        # Start torrent status polling
        if self.torrent_manager:
            self._poll_torrent_status()
        
        # Clean up on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def check_clipboard(self):
        try:
            clipboard_text = self.root.clipboard_get()
            if clipboard_text and 'fitgirl-repacks.site/' in clipboard_text:
                # Basic check if it looks like a URL
                if clipboard_text.startswith('http'):
                    self.url_var.set(clipboard_text.strip())
        except tk.TclError:
            pass # Clipboard might be empty or unsupported type

    def check_first_run(self):
        if not self.config_manager.get_download_dir():
            messagebox.showinfo("Welcome", "Please select a default download location.")
            self.choose_download_dir()

    def choose_download_dir(self):
        dir_path = filedialog.askdirectory(title="Select Default Download Directory")
        if dir_path:
            self.config_manager.set_download_dir(dir_path)
        else:
            if not self.config_manager.get_download_dir():
                # If they cancelled and no dir is set, set a default
                default_dir = os.path.join(os.getcwd(), "downloads")
                os.makedirs(default_dir, exist_ok=True)
                self.config_manager.set_download_dir(default_dir)

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Settings Frame
        settings_frame = ttk.Frame(main_frame)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        self.lbl_download_dir = ttk.Label(settings_frame, text=f"Download Dir: {self.config_manager.get_download_dir()}")
        self.lbl_download_dir.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btn_open_dir = ttk.Button(settings_frame, text="Open Folder", command=self.open_dir)
        btn_open_dir.pack(side=tk.RIGHT, padx=(5, 0))
        btn_change_dir = ttk.Button(settings_frame, text="Change", command=self.change_dir)
        btn_change_dir.pack(side=tk.RIGHT)

        # URL Input Frame
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT, padx=(0, 5))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.btn_fetch = ttk.Button(url_frame, text="Fetch Info", command=self.fetch_info)
        self.btn_fetch.pack(side=tk.LEFT)
        
        self.btn_open_page = ttk.Button(url_frame, text="Open Game Page", command=self.open_game_page, state=tk.DISABLED)
        self.btn_open_page.pack(side=tk.LEFT, padx=(5, 0))

        # Info Frame
        self.info_frame = ttk.LabelFrame(main_frame, text="Game Info", padding="10")
        self.info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.thumbnail_lbl = ttk.Label(self.info_frame)
        self.thumbnail_lbl.grid(row=0, column=0, rowspan=6, padx=(0, 10))
        
        self.lbl_game_name = ttk.Label(self.info_frame, text="Name: -", font=('Helvetica', 10, 'bold'))
        self.lbl_game_name.grid(row=0, column=1, sticky=tk.W)
        self.lbl_genres = ttk.Label(self.info_frame, text="Genres: -")
        self.lbl_genres.grid(row=1, column=1, sticky=tk.W)
        self.lbl_company = ttk.Label(self.info_frame, text="Company: -")
        self.lbl_company.grid(row=2, column=1, sticky=tk.W)
        self.lbl_languages = ttk.Label(self.info_frame, text="Languages: -")
        self.lbl_languages.grid(row=3, column=1, sticky=tk.W)
        self.lbl_size = ttk.Label(self.info_frame, text="Size: -")
        self.lbl_size.grid(row=4, column=1, sticky=tk.W)
        
        btn_actions_frame = ttk.Frame(self.info_frame)
        btn_actions_frame.grid(row=5, column=1, sticky=tk.W, pady=(5, 0))
        
        self.btn_queue = ttk.Button(btn_actions_frame, text="Add to Queue", command=self.add_to_queue, state=tk.DISABLED)
        self.btn_queue.pack(side=tk.LEFT, padx=(0, 5))
        
        torrent_label = "⚡ Torrent Download" if HAS_LIBTORRENT else "Download via Torrent"
        self.btn_torrent = ttk.Button(btn_actions_frame, text=torrent_label, command=self.download_torrent, state=tk.DISABLED)
        self.btn_torrent.pack(side=tk.LEFT)

        self.txt_desc = tk.Text(self.info_frame, wrap=tk.WORD, height=4, width=40, font=('Helvetica', 9))
        self.txt_desc.grid(row=6, column=0, columnspan=3, pady=(10, 0), sticky=tk.EW)
        self.txt_desc.insert(tk.END, "Description: -")
        self.txt_desc.config(state=tk.DISABLED)
        self.info_frame.columnconfigure(1, weight=1)

        self.fitgirl_lbl = ttk.Label(self.info_frame, cursor="hand2")
        self.fitgirl_lbl.grid(row=0, column=2, rowspan=5, padx=(10, 0))
        self.fitgirl_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://fitgirl-repacks.site/donations/"))
        
        threading.Thread(target=self._load_app_icon, daemon=True).start()
        threading.Thread(target=self._load_fitgirl_image, daemon=True).start()

        # Progress Frame (packed before queue_frame so it stays anchored at the bottom)
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.lbl_current_download = ttk.Label(progress_frame, text="Currently Downloading: None")
        self.lbl_current_download.pack(anchor=tk.W)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        self.lbl_progress_text = ttk.Label(progress_frame, text="0%")
        self.lbl_progress_text.pack(anchor=tk.E)

        # Queue Frame
        queue_frame = ttk.LabelFrame(main_frame, text="Download Queue", padding="10")
        queue_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 10))
        
        columns = ("name", "status")
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, show="headings")
        self.queue_tree.heading("name", text="Game Name")
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.column("name", width=400)
        self.queue_tree.column("status", width=150)
        
        # Action Frame (packed BOTTOM so it doesn't get hidden)
        action_frame = ttk.Frame(queue_frame)
        action_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        self.btn_stop = ttk.Button(action_frame, text="Stop", command=self.stop_item, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 5))
        self.btn_resume = ttk.Button(action_frame, text="Resume", command=self.resume_item, state=tk.DISABLED)
        self.btn_resume.pack(side=tk.LEFT, padx=(0, 5))
        self.btn_remove = ttk.Button(action_frame, text="Remove", command=self.remove_item, state=tk.DISABLED)
        self.btn_remove.pack(side=tk.LEFT)
        
        # Now pack the treeview to take up remaining space
        self.queue_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.queue_tree.bind('<<TreeviewSelect>>', self.on_tree_select)

    def save_queue(self):
        """Helper to save the current queue state."""
        self.config_manager.save_queue(self.queue_items, self.torrent_queue_items)

    def load_saved_queue(self):
        """Load and restore the queue from config."""
        queue_data, torrent_queue_data = self.config_manager.get_queue()
        
        for item in queue_data:
            # If status was 'Downloading', reset to 'Queued'
            if item.get('status') == 'Downloading':
                item['status'] = 'Queued'
            
            item_id = self.queue_tree.insert("", tk.END, values=(item['name'], item.get('status', 'Queued')))
            item['tree_id'] = item_id
            self.queue_items[item_id] = item
            
        for item in torrent_queue_data:
            display_name = item.get('display_name', f"🧲 {item['name']}")
            item_id = self.queue_tree.insert("", tk.END, values=(display_name, "Queued"))
            
            if self.torrent_manager and 'magnet_link' in item:
                base_dir = self.config_manager.get_download_dir()
                try:
                    torrent_id = self.torrent_manager.add_magnet(item['magnet_link'], base_dir, name=item['name'])
                    item['torrent_id'] = torrent_id
                    
                    # If it was paused, pause it again
                    if item.get('is_paused'):
                        self.torrent_manager.pause(torrent_id)
                except Exception as e:
                    print(f"Error restarting torrent {item['name']}: {e}")
            
            item['display_status'] = 'Queued'
            self.torrent_queue_items[item_id] = item
        
        self.on_tree_select(None)

        self.fetched_data = None

    def on_tree_select(self, event):
        selected = self.queue_tree.selection()
        if selected:
            item_id = selected[0]
            
            # Check if it's a torrent item
            if item_id in self.torrent_queue_items:
                torrent_info = self.torrent_queue_items[item_id]
                status = torrent_info.get('display_status', '')
                is_paused = torrent_info.get('is_paused', False)
                is_finished = torrent_info.get('is_finished', False)
                
                if is_paused:
                    self.btn_stop.config(state=tk.DISABLED)
                    self.btn_resume.config(state=tk.NORMAL)
                elif not is_finished:
                    self.btn_stop.config(state=tk.NORMAL)
                    self.btn_resume.config(state=tk.DISABLED)
                else:
                    self.btn_stop.config(state=tk.DISABLED)
                    self.btn_resume.config(state=tk.DISABLED)
                self.btn_remove.config(state=tk.NORMAL)
                return
            
            # Regular download item
            status = self.queue_items[item_id]['status']
            if status == 'Downloading':
                self.btn_stop.config(state=tk.NORMAL)
                self.btn_resume.config(state=tk.DISABLED)
            elif status == 'Stopped':
                self.btn_stop.config(state=tk.DISABLED)
                self.btn_resume.config(state=tk.NORMAL)
            else:
                self.btn_stop.config(state=tk.DISABLED)
                self.btn_resume.config(state=tk.DISABLED)
            
            if status != 'Completed':
                self.btn_remove.config(state=tk.NORMAL)
            else:
                self.btn_remove.config(state=tk.NORMAL)
        else:
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_resume.config(state=tk.DISABLED)
            self.btn_remove.config(state=tk.DISABLED)

    def stop_item(self):
        selected = self.queue_tree.selection()
        if selected:
            item_id = selected[0]
            
            # Torrent item
            if item_id in self.torrent_queue_items:
                torrent_info = self.torrent_queue_items[item_id]
                if self.torrent_manager:
                    self.torrent_manager.pause(torrent_info['torrent_id'])
                    torrent_info['is_paused'] = True
                self.save_queue()
                self.on_tree_select(None)
                return
            
            # Regular download item
            if item_id in self.queue_items and self.queue_items[item_id]['status'] == 'Downloading':
                self.abort_flag = True
                self.queue_items[item_id]['status'] = 'Stopped'
                self.queue_tree.set(item_id, 'status', 'Stopped')
                self.save_queue()
                self.on_tree_select(None)

    def resume_item(self):
        selected = self.queue_tree.selection()
        if selected:
            item_id = selected[0]
            
            # Torrent item
            if item_id in self.torrent_queue_items:
                torrent_info = self.torrent_queue_items[item_id]
                if self.torrent_manager:
                    self.torrent_manager.resume(torrent_info['torrent_id'])
                    torrent_info['is_paused'] = False
                self.save_queue()
                self.on_tree_select(None)
                return
            
            # Regular download item
            if item_id in self.queue_items and self.queue_items[item_id]['status'] == 'Stopped':
                self.queue_items[item_id]['status'] = 'Queued'
                self.queue_tree.set(item_id, 'status', 'Queued')
                self.save_queue()
                self.on_tree_select(None)

    def remove_item(self):
        selected = self.queue_tree.selection()
        if selected:
            item_id = selected[0]
            
            # Torrent item
            if item_id in self.torrent_queue_items:
                torrent_info = self.torrent_queue_items[item_id]
                if self.torrent_manager:
                    self.torrent_manager.remove(torrent_info['torrent_id'], delete_files=False)
                del self.torrent_queue_items[item_id]
                self.queue_tree.delete(item_id)
                self.save_queue()
                self.on_tree_select(None)
                return
            
            # Regular download item
            if item_id not in self.queue_items:
                return
            item = self.queue_items[item_id]
            
            if item['status'] == 'Downloading':
                self.abort_flag = True
            
            del self.queue_items[item_id]
            self.queue_tree.delete(item_id)
            self.save_queue()
            self.on_tree_select(None)

    def change_dir(self):
        self.choose_download_dir()
        self.lbl_download_dir.config(text=f"Download Dir: {self.config_manager.get_download_dir()}")

    def open_dir(self):
        path = self.config_manager.get_download_dir()
        if os.path.exists(path):
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])

    def fetch_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL")
            return
        
        self.btn_fetch.config(state=tk.DISABLED)
        self.btn_queue.config(state=tk.DISABLED)
        
        # Run fetch in thread to not freeze UI
        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        try:
            r = requests.get(url, headers=HEADERS)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Extract links
            links = [
                a["href"]
                for a in soup.find_all("a", href=True)
                if a["href"].startswith("https://fuckingfast.co/")
            ]
            
            if not links:
                self.root.after(0, lambda: messagebox.showerror("Error", "No fuckingfast.co links found on this page."))
                self.root.after(0, lambda: self.btn_fetch.config(state=tk.NORMAL))
                return

            # Extract info
            entry_title = soup.find("h1", class_="entry-title")
            game_name = entry_title.get_text().split("–")[0].split("-")[0].strip() if entry_title else "Unknown Game"
            game_name = re.sub(r'[\\/*?:"<>|]', "", game_name).strip()
            
            entry_content = soup.find('div', class_='entry-content')
            img_url = None
            genres = company = languages = orig_size = repack_size = "-"
            
            if entry_content:
                img = entry_content.find('img')
                if img:
                    img_url = img['src']
                
                full_text = entry_content.get_text('\n')
                
                m_genres = re.search(r'Genres/Tags:\s*([^\n]+)', full_text)
                if m_genres: genres = m_genres.group(1).strip().replace('\n', ' ')
                
                m_comp = re.search(r'(?:Company|Companies|Developer/Publisher):\s*([^\n]+)', full_text, re.IGNORECASE)
                if m_comp: company = m_comp.group(1).strip()
                
                m_lang = re.search(r'Languages:\s*([^\n]+)', full_text)
                if m_lang: languages = m_lang.group(1).strip()
                
                m_orig = re.search(r'Original Size:\s*([^\n]+)', full_text)
                if m_orig: orig_size = m_orig.group(1).strip()
                
                m_rep = re.search(r'Repack Size:\s*([^\n]+)', full_text)
                if m_rep: repack_size = m_rep.group(1).strip()
                
                description = "-"
                m_desc = re.search(r'Game Description\n+(.*?)(?=\n+Repack Features|\Z)', full_text, re.DOTALL)
                if m_desc:
                    description = m_desc.group(1).strip()

            # Extract magnet link
            magnet_link = None
            magnet_tag = soup.find('a', href=re.compile(r'^magnet:\?xt=urn:btih:'))
            if magnet_tag:
                magnet_link = magnet_tag['href']

            self.fetched_data = {
                "url": url,
                "name": game_name,
                "links": links,
                "magnet_link": magnet_link,
                "img_url": img_url,
                "genres": genres,
                "company": company,
                "languages": languages,
                "orig_size": orig_size,
                "repack_size": repack_size,
                "description": description
            }
            
            self.root.after(0, self._update_ui_with_fetch)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch information:\n{e}"))
            self.root.after(0, lambda: self.btn_fetch.config(state=tk.NORMAL))

    def _update_ui_with_fetch(self):
        data = self.fetched_data
        self.lbl_game_name.config(text=f"Name: {data['name']}")
        self.lbl_genres.config(text=f"Genres: {data['genres']}")
        self.lbl_company.config(text=f"Company: {data['company']}")
        self.lbl_languages.config(text=f"Languages: {data['languages']}")
        self.lbl_size.config(text=f"Size: {data['repack_size']} (Orig: {data['orig_size']})")
        
        self.txt_desc.config(state=tk.NORMAL)
        self.txt_desc.delete(1.0, tk.END)
        self.txt_desc.insert(tk.END, data['description'])
        self.txt_desc.config(state=tk.DISABLED)
        
        if data['img_url']:
            threading.Thread(target=self._load_image, args=(data['img_url'],), daemon=True).start()
        
        self.btn_fetch.config(state=tk.NORMAL)
        self.btn_open_page.config(state=tk.NORMAL)
        self.btn_queue.config(state=tk.NORMAL)
        if data.get('magnet_link'):
            self.btn_torrent.config(state=tk.NORMAL)
        else:
            self.btn_torrent.config(state=tk.DISABLED)

    def open_game_page(self):
        if self.fetched_data and 'url' in self.fetched_data:
            webbrowser.open(self.fetched_data['url'])

    def download_torrent(self):
        if not self.fetched_data or not self.fetched_data.get('magnet_link'):
            return
        
        magnet = self.fetched_data['magnet_link']
        game_name = self.fetched_data['name']
        
        # Use built-in torrent client if available
        if self.torrent_manager:
            base_dir = self.config_manager.get_download_dir()
            save_path = base_dir
            
            try:
                torrent_id = self.torrent_manager.add_magnet(magnet, save_path, name=game_name)
                
                # Add to queue treeview with torrent indicator
                display_name = f"🧲 {game_name}"
                item_id = self.queue_tree.insert("", tk.END, values=(display_name, "Starting..."))
                
                self.torrent_queue_items[item_id] = {
                    'torrent_id': torrent_id,
                    'name': game_name,
                    'display_name': display_name,
                    'display_status': 'Starting...',
                    'is_paused': False,
                    'is_finished': False,
                    'magnet_link': magnet,
                }
                self.save_queue()
                
                self.btn_torrent.config(state=tk.DISABLED)
                
            except Exception as e:
                messagebox.showerror("Torrent Error", f"Failed to start torrent:\n{e}")
        else:
            # Fallback: open in external torrent client
            if sys.platform == "win32":
                os.startfile(magnet)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", magnet])
            else:
                subprocess.Popen(["xdg-open", magnet])

    def _load_image(self, url):
        try:
            r = requests.get(url)
            img_data = r.content
            img = Image.open(BytesIO(img_data))
            img.thumbnail((150, 200)) # Resize to fit nicely
            photo = ImageTk.PhotoImage(img)
            self.root.after(0, lambda p=photo: self._set_image(p))
        except:
            pass

    def _set_image(self, photo):
        self.thumbnail_lbl.config(image=photo)
        self.thumbnail_lbl.image = photo # Keep reference

    def _load_app_icon(self):
        try:
            img_path = resource_path("img/icon.jpg")
            if os.path.exists(img_path):
                img = Image.open(img_path)
            else:
                r = requests.get("https://fitgirl-repacks.site/wp-content/uploads/2016/08/cropped-icon-32x32.jpg")
                img = Image.open(BytesIO(r.content))
            photo = ImageTk.PhotoImage(img)
            self.root.after(0, lambda p=photo: self.root.iconphoto(False, p))
        except:
            pass

    def _load_fitgirl_image(self):
        try:
            img_path = resource_path("img/support.jpg")
            if os.path.exists(img_path):
                img = Image.open(img_path)
            else:
                r = requests.get("https://fitgirl-repacks.site/wp-content/uploads/2024/05/support2.jpg")
                img = Image.open(BytesIO(r.content))
            img.thumbnail((150, 200)) # Match thumbnail size logic
            photo = ImageTk.PhotoImage(img)
            self.root.after(0, lambda p=photo: self._set_fitgirl_image(p))
        except:
            pass

    def _set_fitgirl_image(self, photo):
        self.fitgirl_lbl.config(image=photo)
        self.fitgirl_lbl.image = photo # Keep reference

    def add_to_queue(self):
        if self.fetched_data:
            item_id = self.queue_tree.insert("", tk.END, values=(self.fetched_data['name'], "Queued"))
            self.fetched_data['tree_id'] = item_id
            self.fetched_data['status'] = 'Queued'
            self.queue_items[item_id] = self.fetched_data
            self.save_queue()
            self.fetched_data = None
            self.btn_queue.config(state=tk.DISABLED)

    def start_download_worker(self):
        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self):
        while True:
            item_id = None
            for key, val in self.queue_items.items():
                if val['status'] == 'Queued':
                    item_id = key
                    break
            
            if not item_id:
                time.sleep(1)
                continue

            item = self.queue_items[item_id]
            self.current_download_id = item_id
            self.abort_flag = False
            self.is_downloading = True
            
            item['status'] = 'Downloading'
            self.root.after(0, lambda i=item_id: self.queue_tree.exists(i) and self.queue_tree.set(i, "status", "Downloading"))
            self.root.after(0, lambda i=item['name']: self.lbl_current_download.config(text=f"Currently Downloading: {i}"))
            self.root.after(0, lambda: self.on_tree_select(None))
            
            game_name = item['name']
            links = item['links']
            base_dir = self.config_manager.get_download_dir()
            download_dir = os.path.join(base_dir, game_name)
            os.makedirs(download_dir, exist_ok=True)
            
            total_links = len(links)
            for idx, link in enumerate(links):
                if self.abort_flag:
                    break
                    
                try:
                    self.root.after(0, lambda i=item_id, c=idx+1, t=total_links: self.queue_tree.exists(i) and self.queue_tree.set(i, "status", f"Downloading {c}/{t}"))
                    
                    response = requests.get(link, headers=HEADERS)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    meta_title = soup.find('meta', attrs={'name': 'title'})
                    file_name = meta_title['content'] if meta_title else f"part_{idx+1}.rar"
                    
                    script_tags = soup.find_all('script')
                    download_url = None
                    for script in script_tags:
                        if 'function download' in script.text:
                            match = re.search(r'window\.open\(["\'](https?://[^\s"\'\)]+)', script.text)
                            if match:
                                download_url = match.group(1)
                                break
                    
                    if download_url:
                        output_path = os.path.join(download_dir, file_name)
                        
                        file_mode = 'wb'
                        existing_size = 0
                        
                        head_response = requests.head(download_url, headers=HEADERS, allow_redirects=True)
                        remote_size = int(head_response.headers.get('content-length', 0))
                        
                        if os.path.exists(output_path):
                            existing_size = os.path.getsize(output_path)
                            if remote_size > 0 and existing_size == remote_size:
                                print(f"Skipping {file_name}, already completed.")
                                continue
                            elif remote_size > 0 and existing_size < remote_size:
                                file_mode = 'ab'
                        
                        self.root.after(0, lambda f=file_name: self.lbl_current_download.config(text=f"Downloading -> {f[:40]}..."))
                        self.root.after(0, lambda: self._update_progress(0, "0% | 0.00 B/0.00 B [00:00<00:00, 0.00 B/s]"))
                        
                        success = self._download_file(download_url, output_path, file_mode, existing_size, remote_size)
                        if not success: # abort flag was set
                            break
                            
                except Exception as e:
                    print(f"Error downloading {link}: {e}")
            
            if not self.abort_flag:
                item['status'] = 'Completed'
                self.root.after(0, lambda i=item_id: self.queue_tree.exists(i) and self.queue_tree.set(i, "status", "Completed"))
                self.save_queue()
            
            self.current_download_id = None
            self.is_downloading = False
            self.root.after(0, lambda: self.lbl_current_download.config(text="Currently Downloading: None"))
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.lbl_progress_text.config(text="0%"))
            self.root.after(0, lambda: self.on_tree_select(None))

    def _download_file(self, download_url, output_path, mode, existing_size, total_size):
        headers = HEADERS.copy()
        if mode == 'ab' and existing_size > 0:
            headers['Range'] = f'bytes={existing_size}-'
            
        response = requests.get(download_url, stream=True, headers=headers)
        if response.status_code in [200, 206]:
            if response.status_code == 200:
                mode = 'wb'
                downloaded = 0
            else:
                downloaded = existing_size
                
            if total_size == 0:
                total_size = int(response.headers.get('content-length', 0)) + downloaded
                
            block_size = 8192
            start_time = time.time()
            last_update_time = start_time
            
            def format_size(size):
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if size < 1024.0: return f"{size:.2f} {unit}"
                    size /= 1024.0
                return f"{size:.2f} PB"
                
            def format_time(secs):
                m, s = divmod(int(secs), 60)
                h, m = divmod(m, 60)
                if h > 0:
                    return f"{h:02d}:{m:02d}:{s:02d}"
                return f"{m:02d}:{s:02d}"
            
            with open(output_path, mode) as f:
                for data in response.iter_content(block_size):
                    if self.abort_flag:
                        return False
                        
                    f.write(data)
                    downloaded += len(data)
                    
                    current_time = time.time()
                    if current_time - last_update_time > 0.5 or downloaded == total_size:
                        last_update_time = current_time
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            elapsed_time = current_time - start_time
                            speed = (downloaded - existing_size if response.status_code == 206 else downloaded) / elapsed_time if elapsed_time > 0 else 0
                            eta = (total_size - downloaded) / speed if speed > 0 else 0
                            
                            progress_text = f"{progress:.0f}% | {format_size(downloaded)}/{format_size(total_size)} [{format_time(elapsed_time)}<{format_time(eta)}, {format_size(speed)}/s]"
                            self.root.after(0, self._update_progress, progress, progress_text)
            return True
        return False
                        
    def _update_progress(self, value, text):
        self.progress_var.set(value)
        self.lbl_progress_text.config(text=text)

    # ─── Torrent Status Polling ────────────────────────────────────────

    def _poll_torrent_status(self):
        """Poll all active torrents every 500ms and update the queue UI."""
        if not self.torrent_manager:
            return

        for tree_id, torrent_info in list(self.torrent_queue_items.items()):
            # Skip if tree item was already deleted
            if not self.queue_tree.exists(tree_id):
                continue

            status = self.torrent_manager.get_status(torrent_info['torrent_id'])
            if not status:
                continue

            # Update cached state
            torrent_info['is_paused'] = status['is_paused']
            torrent_info['is_finished'] = status['is_finished']

            # Update name once metadata arrives
            if status['has_metadata'] and status['name'] != torrent_info['name']:
                torrent_info['name'] = status['name']
                torrent_info['display_name'] = f"🧲 {status['name']}"
                self.queue_tree.set(tree_id, 'name', torrent_info['display_name'])

            # Build status string
            if status['is_paused'] and not status['is_seeding']:
                status_str = f"⏸ Paused — {status['progress']:.1f}%"
            elif status['is_seeding']:
                ratio = status['seed_ratio']
                up_speed = self._format_speed(status['upload_rate'])
                if status['is_paused']:
                    status_str = f"✅ Done — Seeded {ratio:.2f}x"
                else:
                    status_str = f"🌱 Seeding {ratio:.2f}x — ↑ {up_speed}"
            elif not status['has_metadata']:
                status_str = "🔍 Fetching metadata..."
            else:
                dl_speed = self._format_speed(status['download_rate'])
                progress = status['progress']
                peers = status['num_peers']
                eta_str = self._format_eta(status['eta'])
                status_str = f"↓ {dl_speed} — {progress:.1f}% — {peers} peers — ETA {eta_str}"

            torrent_info['display_status'] = status_str
            self.queue_tree.set(tree_id, 'status', status_str)

            # Update progress bar if this torrent is selected
            selected = self.queue_tree.selection()
            if selected and selected[0] == tree_id:
                self.progress_var.set(status['progress'])
                dl_total = self._format_size(status['total_downloaded'])
                total = self._format_size(status['total_size'])
                dl_speed = self._format_speed(status['download_rate'])
                ul_speed = self._format_speed(status['upload_rate'])
                eta_str = self._format_eta(status['eta'])
                progress_text = (
                    f"{status['progress']:.1f}% | {dl_total}/{total} | "
                    f"↓ {dl_speed} ↑ {ul_speed} | {status['num_peers']} peers | ETA {eta_str}"
                )
                self.lbl_progress_text.config(text=progress_text)
                self.lbl_current_download.config(text=f"Torrent: {torrent_info['name']}")

        # Schedule next poll
        self.root.after(500, self._poll_torrent_status)

    @staticmethod
    def _format_speed(bytes_per_sec):
        """Format speed in human-readable units."""
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        elif bytes_per_sec < 1024 * 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024 * 1024):.2f} GB/s"

    @staticmethod
    def _format_size(size_bytes):
        """Format size in human-readable units."""
        if size_bytes <= 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    @staticmethod
    def _format_eta(seconds):
        """Format ETA as human-readable time."""
        if seconds <= 0:
            return "--:--"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _on_close(self):
        """Clean up torrent session on app exit."""
        if self.torrent_manager:
            try:
                self.torrent_manager.shutdown()
            except:
                pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FitGirlDownloaderApp(root)
    root.mainloop()
