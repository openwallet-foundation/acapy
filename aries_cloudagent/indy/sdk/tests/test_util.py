import pytest

from os import makedirs
from os.path import join
from pathlib import Path
from shutil import rmtree

import indy.blob_storage

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ...util import indy_client_dir, generate_pr_nonce, tails_path

from ..util import create_tails_reader, create_tails_writer

from .. import util as test_module


@pytest.mark.indy
class TestIndyUtils(AsyncTestCase):
    TAILS_HASH = "8UW1Sz5cqoUnK9hqQk7nvtKK65t7Chu3ui866J23sFyJ"

    def tearDown(self):
        tails_dir = indy_client_dir("tails", create=False)
        rmtree(tails_dir, ignore_errors=True)

    async def test_tails_reader(self):
        tails_dir = indy_client_dir("tails", create=True)
        tails_local = f"{tails_dir}/{TestIndyUtils.TAILS_HASH}"

        with open(tails_local, "a") as f:
            print("1234123412431234", file=f)

        with async_mock.patch.object(
            indy.blob_storage, "open_reader", async_mock.CoroutineMock()
        ) as mock_blob_open_reader:
            result = await create_tails_reader(tails_local)
            assert result == mock_blob_open_reader.return_value

        rmtree(tails_dir, ignore_errors=True)
        with self.assertRaises(FileNotFoundError):
            await create_tails_reader(tails_local)

    async def test_tails_writer(self):
        tails_dir = indy_client_dir("tails", create=True)
        assert await create_tails_writer(tails_dir)

        rmtree(tails_dir, ignore_errors=True)

    async def test_nonce(self):
        assert await generate_pr_nonce()

    async def test_tails_path(self):
        tails_dir = indy_client_dir("tails", create=False)
        rmtree(tails_dir, ignore_errors=True)

        tails_local_path = tails_path("rev-reg-id")
        assert tails_local_path is None

        tails_rr_dir = indy_client_dir(join("tails", "rev-reg-id"), create=True)
        tails_local_path = tails_path("rev-reg-id")
        assert tails_local_path is None

        with open(join(tails_rr_dir, "tails-hash"), "w") as f:
            f.write("content")
        tails_local_path = tails_path("rev-reg-id")
        assert tails_local_path
