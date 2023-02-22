"""Utilities for dealing with Indy conventions."""

from os import getenv, makedirs, urandom
from os.path import isdir, join
from pathlib import Path
from platform import system


async def generate_pr_nonce() -> str:
    """Generate a nonce for a proof request."""
    # equivalent to indy.anoncreds.generate_nonce
    return str(int.from_bytes(urandom(10), "big"))


def indy_client_dir(subpath: str = None, create: bool = False) -> str:
    """
    Return '/'-terminated subdirectory of indy-client directory.

    Args:
        subpath: subpath within indy-client structure
        create: whether to create subdirectory if absent
    """

    home = Path.home()
    target_dir = join(
        home,
        "Documents"
        if isdir(join(home, "Documents"))
        else getenv("EXTERNAL_STORAGE", "")
        if system() == "Linux"
        else "",
        ".indy_client",
        subpath if subpath else "",
        "",  # set trailing separator
    )
    if create:
        makedirs(target_dir, exist_ok=True)

    return target_dir
