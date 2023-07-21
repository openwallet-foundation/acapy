"""Module to contain logic to generate the banner for ACA-py."""


from contextlib import contextmanager
from enum import Enum, auto
import sys
import textwrap
from typing import Optional, TextIO


@contextmanager
def Banner(border: str, length: int, file: Optional[TextIO] = None):
    """Context manager to generate a banner for ACA-py."""
    banner = _Banner(border, length, file)
    banner.print_border()
    yield banner
    banner.print_border()


class _Banner:
    """Management class to generate a banner for ACA-py."""

    class align(Enum):
        """Alignment options for banner elements."""

        LEFT = auto()
        CENTER = auto()
        RIGHT = auto()

    def __init__(self, border: str, length: int, file: Optional[TextIO] = None):
        """Initialize the banner object.

        The ``border`` is a single character to be used, and ``length``
        is the desired length of the whole banner, inclusive.
        """
        self.border = border
        self.length = length
        self.file = file or sys.stdout

    def _print(self, text: str):
        """Print value."""
        print(text, file=self.file)

    def _lr_pad(self, content: str):
        """Pad string content with defined border character.

        Args:
            content: String content to pad
        """
        return f"{self.border}{self.border} {content} {self.border}{self.border}"

    def _print_line(self, text: str, alignment: align = align.LEFT):
        """Print line."""
        lines = textwrap.wrap(text, width=self.length)
        for line in lines:
            if len(line) < self.length:
                if alignment == self.align.LEFT:
                    left = ""
                    right = " " * (self.length - len(line))
                elif alignment == self.align.CENTER:
                    left = " " * ((self.length - len(line)) // 2)
                    right = " " * ((self.length - len(line)) // 2)
                    if len(line) % 2 != 0:
                        right += " "
                elif alignment == self.align.RIGHT:
                    left = " " * (self.length - len(line))
                    right = ""
                else:
                    raise ValueError(f"Invalid alignment: {alignment}")
                line = f"{left}{line}{right}"
            self._print(self._lr_pad(line))

    def print_border(self):
        """Print a full line using the border character."""
        self._print(self.border * (self.length + 6))

    def title(self, title, spacing_after: int = 2):
        """Print the main title element."""
        self._print_line(title, self.align.CENTER)
        for _ in range(spacing_after):
            self.spacer()

    def spacer(self):
        """Print an empty line with the border character only."""
        self._print(self._lr_pad(" " * self.length))

    def hr(self, char: str = "-"):
        """Print a line with a horizontal rule."""
        self._print(self._lr_pad(char * self.length))

    def subtitle(self, title: str, spacing_after: int = 1):
        """Print a subtitle for a section."""
        title += ":"
        self._print_line(title, self.align.LEFT)
        for _ in range(spacing_after):
            self.spacer()

    def list(self, items, spacing_after: int = 1):
        """Print a list of items, prepending a dash to each item."""
        for item in items:
            self._print_line(f"  - {item}", self.align.LEFT)

        for _ in range(spacing_after):
            self.spacer()

    def version(self, version):
        """Print the current ``version``."""
        version = f"ver: {version}"
        self._print_line(version, self.align.RIGHT)

    def print(self, text: str):
        """Print a line of text."""
        self._print_line(text, self.align.LEFT)

    def left(self, text: str):
        """Print a line of text left aligned.

        Same as `print` method.
        """
        self._print_line(text, self.align.LEFT)

    def centered(self, text: str):
        """Print a line of text centered."""
        self._print_line(text, self.align.CENTER)

    def right(self, text: str):
        """Print a line of text right aligned."""
        self._print_line(text, self.align.RIGHT)
