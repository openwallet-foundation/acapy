"""Temp file utilities."""

import tempfile

TEMP_DIRS = {}


def get_temp_dir(category: str) -> str:
    """Accessor for the temp directory."""
    if category not in TEMP_DIRS:
        TEMP_DIRS[category] = tempfile.TemporaryDirectory(category)
    return TEMP_DIRS[category].name
