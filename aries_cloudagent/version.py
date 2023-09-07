"""Library version information."""

from contextlib import suppress
import importlib.metadata
from pathlib import Path


def extract_version() -> str:
    """Return package version.

    Returns version of the installed package or the one found in nearby pyproject.toml
    for cases when package is not installed (ie. local development and testing).
    """
    try:
        return importlib.metadata.version("aries-cloudagent")
    except importlib.metadata.PackageNotFoundError:
        with suppress(FileNotFoundError, StopIteration):
            with open(
                (Path(__file__).parent.parent) / "pyproject.toml",
                encoding="utf-8",
            ) as pyproject_toml:
                version = (
                    next(line for line in pyproject_toml if line.startswith("version"))
                    .split("=")[1]
                    .strip("'\"\n ")
                )
                return f"{version}"


__version__ = extract_version()
RECORD_TYPE_ACAPY_VERSION = "acapy_version"
