"""Indy utilities."""

import json

from pathlib import Path

import indy.blob_storage


async def create_tails_reader(tails_file_path: str) -> int:
    """Get a handle for the blob_storage file reader."""
    tails_file_path = Path(tails_file_path)

    if not tails_file_path.exists():
        raise FileNotFoundError("Tails file does not exist.")

    tails_reader_config = json.dumps(
        {
            "base_dir": str(tails_file_path.parent.absolute()),
            "file": str(tails_file_path.name),
        }
    )
    return await indy.blob_storage.open_reader("default", tails_reader_config)


async def create_tails_writer(tails_base_dir: str) -> int:
    """Get a handle for the blob_storage file writer."""
    tails_writer_config = json.dumps({"base_dir": tails_base_dir, "uri_pattern": ""})
    return await indy.blob_storage.open_writer("default", tails_writer_config)
