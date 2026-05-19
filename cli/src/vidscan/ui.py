import os
import sys
from dataclasses import dataclass
from collections.abc import Iterator
import itertools

from .utils import enable_ansi_windows

@dataclass(frozen=True, slots=True)
class UI:
    is_terminal: bool
    bar_fill: str
    bar_empty: str
    spinner: Iterator[str]
    color_red: str
    color_yellow: str
    color_green: str
    color_cyan: str
    color_reset: str

    def error(self, text: object) -> str:
        return f"{self.color_red}{text}{self.color_reset}"

    def warning(self, text: object) -> str:
        return f"{self.color_yellow}{text}{self.color_reset}"

    def success(self, text: object) -> str:
        return f"{self.color_green}{text}{self.color_reset}"

    def info(self, text: object) -> str:
        return f"{self.color_cyan}{text}{self.color_reset}"
    
def get_ui() -> UI:
    # getattr fallback when stdout not have encoding attribute
    stdout_encoding = getattr(sys.stdout, 'encoding', '')
    is_utf8 = stdout_encoding and stdout_encoding.lower() in ['utf-8', 'utf8']

    if is_utf8:
        bar_fill = '█'
        bar_empty = '░'
        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    else:
        # Fallback for terminals that don't support utf-8
        bar_fill = '='
        bar_empty = '-'
        spinner = ['|', '/', '-', '\\']

    is_terminal = sys.stdout.isatty()

    color = False

    # Flags used by CI/CD tools
    if 'FORCE_COLOR' in os.environ or 'CLICOLOR_FORCE' in os.environ:
        color = True
    # 'NO_COLOR' standard (https://no-color.org/)
    elif 'NO_COLOR' in os.environ:
        color = False
    elif is_terminal and enable_ansi_windows():
        color = True
    if color:
        red = '\033[91m'
        yellow = '\033[93m'
        green = '\033[92m'
        cyan = '\033[96m'
        reset = '\033[0m'
    else:
        red = yellow = green = cyan = reset = ''

    return UI(
        is_terminal=is_terminal,
        bar_fill=bar_fill,
        bar_empty=bar_empty,
        spinner=itertools.cycle(spinner),
        color_red=red,
        color_yellow=yellow,
        color_green=green,
        color_cyan=cyan,
        color_reset=reset
    )