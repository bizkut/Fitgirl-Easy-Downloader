import sys
import types
import unittest


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


if __name__ == '__main__':
    unittest.main()
