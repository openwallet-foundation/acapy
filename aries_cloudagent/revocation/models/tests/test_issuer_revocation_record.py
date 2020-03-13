import json

import indy.anoncreds
import indy.blob_storage

import pytest

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ....config.injection_context import InjectionContext
from ....issuer.base import BaseIssuer
from ....issuer.indy import IndyIssuer
from ....ledger.base import BaseLedger
from ....storage.base import BaseStorage
from ....storage.basic import BasicStorage
from ....wallet.base import BaseWallet, DIDInfo

from ...error import RevocationError

from ..issuer_revocation_record import IssuerRevocationRecord
from ..revocation_registry import RevocationRegistry


class TestRecord(AsyncTestCase):
    test_did = "55GkHamhTU1ZbTbV2ab9DE"

    def setUp(self):
        self.context = InjectionContext(enforce_typing=False)

        self.wallet = async_mock.MagicMock()
        self.wallet.WALLET_TYPE = "indy"
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

        rec = IssuerRevocationRecord(
            issuer_did=TestRecord.test_did, cred_def_id=CRED_DEF_ID
        )
        issuer = async_mock.MagicMock(BaseIssuer)
        self.context.injector.bind_instance(BaseIssuer, issuer)

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

        await rec.generate_registry(self.context, None)

        assert rec.revoc_reg_id == REV_REG_ID
        assert rec.state == IssuerRevocationRecord.STATE_GENERATED
        assert rec.tails_hash == "59NY25UEV8a5CzNkXFQMppwofUxtYtf4FDp1h9xgeLcK"
        assert rec.tails_local_path == "point at infinity"

        rec.set_tails_file_public_uri("dummy")
        assert rec.tails_public_uri == "dummy"
        assert rec.revoc_reg_def["value"]["tailsLocation"] == "dummy"

        ledger = await self.context.inject(BaseLedger)
        await rec.publish_registry_definition(self.context)
        ledger.send_revoc_reg_def.assert_called_once()

        await rec.publish_registry_entry(self.context)
        ledger.send_revoc_reg_entry.assert_called_once()

        rev_reg = await rec.get_registry()
        assert type(rev_reg) == RevocationRegistry

        queried = await IssuerRevocationRecord.query_by_cred_def_id(
            context=self.context,
            cred_def_id=CRED_DEF_ID,
            state=IssuerRevocationRecord.STATE_GENERATED,
        )
        assert len(queried) == 1

        retrieved = await IssuerRevocationRecord.retrieve_by_revoc_reg_id(
            context=self.context, revoc_reg_id=rec.revoc_reg_id
        )
        assert retrieved.revoc_reg_id == rec.revoc_reg_id

        await rec.mark_full(self.context)
        assert rec.state == IssuerRevocationRecord.STATE_FULL

        data = rec.serialize()
        model_instance = IssuerRevocationRecord.deserialize(data)
        assert isinstance(model_instance, IssuerRevocationRecord)
        assert model_instance == rec

    # async def test_generate_registry_not_indy_wallet(self):
    #     self.wallet = async_mock.MagicMock()
    #     self.wallet.WALLET_TYPE = "not-indy"
    #     self.context.injector.clear_binding(BaseWallet)
    #     self.context.injector.bind_instance(BaseWallet, self.wallet)
    #     issuer = IndyIssuer(self.wallet)
    #     self.context.injector.bind_instance(BaseIssuer, issuer)

    #     rec = IssuerRevocationRecord()
    #     with self.assertRaises(RevocationError):
    #         await rec.generate_registry(self.context, ".")

    async def test_set_tails_file_public_uri_rev_reg_undef(self):
        rec = IssuerRevocationRecord()
        with self.assertRaises(RevocationError):
            rec.set_tails_file_public_uri("dummy")

    async def test_publish_rev_reg_undef(self):
        rec = IssuerRevocationRecord()
        with self.assertRaises(RevocationError):
            await rec.publish_registry_definition(self.context)

        with self.assertRaises(RevocationError):
            await rec.publish_registry_entry(self.context)

