"""Module to contain logic to generate the banner for ACA-py."""


class Banner:
    """Management class to generate a banner for ACA-py."""

    def __init__(self, border: str, length: int):
        """Initialize the banner object.

        The ``border`` is a single character to be used, and ``length``
        is the desired length of the whole banner, inclusive.
        """
        self.border = border
        self.length = length

    def print_border(self):
        """Print a full line using the border character."""
        print(self.border * (self.length + 6))

    def print_title(self, title):
        """Print the main title element."""
        spacer = " " * (self.length - len(title))
        print(self.lr_pad(f"{title}{spacer}"))

    def print_spacer(self):
        """Print an empty line with the border character only."""
        print(self.lr_pad(" " * self.length))

    def print_subtitle(self, title):
        """Print a subtitle for a section."""
        title += ":"
        spacer = " " * (self.length - len(title))
        print(self.lr_pad(f"{title}{spacer}"))

    def print_list(self, items):
        """Print a list of items, prepending a dash to each item."""
        for item in items:
            left_part = f"  - {item}"
            spacer = " " * (self.length - len(left_part))
            print(self.lr_pad(f"{left_part}{spacer}"))

    def print_version(self, version):
        """Print the current ``version``."""
        version = f"ver: {version}"
        spacer = " " * (self.length - len(version))
        print(self.lr_pad(f"{spacer}{version}"))

    def lr_pad(self, content: str):
        """Pad string content with defined border character.

        Args:
            content: String content to pad
        """
        return f"{self.border}{self.border} {content} {self.border}{self.border}"
