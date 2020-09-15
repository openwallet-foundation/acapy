"""Libindy utility functions."""

from os import getenv, listdir, makedirs
from os.path import isdir, join
from pathlib import Path
from platform import system

from indy.anoncreds import generate_nonce


async def generate_pr_nonce():
    """Generate a nonce for a proof request."""
    return await generate_nonce()


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


def tails_path(rev_reg_id: str) -> str:
    """Return path to indy tails file for input rev reg id."""

    tails_dir = indy_client_dir(join("tails", rev_reg_id), create=False)
    if not isdir(tails_dir):
        return None

    content = listdir(tails_dir)
    if len(content) != 1:
        return None

    return join(tails_dir, content[0])
