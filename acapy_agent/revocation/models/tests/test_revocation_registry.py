from copy import deepcopy
from http import HTTPStatus
from pathlib import Path
from shutil import rmtree
from unittest import IsolatedAsyncioTestCase, mock

import aiohttp
import base58

from ....indy.util import indy_client_dir
from ...error import RevocationError
from .. import revocation_registry as test_module
from ..revocation_registry import RevocationRegistry


class _MockResponse:
    def __init__(self, status, chunks):
        self.status = status
        self.content = _MockContent(chunks)


class _MockContent:
    def __init__(self, chunks):
        self._chunks = chunks

    def iter_chunked(self, chunk_size):
        async def _iter():
            for chunk in self._chunks:
                yield chunk

        return _iter()


def _mock_aiohttp_session(chunks=None, response_status=HTTPStatus.OK, get_side_effect=None):
    chunks = chunks or [b"abcd1234", b""]

    mock_response = _MockResponse(response_status, chunks)

    mock_get = mock.AsyncMock()
    mock_get.__aenter__ = mock.AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = mock.AsyncMock(return_value=False)

    mock_session_instance = mock.AsyncMock()
    mock_session_instance.get = mock.Mock(
        side_effect=get_side_effect,
        return_value=mock_get,
    )
    mock_session_instance.__aenter__ = mock.AsyncMock(return_value=mock_session_instance)
    mock_session_instance.__aexit__ = mock.AsyncMock(return_value=False)

    mock_session_class = mock.Mock(return_value=mock_session_instance)

    return mock.patch.object(test_module.aiohttp, "ClientSession", mock_session_class)

TEST_DID = "FkjWznKwA4N1JEp2iPiKPG"
CRED_DEF_ID = f"{TEST_DID}:3:CL:12:tag1"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:tag1"
TAILS_DIR = indy_client_dir("tails")
TAILS_HASH = "8UW1Sz5cqoUnK9hqQk7nvtKK65t7Chu3ui866J23sFyJ"
TAILS_LOCAL = f"{TAILS_DIR}{REV_REG_ID}/{TAILS_HASH}"
REV_REG_DEF = {
    "ver": "1.0",
    "id": REV_REG_ID,
    "revocDefType": "CL_ACCUM",
    "tag": "tag1",
    "credDefId": CRED_DEF_ID,
    "value": {
        "issuanceType": "ISSUANCE_ON_DEMAND",
        "maxCredNum": 5,
        "publicKeys": {
            "accumKey": {
                "z": "1 21C2C33125242BF80E85DECC0DD7D81197C2CA827179724081623CEBB03C3DBE 1 0ACA5C9CDBAF5348E8F4783AB5FFBDA480C5075F549BBD53A4D71613C584C97B 1 0EB5326BF28738CEA8863A1F6783AEA97847E7C42C7713C356C8FCF8B8187723 1 174D9052BAABB63B1D6CDC4C468CC00095BF9C7ECCEC941B3B1493EF57644237 1 18A38A66728EF7C7E206A1C15B052848E4AC6281878A7957C54C8FFFFC96A0D7 1 1F9414C188301F4A1DBCD16D6B4B68B27072034F1FA12B6437E5FB174D819DAB 1 094C0D112DD652D1B224FFDC79679CCB08D4BDC2820C354C07B9F55570D0E79E 1 25066D0C941E0090A780B0E3468FAB8529B3C3671A7E93CC57CE1D563B856A23 1 01DF5AAC4322FE2A0AC2BEF491E4FE8B438C79C876B960F9C64FC893A01164BA 1 21E5D8CAA97DD06498C845E544C75D5843B729CC3B1FFCB26BB3380146E4A468 1 2315EAAACFB957A56F75DB8856350D193F62D895E37B8C258F690AA97235D9C2 1 1A763EC7BEC67E521A69A0C4CC482FF98C9D7FE49DFB6EEC77978614C2FE91C8"
            }
        },
        "tailsHash": TAILS_HASH,
        "tailsLocation": TAILS_LOCAL,
    },
}


