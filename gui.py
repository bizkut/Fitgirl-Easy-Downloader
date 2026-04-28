import os
import json
import threading
import queue
import re
import time
import requests
import webbrowser
from io import BytesIO
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

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
        
        self.setup_ui()
        self.start_download_worker()

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
        
        self.btn_queue = ttk.Button(self.info_frame, text="Add to Queue", command=self.add_to_queue, state=tk.DISABLED)
        self.btn_queue.grid(row=5, column=1, sticky=tk.W, pady=(5, 0))

        self.txt_desc = tk.Text(self.info_frame, wrap=tk.WORD, height=4, width=40, font=('Helvetica', 9))
        self.txt_desc.grid(row=6, column=0, columnspan=3, pady=(10, 0), sticky=tk.EW)
        self.txt_desc.insert(tk.END, "Description: -")
        self.txt_desc.config(state=tk.DISABLED)
        self.info_frame.columnconfigure(1, weight=1)

        self.fitgirl_lbl = ttk.Label(self.info_frame, cursor="hand2")
        self.fitgirl_lbl.grid(row=0, column=2, rowspan=5, padx=(10, 0))
        self.fitgirl_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://fitgirl-repacks.site/donations/"))
        
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
        self.btn_cancel = ttk.Button(action_frame, text="Cancel", command=self.cancel_item, state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT)
        
        # Now pack the treeview to take up remaining space
        self.queue_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.queue_tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        self.fetched_data = None

    def on_tree_select(self, event):
        selected = self.queue_tree.selection()
        if selected:
            item_id = selected[0]
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
                self.btn_cancel.config(state=tk.NORMAL)
            else:
                self.btn_cancel.config(state=tk.NORMAL)
        else:
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_resume.config(state=tk.DISABLED)
            self.btn_cancel.config(state=tk.DISABLED)

    def stop_item(self):
        selected = self.queue_tree.selection()
        if selected:
            item_id = selected[0]
            if self.queue_items[item_id]['status'] == 'Downloading':
                self.abort_flag = True
                self.queue_items[item_id]['status'] = 'Stopped'
                self.queue_tree.set(item_id, 'status', 'Stopped')
                self.on_tree_select(None)

    def resume_item(self):
        selected = self.queue_tree.selection()
        if selected:
            item_id = selected[0]
            if self.queue_items[item_id]['status'] == 'Stopped':
                self.queue_items[item_id]['status'] = 'Queued'
                self.queue_tree.set(item_id, 'status', 'Queued')
                self.on_tree_select(None)

    def cancel_item(self):
        selected = self.queue_tree.selection()
        if selected:
            item_id = selected[0]
            if self.queue_items[item_id]['status'] == 'Downloading':
                self.abort_flag = True
            
            del self.queue_items[item_id]
            self.queue_tree.delete(item_id)
            self.on_tree_select(None)

    def change_dir(self):
        self.choose_download_dir()
        self.lbl_download_dir.config(text=f"Download Dir: {self.config_manager.get_download_dir()}")

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

            self.fetched_data = {
                "url": url,
                "name": game_name,
                "links": links,
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
        self.btn_queue.config(state=tk.NORMAL)

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

    def _load_fitgirl_image(self):
        try:
            r = requests.get("https://fitgirl-repacks.site/wp-content/uploads/2024/05/support2.jpg")
            img_data = r.content
            img = Image.open(BytesIO(img_data))
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

if __name__ == "__main__":
    root = tk.Tk()
    app = FitGirlDownloaderApp(root)
    root.mainloop()
