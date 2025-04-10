"""Module to contain logic to generate the banner for ACA-py."""

import logging
import textwrap
from contextlib import contextmanager
from enum import Enum, auto
from typing import Optional, TextIO

logger = logging.getLogger(__name__)


@contextmanager
def Banner(border: str, length: int, file: Optional[TextIO] = None):
    """Context manager to generate a banner for ACA-py."""
    banner = _Banner(border, length, file)
    banner.add_border()
    yield banner
    banner.add_border()

    # Join all lines with newlines and log them
    banner_text = "\n".join(banner.lines)
    banner_text = f"\n{banner_text.strip()}\n"  # Start/end with a newline
    if file:
        print(banner_text, file=file)
    else:
        logger.info(banner_text)


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
        self.file = file
        self.lines = []

    def _add_line(self, text: str):
        """Add a line to the banner."""
        self.lines.append(text)

    def _lr_pad(self, content: str):
        """Pad string content with defined border character.

        Args:
            content: String content to pad
        """
        return f"{self.border}{self.border} {content} {self.border}{self.border}"

    def _format_line(self, text: str, alignment: align = align.LEFT):
        """Format a line with the specified alignment."""
        lines = textwrap.wrap(text, width=self.length)
        formatted_lines = []

        for line in lines:
            if len(line) < self.length:
                if alignment == self.align.LEFT:
                    # Left alignment
                    formatted_line = f"{line:<{self.length}}"
                elif alignment == self.align.CENTER:
                    # Center alignment
                    total_padding = self.length - len(line)
                    left_padding = total_padding // 2
                    right_padding = total_padding - left_padding
                    formatted_line = f"{' ' * left_padding}{line}{' ' * right_padding}"
                elif alignment == self.align.RIGHT:
                    # Right alignment
                    formatted_line = f"{line:>{self.length}}"
                else:
                    raise ValueError(f"Invalid alignment: {alignment}")
            else:
                formatted_line = line

            formatted_lines.append(self._lr_pad(formatted_line))

        return formatted_lines

    def add_border(self):
        """Add a full line using the border character."""
        self._add_line(self.border * (self.length + 6))

    def title(self, title, spacing_after: int = 2):
        """Add the main title element."""
        self.lines.extend(self._format_line(title, self.align.CENTER))
        for _ in range(spacing_after):
            self.spacer()

    def spacer(self):
        """Add an empty line with the border character only."""
        self._add_line(self._lr_pad(" " * self.length))

    def hr(self, char: str = "-"):
        """Add a line with a horizontal rule."""
        self._add_line(self._lr_pad(char * self.length))

    def subtitle(self, title: str, spacing_after: int = 1):
        """Add a subtitle for a section."""
        title += ":"
        self.lines.extend(self._format_line(title, self.align.LEFT))
        for _ in range(spacing_after):
            self.spacer()

    def list(self, items, spacing_after: int = 1):
        """Add a list of items, prepending a dash to each item."""
        for item in items:
            self.lines.extend(self._format_line(f"  - {item}", self.align.LEFT))

        for _ in range(spacing_after):
            self.spacer()

    def version(self, version):
        """Add the current ``version``."""
        version = f"ver: {version}"
        self.lines.extend(self._format_line(version, self.align.RIGHT))

    def print(self, text: str):
        """Add a line of text."""
        self.lines.extend(self._format_line(text, self.align.LEFT))

    def left(self, text: str):
        """Add a line of text left aligned.

        Same as `print` method.
        """
        self.lines.extend(self._format_line(text, self.align.LEFT))

    def centered(self, text: str):
        """Add a line of text centered."""
        self.lines.extend(self._format_line(text, self.align.CENTER))

    def right(self, text: str):
        """Add a line of text right aligned."""
        self.lines.extend(self._format_line(text, self.align.RIGHT))
