import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch


def _install_import_stubs():
    requests_stub = types.ModuleType('requests')
    requests_stub.get = lambda *args, **kwargs: None
    requests_stub.head = lambda *args, **kwargs: None
    sys.modules.setdefault('requests', requests_stub)

    bs4_stub = types.ModuleType('bs4')
    bs4_stub.BeautifulSoup = lambda *args, **kwargs: None
    sys.modules.setdefault('bs4', bs4_stub)

    pil_stub = types.ModuleType('PIL')
    pil_stub.Image = types.ModuleType('Image')
    pil_stub.ImageTk = types.ModuleType('ImageTk')
    sys.modules.setdefault('PIL', pil_stub)
    sys.modules.setdefault('PIL.Image', pil_stub.Image)
    sys.modules.setdefault('PIL.ImageTk', pil_stub.ImageTk)


_install_import_stubs()

from ff_utils import FuckingFastVerificationRequired, resolve_fuckingfast_download
from gui import FitGirlDownloaderApp


class FuckingFastEtaEstimateTests(unittest.TestCase):
    def test_first_part_size_is_enough_for_total_estimate(self):
        batch_state = {
            'part_sizes': {1: 500},
            'standard_part_size': 500,
            'last_part_size': 0,
        }

        self.assertTrue(FitGirlDownloaderApp._is_fuckingfast_total_estimate_ready(batch_state, 120))
        self.assertEqual(FitGirlDownloaderApp._estimate_fuckingfast_total_size(batch_state, 120), 60000)

    def test_last_part_size_refines_total_estimate(self):
        batch_state = {
            'part_sizes': {1: 500, 120: 200},
            'standard_part_size': 500,
            'last_part_size': 200,
        }

        self.assertTrue(FitGirlDownloaderApp._is_fuckingfast_total_estimate_ready(batch_state, 120))
        self.assertEqual(FitGirlDownloaderApp._estimate_fuckingfast_total_size(batch_state, 120), 59700)

    def test_single_part_ready_when_its_size_is_known(self):
        batch_state = {
            'part_sizes': {1: 300},
            'standard_part_size': 0,
            'last_part_size': 0,
        }

        self.assertTrue(FitGirlDownloaderApp._is_fuckingfast_total_estimate_ready(batch_state, 1))
        self.assertEqual(FitGirlDownloaderApp._estimate_fuckingfast_total_size(batch_state, 1), 300)


class FetchInfoTests(unittest.TestCase):
    def test_fetch_keeps_magnet_when_no_fuckingfast_links_exist(self):
        response = MagicMock(text="page html")
        magnet_link = "magnet:?xt=urn:btih:0123456789abcdef"
        entry_content = MagicMock()
        entry_content.find.return_value = None
        entry_content.find_all.return_value = []
        entry_content.get_text.return_value = ""
        soup = MagicMock()
        soup.find.side_effect = [entry_content, {"href": magnet_link}]
        soup.find_all.return_value = []

        app = FitGirlDownloaderApp.__new__(FitGirlDownloaderApp)
        app.root = MagicMock()
        app.root.after.side_effect = lambda _delay, callback: callback()
        app._update_ui_with_fetch = MagicMock()
        app.btn_queue = MagicMock()
        app.btn_torrent = MagicMock()
        app.queue_items = {}
        app.torrent_manager = MagicMock()
        app.torrent_queue_items = {}

        with (
            patch("gui.requests.get", return_value=response),
            patch("gui.BeautifulSoup", return_value=soup),
            patch("gui.extract_fuckingfast_links", return_value=[]),
            patch("gui.extract_game_name", return_value="Torrent-only Game"),
        ):
            app._fetch_thread("https://fitgirl-repacks.site/torrent-only-game/")

        fetched_data = app.fetched_data
        assert fetched_data is not None
        self.assertEqual(fetched_data["links"], [])
        self.assertEqual(fetched_data["magnet_link"], magnet_link)
        app._update_ui_with_fetch.assert_called_once_with()

        app._update_action_buttons_state()
        app.btn_queue.config.assert_called_once_with(state="disabled")
        app.btn_torrent.config.assert_called_once_with(state="normal")

    def test_fuckingfast_button_recovers_for_new_page_with_failed_queue_entry(self):
        app = FitGirlDownloaderApp.__new__(FitGirlDownloaderApp)
        app.btn_queue = MagicMock()
        app.btn_torrent = MagicMock()
        app.torrent_manager = MagicMock()
        app.torrent_queue_items = {}
        app.queue_items = {}
        app.fetched_data = {
            'url': 'https://fitgirl-repacks.site/no-fuckingfast/',
            'links': [],
            'magnet_link': 'magnet:?xt=urn:btih:no-links',
        }

        app._update_action_buttons_state()
        app.btn_queue.config.assert_called_with(state="disabled")

        alchemy_url = 'https://fitgirl-repacks.site/alchemy-factory/'
        app.fetched_data = {
            'url': alchemy_url,
            'links': ['https://fuckingfast.co/alchemy-part-1'],
            'magnet_link': 'magnet:?xt=urn:btih:alchemy',
        }
        app.queue_items = {
            'failed-alchemy': {'url': alchemy_url, 'status': 'Failed'}
        }

        app._update_action_buttons_state()

        app.btn_queue.config.assert_called_with(state="normal")

    def test_fuckingfast_retry_reuses_failed_queue_row(self):
        app = FitGirlDownloaderApp.__new__(FitGirlDownloaderApp)
        app.queue_tree = MagicMock()
        app.save_queue = MagicMock()
        app._update_action_buttons_state = MagicMock()
        alchemy_url = 'https://fitgirl-repacks.site/alchemy-factory/'
        app.fetched_data = {
            'url': alchemy_url,
            'name': 'Alchemy Factory',
            'links': ['https://fuckingfast.co/alchemy-part-1'],
            'magnet_link': 'magnet:?xt=urn:btih:alchemy',
        }
        app.queue_items = {
            'failed-alchemy': {
                'url': alchemy_url,
                'name': 'Alchemy Factory',
                'status': 'Failed',
            }
        }

        app.add_to_queue()

        app.queue_tree.insert.assert_not_called()
        self.assertEqual(app.queue_items['failed-alchemy']['status'], 'Queued')
        self.assertEqual(app.queue_items['failed-alchemy']['links'], app.fetched_data['links'])
        app.queue_tree.item.assert_called_once_with(
            'failed-alchemy', values=('Alchemy Factory', 'Queued')
        )
        app.save_queue.assert_called_once_with()


