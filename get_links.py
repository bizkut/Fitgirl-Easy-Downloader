import os
from datetime import datetime

import pyperclip
import requests
from colorama import Fore, Style

from ff_utils import get_game_links_and_name


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

    def input(self, message):
        return input(
            f"{self.colors['lightblack']}{self.timestamp()} >> "
            f"{self.colors['lightcyan']}INPUT   {self.colors['lightblack']}- "
            f"{self.colors['white']}{message}{self.colors['reset']}"
        )


log = Console()
log.clear()

url = log.input("Enter Fitgirl Game Link : ")
try:
    links, _, _ = get_game_links_and_name(url)
except requests.exceptions.RequestException as e:
    log.error("HTTP request failed", f"{url} ({e})")
    raise SystemExit(1)

if not links:
    log.error("No Matching URLs Found", "Retry..")
else:
    output = "\n".join(links)
    print("Matching URLs:")
    print(output)
    pyperclip.copy(output)
    log.success("All Links Copied To Clipboard", len(links))