class TestRevocationRegistry(IsolatedAsyncioTestCase):
    def tearDown(self):
        rmtree(TAILS_DIR, ignore_errors=True)

    async def test_init(self):
        rev_reg = RevocationRegistry()
        assert str(rev_reg).startswith("<RevocationRegistry")

        for public in (True, False):
            rev_reg = RevocationRegistry.from_definition(REV_REG_DEF, public_def=public)
            if public:
                assert rev_reg.tails_local_path
                assert rev_reg.tails_public_uri
            else:
                assert rev_reg.tails_local_path
                assert not rev_reg.tails_public_uri

    async def test_properties(self):
        rev_reg = RevocationRegistry.from_definition(REV_REG_DEF, public_def=False)

        assert rev_reg.cred_def_id == REV_REG_DEF["credDefId"]
        assert rev_reg.issuer_did == TEST_DID
        assert rev_reg.max_creds == 5
        assert rev_reg.reg_def_type == "CL_ACCUM"
        assert rev_reg.registry_id == REV_REG_ID
        assert rev_reg.tag == "tag1"
        assert rev_reg.tails_hash == "8UW1Sz5cqoUnK9hqQk7nvtKK65t7Chu3ui866J23sFyJ"
        rev_reg.tails_local_path = "dummy"
        assert rev_reg.tails_local_path == "dummy"
        rev_reg.tails_public_uri = "dummy"
        assert rev_reg.tails_public_uri == "dummy"
        assert rev_reg.reg_def == REV_REG_DEF

    async def test_tails_local_path(self):
        rr_def_public = deepcopy(REV_REG_DEF)
        rr_def_public["value"]["tailsLocation"] = "http://sample.ca:8088/path"
        rev_reg_pub = RevocationRegistry.from_definition(rr_def_public, public_def=True)

        assert rev_reg_pub.get_receiving_tails_local_path() == TAILS_LOCAL

        rev_reg_loc = RevocationRegistry.from_definition(REV_REG_DEF, public_def=False)
        assert rev_reg_loc.get_receiving_tails_local_path() == TAILS_LOCAL

        with mock.patch.object(Path, "is_file", autospec=True) as mock_is_file:
            mock_is_file.return_value = True

            assert await rev_reg_loc.get_or_fetch_local_tails_path() == TAILS_LOCAL

        rmtree(TAILS_DIR, ignore_errors=True)
        assert not rev_reg_loc.has_local_tails_file()

    async def test_retrieve_tails(self):
        rev_reg = RevocationRegistry.from_definition(REV_REG_DEF, public_def=False)
        with self.assertRaises(RevocationError) as x_retrieve:
            await rev_reg.retrieve_tails()
            assert x_retrieve.message.contains("Tails file public URI is empty")

        rr_def_public = deepcopy(REV_REG_DEF)
        rr_def_public["value"]["tailsLocation"] = "http://sample.ca:8088/path"
        rev_reg = RevocationRegistry.from_definition(rr_def_public, public_def=True)

        with _mock_aiohttp_session(
            get_side_effect=aiohttp.ClientError("Not this time")
        ):
            with self.assertRaises(RevocationError) as x_retrieve:
                await rev_reg.retrieve_tails()
                assert x_retrieve.message.contains("Error retrieving tails file")

            rmtree(TAILS_DIR, ignore_errors=True)

        with _mock_aiohttp_session(chunks=[b"abcd1234", b""]):
            with self.assertRaises(RevocationError) as x_retrieve:
                await rev_reg.retrieve_tails()
                assert x_retrieve.message.contains(
                    "The hash of the downloaded tails file does not match."
                )

            rmtree(TAILS_DIR, ignore_errors=True)

        with (
            _mock_aiohttp_session(chunks=[b"abcd1234", b""]),
            mock.patch.object(base58, "b58encode", mock.MagicMock()) as mock_b58enc,
            mock.patch.object(Path, "is_file", autospec=True) as mock_is_file,
        ):
            mock_is_file.return_value = False

            mock_b58enc.return_value = mock.MagicMock(
                decode=mock.MagicMock(return_value=TAILS_HASH)
            )
            await rev_reg.get_or_fetch_local_tails_path()

            rmtree(TAILS_DIR, ignore_errors=True)
