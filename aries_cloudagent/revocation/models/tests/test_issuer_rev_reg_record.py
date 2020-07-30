import json

from os.path import join

import indy.anoncreds
import indy.blob_storage

import pytest

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ....config.injection_context import InjectionContext
from ....indy.util import indy_client_dir
from ....issuer.base import BaseIssuer, IssuerError
from ....issuer.indy import IndyIssuer
from ....ledger.base import BaseLedger
from ....storage.base import BaseStorage
from ....storage.basic import BasicStorage
from ....wallet.base import BaseWallet, DIDInfo

from ...error import RevocationError

from ..issuer_rev_reg_record import IssuerRevRegRecord
from ..revocation_registry import RevocationRegistry
from .. import issuer_rev_reg_record as test_module


class TestRecord(AsyncTestCase):
    test_did = "55GkHamhTU1ZbTbV2ab9DE"

    def setUp(self):
        self.context = InjectionContext(enforce_typing=False)

        self.wallet = async_mock.MagicMock()
        self.wallet.type = "indy"
        self.context.injector.bind_instance(BaseWallet, self.wallet)

        Ledger = async_mock.MagicMock(BaseLedger, autospec=True)
        self.ledger = Ledger()
        self.ledger.send_revoc_reg_def = async_mock.CoroutineMock()
        self.ledger.send_revoc_reg_entry = async_mock.CoroutineMock()
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        self.storage = BasicStorage()
        self.context.injector.bind_instance(BaseStorage, self.storage)

    async def test_generate_registry_etc(self):
        CRED_DEF_ID = f"{TestRecord.test_did}:3:CL:1234:default"
        REV_REG_ID = f"{TestRecord.test_did}:4:{CRED_DEF_ID}:CL_ACCUM:0"

        rec = IssuerRevRegRecord(
            issuer_did=TestRecord.test_did,
            cred_def_id=CRED_DEF_ID,
            revoc_reg_id=REV_REG_ID,
        )
        issuer = async_mock.MagicMock(BaseIssuer)
        self.context.injector.bind_instance(BaseIssuer, issuer)

        with async_mock.patch.object(
            issuer, "create_and_store_revocation_registry", async_mock.CoroutineMock()
        ) as mock_create_store_rr:
            mock_create_store_rr.side_effect = IssuerError("Not this time")

            with self.assertRaises(RevocationError):
                await rec.generate_registry(self.context)

        issuer.create_and_store_revocation_registry.return_value = (
            REV_REG_ID,
            json.dumps(
                {
                    "value": {
                        "tailsHash": "59NY25UEV8a5CzNkXFQMppwofUxtYtf4FDp1h9xgeLcK",
                        "tailsLocation": "point at infinity",
                    }
                }
            ),
            json.dumps({"revoc_reg_entry": "dummy-entry"}),
        )

        with async_mock.patch.object(
            test_module, "move", async_mock.MagicMock()
        ) as mock_move:
            await rec.generate_registry(self.context)

        assert rec.revoc_reg_id == REV_REG_ID
        assert rec.state == IssuerRevRegRecord.STATE_GENERATED
        assert rec.tails_hash == "59NY25UEV8a5CzNkXFQMppwofUxtYtf4FDp1h9xgeLcK"
        assert rec.tails_local_path == join(
            indy_client_dir(join("tails", REV_REG_ID)), rec.tails_hash
        )
        with self.assertRaises(RevocationError):
            await rec.set_tails_file_public_uri(self.context, "dummy")

        await rec.set_tails_file_public_uri(self.context, "http://localhost/dummy")
        assert rec.tails_public_uri == "http://localhost/dummy"
        assert rec.revoc_reg_def["value"]["tailsLocation"] == "http://localhost/dummy"

        ledger = await self.context.inject(BaseLedger)
        await rec.publish_registry_definition(self.context)
        assert rec.state == IssuerRevRegRecord.STATE_PUBLISHED
        ledger.send_revoc_reg_def.assert_called_once()

        await rec.publish_registry_entry(self.context)
        assert rec.state == IssuerRevRegRecord.STATE_ACTIVE
        ledger.send_revoc_reg_entry.assert_called_once()

        rev_reg = await rec.get_registry()
        assert type(rev_reg) == RevocationRegistry

        queried = await IssuerRevRegRecord.query_by_cred_def_id(
            context=self.context,
            cred_def_id=CRED_DEF_ID,
            state=IssuerRevRegRecord.STATE_ACTIVE,
        )
        assert len(queried) == 1

        retrieved = await IssuerRevRegRecord.retrieve_by_revoc_reg_id(
            context=self.context, revoc_reg_id=rec.revoc_reg_id
        )
        assert retrieved.revoc_reg_id == rec.revoc_reg_id

        await rec.mark_full(self.context)
        assert rec.state == IssuerRevRegRecord.STATE_FULL

        data = rec.serialize()
        model_instance = IssuerRevRegRecord.deserialize(data)
        assert isinstance(model_instance, IssuerRevRegRecord)
        assert model_instance == rec

    async def test_operate_on_full_record(self):
        CRED_DEF_ID = f"{TestRecord.test_did}:3:CL:1234:default"
        REV_REG_ID = f"{TestRecord.test_did}:4:{CRED_DEF_ID}:CL_ACCUM:0"

        rec_full = IssuerRevRegRecord(
            issuer_did=TestRecord.test_did,
            revoc_reg_id=REV_REG_ID,
            revoc_reg_def={"sample": "rr-def"},
            revoc_def_type="CL_ACCUM",
            revoc_reg_entry={"sample": "rr-ent"},
            cred_def_id=CRED_DEF_ID,
            state=IssuerRevRegRecord.STATE_FULL,
            tails_public_uri="http://localhost/dummy/path",
        )

        with self.assertRaises(RevocationError) as x_state:
            await rec_full.generate_registry(self.context)

        with self.assertRaises(RevocationError) as x_state:
            await rec_full.publish_registry_definition(self.context)

        rec_full.state = IssuerRevRegRecord.STATE_INIT
        with self.assertRaises(RevocationError) as x_state:
            await rec_full.publish_registry_entry(self.context)

    async def test_pending(self):
        rec = IssuerRevRegRecord()
        await rec.mark_pending(self.context, "1")
        await rec.mark_pending(self.context, "2")
        await rec.mark_pending(self.context, "3")
        await rec.mark_pending(self.context, "4")

        found = await IssuerRevRegRecord.query_by_pending(self.context)
        assert len(found) == 1 and found[0] == rec

        await rec.clear_pending(self.context, ["1", "2"])
        assert rec.pending_pub == ["3", "4"]
        found = await IssuerRevRegRecord.query_by_pending(self.context)
        assert found

        await rec.clear_pending(self.context, [])
        assert rec.pending_pub == []
        found = await IssuerRevRegRecord.query_by_pending(self.context)
        assert not found

        await rec.mark_pending(self.context, "5")
        await rec.mark_pending(self.context, "6")

        await rec.clear_pending(self.context, [])
        assert rec.pending_pub == []
        found = await IssuerRevRegRecord.query_by_pending(self.context)
        assert not found

    async def test_set_tails_file_public_uri_rev_reg_undef(self):
        rec = IssuerRevRegRecord()
        with self.assertRaises(RevocationError):
            await rec.set_tails_file_public_uri(self.context, "dummy")

    async def test_publish_rev_reg_undef(self):
        rec = IssuerRevRegRecord()
        with self.assertRaises(RevocationError):
            await rec.publish_registry_definition(self.context)

        with self.assertRaises(RevocationError):
            await rec.publish_registry_entry(self.context)