class FuckingFastVerificationTests(unittest.TestCase):
    def test_cloudflare_challenge_raises_browser_verification_error(self):
        response = MagicMock()
        response.status_code = 403
        response.headers = {'cf-mitigated': 'challenge'}
        response.text = '<title>Just a moment...</title>'

        with patch('ff_utils.requests.get', return_value=response):
            with self.assertRaises(FuckingFastVerificationRequired):
                resolve_fuckingfast_download('https://fuckingfast.co/example', fetch_size=False)

        response.raise_for_status.assert_not_called()

    def test_turnstile_download_gate_raises_browser_verification_error(self):
        response = MagicMock(status_code=200, headers={}, text='download page')
        soup = MagicMock()
        soup.select_one.return_value = object()

        with (
            patch('ff_utils.requests.get', return_value=response),
            patch('ff_utils.BeautifulSoup', return_value=soup),
        ):
            with self.assertRaises(FuckingFastVerificationRequired):
                resolve_fuckingfast_download('https://fuckingfast.co/example', fetch_size=False)

    def test_gui_recommends_torrent_when_verification_is_required(self):
        app = FitGirlDownloaderApp.__new__(FitGirlDownloaderApp)
        app.queue_tree = MagicMock()
        app.queue_tree.exists.return_value = True
        app.btn_queue = MagicMock()
        app.btn_torrent = MagicMock()
        app.fetched_data = {
            'url': 'https://fitgirl-repacks.site/example/',
            'links': ['https://fuckingfast.co/example'],
            'magnet_link': 'magnet:?xt=urn:btih:example',
        }
        app.queue_items = {'queued-item': {'url': app.fetched_data['url']}}
        app.torrent_manager = MagicMock()
        app.torrent_queue_items = {}
        item = {'magnet_link': 'magnet:?xt=urn:btih:example'}

        with patch('gui.messagebox.showwarning') as showwarning:
            app._mark_fuckingfast_verification_required('queue-item', item)

        expected_status = "Browser verification required — use Torrent Download"
        self.assertEqual(item['status'], expected_status)
        app.queue_tree.set.assert_called_once_with('queue-item', 'status', expected_status)
        app.btn_queue.config.assert_called_once_with(state="disabled")
        app.btn_torrent.config.assert_called_once_with(state="normal")
        self.assertIn('Torrent Download', showwarning.call_args.args[1])

    def test_download_worker_surfaces_verification_failure(self):
        class WorkerStopped(Exception):
            pass

        class OneCycleQueue(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.items_calls = 0

            def items(self):
                self.items_calls += 1
                if self.items_calls > 1:
                    raise WorkerStopped
                return super().items()

        item = {
            'name': 'Torrent-only Game',
            'links': ['https://fuckingfast.co/example'],
            'magnet_link': 'magnet:?xt=urn:btih:example',
            'status': 'Queued',
        }
        app = FitGirlDownloaderApp.__new__(FitGirlDownloaderApp)
        app.queue_items = OneCycleQueue({'queue-item': item})
        app.root = MagicMock()
        app.root.after.side_effect = lambda _delay, callback: callback()
        app.queue_tree = MagicMock()
        app.queue_tree.exists.return_value = True
        app.config_manager = MagicMock()
        app._resolve_fuckingfast_download = MagicMock(
            side_effect=FuckingFastVerificationRequired('verification required')
        )
        app._mark_fuckingfast_verification_required = MagicMock()
        app._set_current_download_text = MagicMock()
        app._reset_progress_widgets = MagicMock()
        app.on_tree_select = MagicMock()
        app.save_queue = MagicMock()

        with tempfile.TemporaryDirectory() as download_dir:
            app.config_manager.get_download_dir.return_value = download_dir
            with patch('builtins.print'):
                with self.assertRaises(WorkerStopped):
                    app._download_worker()

        expected_status = "Browser verification required — use Torrent Download"
        self.assertEqual(item['status'], expected_status)
        app._mark_fuckingfast_verification_required.assert_called_once_with('queue-item', item)
        app.save_queue.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
