"""Environment utility methods."""

from os import getenv
from pathlib import Path


def storage_path(*subpaths, create: bool = False) -> Path:
    """Get the default aca-py home directory."""
    custom = getenv("ACAPY_HOME")
    if custom:
        path = Path(custom)
    else:
        path = Path.home().joinpath(".acapy_agent")
    if subpaths:
        path = path.joinpath(*subpaths)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path
