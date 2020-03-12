import json

import indy.anoncreds
import indy.blob_storage

import pytest

from asynctest import TestCase as AsyncTestCase, mock as async_mock
from copy import deepcopy
from os import makedirs
from pathlib import Path
from shutil import rmtree

import base58

from ....config.injection_context import InjectionContext
from ....storage.base import BaseStorage
from ....storage.basic import BasicStorage

from ...error import RevocationError

from ..issuer_revocation_record import IssuerRevocationRecord
from ..revocation_registry import RevocationRegistry

from .. import revocation_registry as test_module


TEST_DID = "FkjWznKwA4N1JEp2iPiKPG"
CRED_DEF_ID = f"{TEST_DID}:3:CL:12:tag1"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:tag1",
TAILS_DIR = "/tmp/indy/revocation/tails_files"
TAILS_HASH = "8UW1Sz5cqoUnK9hqQk7nvtKK65t7Chu3ui866J23sFyJ"
TAILS_LOCAL = f"{TAILS_DIR}/{TAILS_HASH}"
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
        "tailsLocation": TAILS_LOCAL
    }
}


class TestRevocationRegistry(AsyncTestCase):

    def setUp(self):
        self.context = InjectionContext(
            settings={
                "holder.revocation.tails_files.path": TAILS_DIR
            },
            enforce_typing=False
        )

        self.storage = BasicStorage()
        self.context.injector.bind_instance(BaseStorage, self.storage)

    def tearDown(self):
        rmtree(TAILS_DIR, ignore_errors=True)

    async def test_init(self):
        rev_reg = RevocationRegistry()
        assert str(rev_reg).startswith("<RevocationRegistry")

        for public in (True, False):
            rev_reg = RevocationRegistry.from_definition(
                REV_REG_DEF,
                public_def=public
            )
            if public:
                assert not rev_reg.tails_local_path
                assert rev_reg.tails_public_uri
            else:
                assert rev_reg.tails_local_path
                assert not rev_reg.tails_public_uri

    async def test_temp_dir(self):
        assert RevocationRegistry.get_temp_dir()

    async def test_properties(self):
        rev_reg = RevocationRegistry.from_definition(
            REV_REG_DEF,
            public_def=False
        )

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

    async def test_tails_reader(self):
        makedirs(TAILS_DIR, exist_ok=True)
        with open(TAILS_LOCAL, "a") as f:
            print("1234123412431234", file=f)

        rev_reg = RevocationRegistry.from_definition(
            REV_REG_DEF,
            public_def=False
        )

        with async_mock.patch.object(
            indy.blob_storage, "open_reader", async_mock.CoroutineMock()
        ) as mock_blob_open_reader:
            result = await rev_reg.create_tails_reader(self.context)
            assert result == mock_blob_open_reader.return_value
            assert rev_reg.has_local_tails_file(self.context)

        rmtree(TAILS_DIR, ignore_errors=True)
        with self.assertRaises(FileNotFoundError):
            await rev_reg.create_tails_reader(self.context)

    async def test_tails_local_path(self):
        rr_def_public = deepcopy(REV_REG_DEF)
        rr_def_public["value"]["tailsLocation"] = "http://sample.ca:8088/path"
        rev_reg = RevocationRegistry.from_definition(
            rr_def_public,
            public_def=True
        )

        assert rev_reg.get_receiving_tails_local_path(self.context) == TAILS_LOCAL

    async def test_retrieve_tails(self):
        rev_reg = RevocationRegistry.from_definition(
            REV_REG_DEF,
            public_def=False
        )
        with self.assertRaises(RevocationError) as x_retrieve:
            await rev_reg.retrieve_tails(self.context)
            assert x_retrieve.message.contains("Tails file public URI is empty")

        rr_def_public = deepcopy(REV_REG_DEF)
        rr_def_public["value"]["tailsLocation"] = "http://sample.ca:8088/path"
        rev_reg = RevocationRegistry.from_definition(
            rr_def_public,
            public_def=True
        )

        with async_mock.patch.object(
            test_module, "fetch_stream", async_mock.CoroutineMock()
        ) as mock_fetch:
            mock_fetch.side_effect = test_module.FetchError()

            with self.assertRaises(RevocationError) as x_retrieve:
                await rev_reg.retrieve_tails(self.context)
                assert x_retrieve.message.contains("Error retrieving tails file")

        rmtree(TAILS_DIR, ignore_errors=True)

        with async_mock.patch.object(
            test_module, "fetch_stream", async_mock.CoroutineMock()
        ) as mock_fetch:
            mock_fetch.return_value = async_mock.CoroutineMock(
                read=async_mock.CoroutineMock(
                    side_effect=[
                        b"abcd1234",
                        b""
                    ]
                )
            )
            with self.assertRaises(RevocationError) as x_retrieve:
                await rev_reg.retrieve_tails(self.context)
                assert x_retrieve.message.contains(
                    "The has of the downloaded tails file does not match."
                )

        with async_mock.patch.object(
            test_module, "fetch_stream", async_mock.CoroutineMock()
        ) as mock_fetch, async_mock.patch.object(
            base58, "b58encode", async_mock.MagicMock()
        ) as mock_b58enc:
            mock_fetch.return_value = async_mock.CoroutineMock(
                read=async_mock.CoroutineMock(
                    side_effect=[
                        b"abcd1234",
                        b""
                    ]
                )
            )
            mock_b58enc.return_value = async_mock.MagicMock(
                decode=async_mock.MagicMock(
                    return_value=TAILS_HASH
                )
            )
            await rev_reg.retrieve_tails(self.context)
            assert Path(TAILS_LOCAL).is_file()

    async def test_create_revocation_state(self):
        rev_reg = RevocationRegistry.from_definition(
            REV_REG_DEF,
            public_def=False
        )
        rr_state = {
            "witness": {
                "omega": "1 ..."
            },
            "rev_reg": {
                "accum": "21 ..."
            },
            "timestamp": 1234567890
        }

        with async_mock.patch.object(
            rev_reg, "create_tails_reader", async_mock.CoroutineMock()
        ) as mock_create_tails_reader, async_mock.patch.object(
            indy.anoncreds, "create_revocation_state", async_mock.CoroutineMock()
        ) as mock_create_rr_state:
            mock_create_rr_state.return_value = json.dumps(rr_state)

            result = await rev_reg.create_revocation_state(
                self.context,
                None,
                None,
                None
            )
            assert result == rr_state
