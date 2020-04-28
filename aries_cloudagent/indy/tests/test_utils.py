from os import makedirs
from pathlib import Path
from shutil import rmtree

from asynctest import TestCase as AsyncTestCase, mock as async_mock

import indy.blob_storage

from .. import create_tails_reader, create_tails_writer

TAILS_DIR = "/tmp/indy/revocation/tails_files"
TAILS_HASH = "8UW1Sz5cqoUnK9hqQk7nvtKK65t7Chu3ui866J23sFyJ"
TAILS_LOCAL = f"{TAILS_DIR}/{TAILS_HASH}"


class TestIndyUtils(AsyncTestCase):
    def tearDown(self):
        rmtree(TAILS_DIR, ignore_errors=True)

    async def test_tails_reader(self):
        makedirs(TAILS_DIR, exist_ok=True)
        with open(TAILS_LOCAL, "a") as f:
            print("1234123412431234", file=f)

        with async_mock.patch.object(
            indy.blob_storage, "open_reader", async_mock.CoroutineMock()
        ) as mock_blob_open_reader:
            result = await create_tails_reader(TAILS_LOCAL)
            assert result == mock_blob_open_reader.return_value

        rmtree(TAILS_DIR, ignore_errors=True)
        with self.assertRaises(FileNotFoundError):
            await create_tails_reader(TAILS_LOCAL)

    async def test_tails_writer(self):
        makedirs(TAILS_DIR, exist_ok=True)
        assert await create_tails_writer(TAILS_DIR)

        rmtree(TAILS_DIR, ignore_errors=True)
