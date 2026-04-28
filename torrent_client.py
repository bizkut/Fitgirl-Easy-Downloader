"""
Built-in torrent client using libtorrent-rasterbar.
All torrents download concurrently within a single session.
"""

import libtorrent as lt
import time
import os
import threading


class TorrentManager:
    """
    Manages a libtorrent session with support for concurrent torrent downloads.
    Each torrent runs simultaneously — no sequential queue.
    """

    # State names matching libtorrent's torrent_status.state_t enum
    STATE_STR = [
        'Checking (q)', 'Checking', 'Downloading Metadata',
        'Downloading', 'Finished', 'Seeding', 'Allocating',
        'Checking (r)'
    ]

    def __init__(self, config=None):
        """
        Initialize the torrent session.

        Args:
            config: dict with optional keys:
                - port_range: (start, end) tuple, default (6881, 6891)
                - max_download_speed: bytes/s, 0 = unlimited
                - max_upload_speed: bytes/s, 0 = unlimited
                - seed_after_download: bool, default True
                - seed_ratio_limit: float, default 1.0
                - encryption: bool, default True
        """
        config = config or {}

        self._torrents = {}  # info_hash_str -> {handle, save_path, name, added_time, ...}
        self._lock = threading.Lock()

        # Session settings
        settings = {
            'user_agent': 'FitGirlEasyDownloader/1.0 libtorrent/' + lt.__version__,
            'listen_interfaces': '0.0.0.0:{}'.format(config.get('port_range', [6881, 6891])[0]),
            'enable_dht': True,
            'enable_lsd': True,
            'enable_upnp': True,
            'enable_natpmp': True,
            'announce_to_all_trackers': True,
            'announce_to_all_tiers': True,
        }

        # Speed limits (0 = unlimited)
        dl_limit = config.get('max_download_speed', 0)
        ul_limit = config.get('max_upload_speed', 0)
        if dl_limit > 0:
            settings['download_rate_limit'] = dl_limit
        if ul_limit > 0:
            settings['upload_rate_limit'] = ul_limit

        # Encryption
        if config.get('encryption', True):
            settings['in_enc_policy'] = lt.enc_policy.pe_enabled
            settings['out_enc_policy'] = lt.enc_policy.pe_enabled

        self._session = lt.session(settings)

        # Bootstrap DHT
        self._session.add_dht_router('router.bittorrent.com', 6881)
        self._session.add_dht_router('router.utorrent.com', 6881)
        self._session.add_dht_router('dht.transmissionbt.com', 6881)
        self._session.add_dht_router('dht.aelitis.com', 6881)

        # Seeding config
        self.seed_after_download = config.get('seed_after_download', True)
        self.seed_ratio_limit = config.get('seed_ratio_limit', 1.0)

    def add_magnet(self, magnet_uri, save_path, name=None, **kwargs):
        """
        Add a magnet link for concurrent download.

        Args:
            magnet_uri: magnet:?xt=urn:btih:... string
            save_path: directory to save downloaded files
            name: optional display name

        Returns:
            torrent_id (str) — the info-hash hex string used as key
        """
        os.makedirs(save_path, exist_ok=True)

        params = lt.parse_magnet_uri(magnet_uri)
        params.save_path = save_path

        handle = self._session.add_torrent(params)
        handle.set_flags(lt.torrent_flags.auto_managed)

        # Use info-hash as unique ID
        info_hash = str(handle.info_hash())

        with self._lock:
            self._torrents[info_hash] = {
                'handle': handle,
                'save_path': save_path,
                'name': name or 'Fetching metadata...',
                'added_time': time.time(),
                'user_stopped': False,
                'initial_upload': kwargs.get('initial_upload', 0),
                'initial_download': kwargs.get('initial_download', 0),
            }

        return info_hash

    def get_status(self, torrent_id):
        """
        Get the current status of a torrent.

        Returns:
            dict with keys: name, state, progress, download_rate, upload_rate,
            num_peers, num_seeds, total_downloaded, total_size, eta,
            total_uploaded, seed_ratio, is_finished, is_seeding, save_path
            OR None if torrent_id not found.
        """
        with self._lock:
            entry = self._torrents.get(torrent_id)
            if not entry:
                return None

        handle = entry['handle']
        s = handle.status()

        # Update name once metadata is received
        if s.has_metadata and entry['name'] == 'Fetching metadata...':
            ti = s.torrent_file
            if ti:
                entry['name'] = ti.name()

        # Calculate ETA
        eta = 0
        if s.download_rate > 0 and s.total_wanted > 0:
            remaining = s.total_wanted - s.total_wanted_done
            eta = remaining / s.download_rate if s.download_rate > 0 else 0

        # Seed ratio calculation with persistence
        current_upload = s.all_time_upload + entry.get('initial_upload', 0)
        current_download = (s.total_wanted_done if s.total_wanted_done > 0 else s.all_time_download) + entry.get('initial_download', 0)
        seed_ratio = (current_upload / current_download) if current_download > 0 else 0.0

        # Check if we should stop seeding (ratio reached)
        is_finished = s.is_finished
        is_seeding = s.is_seeding

        if is_seeding and not entry['user_stopped']:
            if not self.seed_after_download:
                handle.pause()
                entry['user_stopped'] = True
            elif self.seed_ratio_limit > 0 and seed_ratio >= self.seed_ratio_limit:
                handle.pause()
                entry['user_stopped'] = True

        state_idx = s.state
        state_name = self.STATE_STR[state_idx] if state_idx < len(self.STATE_STR) else 'Unknown'

        return {
            'name': entry['name'],
            'state': state_name,
            'state_idx': state_idx,
            'progress': s.progress * 100,
            'download_rate': s.download_rate,
            'upload_rate': s.upload_rate,
            'num_peers': s.num_peers,
            'num_seeds': s.num_seeds,
            'total_downloaded': current_download,
            'total_size': s.total_wanted,
            'eta': eta,
            'total_uploaded': current_upload,
            'seed_ratio': seed_ratio,
            'is_finished': is_finished,
            'is_seeding': is_seeding,
            'is_paused': s.paused,
            'save_path': entry['save_path'],
            'has_metadata': s.has_metadata,
        }

    def pause(self, torrent_id):
        """Pause a torrent."""
        with self._lock:
            entry = self._torrents.get(torrent_id)
            if entry:
                entry['handle'].pause()
                entry['user_stopped'] = True

    def resume(self, torrent_id):
        """Resume a paused torrent."""
        with self._lock:
            entry = self._torrents.get(torrent_id)
            if entry:
                entry['handle'].resume()
                entry['user_stopped'] = False

    def remove(self, torrent_id, delete_files=False):
        """Remove a torrent from the session."""
        with self._lock:
            entry = self._torrents.pop(torrent_id, None)
            if entry:
                if delete_files:
                    self._session.remove_torrent(entry['handle'], lt.options_t.delete_files)
                else:
                    self._session.remove_torrent(entry['handle'])

    def set_download_limit(self, torrent_id, limit_bytes):
        """Set per-torrent download rate limit (0 = unlimited)."""
        with self._lock:
            entry = self._torrents.get(torrent_id)
            if entry:
                entry['handle'].set_download_limit(limit_bytes)

    def set_upload_limit(self, torrent_id, limit_bytes):
        """Set per-torrent upload rate limit (0 = unlimited)."""
        with self._lock:
            entry = self._torrents.get(torrent_id)
            if entry:
                entry['handle'].set_upload_limit(limit_bytes)

    def get_all_ids(self):
        """Return list of all active torrent IDs."""
        with self._lock:
            return list(self._torrents.keys())

    def shutdown(self):
        """Gracefully shut down the session."""
        # Pause all torrents first
        with self._lock:
            for entry in self._torrents.values():
                try:
                    entry['handle'].pause()
                except:
                    pass
        # Small delay to let libtorrent flush
        time.sleep(0.5)
