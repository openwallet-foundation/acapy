import json
import tempfile
import pytest

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ....askar.profile import AskarProfileManager
from ....config.injection_context import InjectionContext
from ....ledger.base import BaseLedger
from ....ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)

from .. import issuer, holder, verifier


TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
SCHEMA_NAME = "resident"
SCHEMA_VERSION = "1.0"
SCHEMA_TXN = 1234
SCHEMA_ID = f"{TEST_DID}:2:{SCHEMA_NAME}:{SCHEMA_VERSION}"
CRED_DEF_ID = f"{TEST_DID}:3:CL:{SCHEMA_TXN}:default"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:0"
CRED_REFT = "attr_0_uuid"
PRES_REQ_NON_REV = {
    "name": "pres-request",
    "version": "1.0",
    "nonce": "1234567890",
    "requested_attributes": {CRED_REFT: {"names": ["name", "moniker"]}},
    "requested_predicates": {},
}
TIMESTAMP = 99999
PRES_REQ_REV = {
    "name": "pres-request",
    "version": "1.0",
    "nonce": "1234567890",
    "requested_attributes": {CRED_REFT: {"names": ["name", "moniker"]}},
    "requested_predicates": {},
    "non_revoked": {"to": TIMESTAMP},
}


@pytest.mark.askar
@pytest.mark.indy_credx
class TestIndyCredxIssuance(AsyncTestCase):
    async def setUp(self):
        context = InjectionContext(enforce_typing=False)
        mock_ledger = async_mock.MagicMock(
            get_credential_definition=async_mock.CoroutineMock(
                return_value={"value": {}}
            ),
            get_revoc_reg_delta=async_mock.CoroutineMock(
                return_value=(
                    {"value": {"...": "..."}},
                    1234567890,
                )
            ),
        )
        mock_ledger.__aenter__ = async_mock.CoroutineMock(return_value=mock_ledger)
        self.ledger = mock_ledger

        self.holder_profile = await AskarProfileManager().provision(
            context,
            {
                "name": ":memory:",
                "key": await AskarProfileManager.generate_store_key(),
                "key_derivation_method": "RAW",
            },
        )
        self.issuer_profile = await AskarProfileManager().provision(
            context,
            {
                "name": ":memory:",
                "key": await AskarProfileManager.generate_store_key(),
                "key_derivation_method": "RAW",
            },
        )
        self.issuer_profile._context.injector.bind_instance(BaseLedger, mock_ledger)
        self.issuer_profile._context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.CoroutineMock(
                    return_value=(None, mock_ledger)
                )
            ),
        )

        self.holder = holder.IndyCredxHolder(self.holder_profile)
        self.issuer = issuer.IndyCredxIssuer(self.issuer_profile)
        self.verifier = verifier.IndyCredxVerifier(self.issuer_profile)
        assert "IndyCredxHolder" in str(self.holder)
        assert "IndyCredxIssuer" in str(self.issuer)
        assert "IndyCredxVerifier" in str(self.verifier)

    async def test_issue_store_non_rev(self):
        assert (
            self.issuer.make_schema_id(TEST_DID, SCHEMA_NAME, SCHEMA_VERSION)
            == SCHEMA_ID
        )

        (s_id, schema_json) = await self.issuer.create_schema(
            TEST_DID,
            SCHEMA_NAME,
            SCHEMA_VERSION,
            ["name", "moniker"],
        )
        assert s_id == SCHEMA_ID
        schema = json.loads(schema_json)
        schema["seqNo"] = SCHEMA_TXN

        assert (
            self.issuer.make_credential_definition_id(TEST_DID, schema, tag="default")
            == CRED_DEF_ID
        )

        (
            cd_id,
            cred_def_json,
        ) = await self.issuer.create_and_store_credential_definition(
            TEST_DID, schema, support_revocation=False
        )
        assert cd_id == CRED_DEF_ID
        assert await self.issuer.credential_definition_in_wallet(cd_id)
        cred_def = json.loads(cred_def_json)

        cred_offer_json = await self.issuer.create_credential_offer(cd_id)
        cred_offer = json.loads(cred_offer_json)

        cred_req_json, cred_req_meta_json = await self.holder.create_credential_request(
            cred_offer, cred_def, TEST_DID
        )
        cred_req = json.loads(cred_req_json)
        cred_req_meta = json.loads(cred_req_meta_json)

        cred_json, cred_rev_id = await self.issuer.create_credential(
            schema,
            cred_offer,
            cred_req,
            {"name": "NAME", "moniker": "MONIKER"},
            revoc_reg_id=None,
            tails_file_path=None,
        )
        assert cred_rev_id is None
        cred_data = json.loads(cred_json)

        cred_id = await self.holder.store_credential(cred_def, cred_data, cred_req_meta)

        found = await self.holder.get_credential(cred_id)
        assert found
        stored_cred = json.loads(found)

        assert not await self.holder.get_mime_type(cred_id, "name")

        creds = await self.holder.get_credentials(None, None, None)
        assert len(creds) == 1
        assert creds[0] == stored_cred

        assert not await self.holder.credential_revoked(self.ledger, cred_id)

        pres_creds = (
            await self.holder.get_credentials_for_presentation_request_by_referent(
                PRES_REQ_NON_REV,
                None,
                0,
                10,
                {},
            )
        )
        assert pres_creds == [
            {
                "cred_info": stored_cred,
                "interval": None,
                "presentation_referents": [CRED_REFT],
            }
        ]

        pres_json = await self.holder.create_presentation(
            PRES_REQ_NON_REV,
            {
                "requested_attributes": {
                    CRED_REFT: {"cred_id": cred_id, "revealed": True}
                }
            },
            {s_id: schema},
            {cd_id: cred_def},
            rev_states=None,
        )
        pres = json.loads(pres_json)

        assert await self.verifier.verify_presentation(
            PRES_REQ_NON_REV, pres, {s_id: schema}, {cd_id: cred_def}, {}, {}
        )

        await self.holder.delete_credential(cred_id)

    async def test_issue_store_rev(self):
        assert (
            self.issuer.make_schema_id(TEST_DID, SCHEMA_NAME, SCHEMA_VERSION)
            == SCHEMA_ID
        )

        (s_id, schema_json) = await self.issuer.create_schema(
            TEST_DID,
            SCHEMA_NAME,
            SCHEMA_VERSION,
            ["name", "moniker"],
        )
        assert s_id == SCHEMA_ID
        schema = json.loads(schema_json)
        schema["seqNo"] = SCHEMA_TXN

        assert (
            self.issuer.make_credential_definition_id(TEST_DID, schema, tag="default")
            == CRED_DEF_ID
        )

        (
            cd_id,
            cred_def_json,
        ) = await self.issuer.create_and_store_credential_definition(
            TEST_DID, schema, support_revocation=True
        )
        assert cd_id == CRED_DEF_ID
        cred_def = json.loads(cred_def_json)
        self.ledger.get_credential_definition.return_value = cred_def

        with tempfile.TemporaryDirectory() as tmp_path:
            (
                reg_id,
                reg_def_json,
                reg_entry_json,
            ) = await self.issuer.create_and_store_revocation_registry(
                TEST_DID, cd_id, "CL_ACCUM", "0", 10, tmp_path
            )
            assert reg_id == REV_REG_ID
            reg_def = json.loads(reg_def_json)
            reg_entry = json.loads(reg_entry_json)
            tails_path = reg_def["value"]["tailsLocation"]

            cred_offer_json = await self.issuer.create_credential_offer(cd_id)
            cred_offer = json.loads(cred_offer_json)

            (
                cred_req_json,
                cred_req_meta_json,
            ) = await self.holder.create_credential_request(
                cred_offer, cred_def, TEST_DID
            )
            cred_req = json.loads(cred_req_json)
            cred_req_meta = json.loads(cred_req_meta_json)

            cred_json, cred_rev_id = await self.issuer.create_credential(
                schema,
                cred_offer,
                cred_req,
                {"name": "NAME", "moniker": "MONIKER"},
                revoc_reg_id=reg_id,
                tails_file_path=tails_path,
            )
            assert cred_rev_id == "1"
            cred_data = json.loads(cred_json)

            cred_id = await self.holder.store_credential(
                cred_def,
                cred_data,
                cred_req_meta,
                rev_reg_def=reg_def,
            )

            found = await self.holder.get_credential(cred_id)
            assert found
            stored_cred = json.loads(found)

            creds = await self.holder.get_credentials(None, None, None)
            assert len(creds) == 1
            assert creds[0] == stored_cred

            assert not await self.holder.credential_revoked(self.ledger, cred_id)

            pres_creds = (
                await self.holder.get_credentials_for_presentation_request_by_referent(
                    PRES_REQ_REV,
                    None,
                    0,
                    10,
                    {},
                )
            )
            assert pres_creds == [
                {
                    "cred_info": stored_cred,
                    "interval": {"to": TIMESTAMP},
                    "presentation_referents": [CRED_REFT],
                }
            ]

            rev_state_time = 1
            rev_state_json = await self.holder.create_revocation_state(
                cred_rev_id, reg_def, reg_entry, rev_state_time, tails_path
            )
            rev_state_init = json.loads(rev_state_json)
            rev_delta_init = {"ver": "1.0", "value": rev_state_init["rev_reg"]}

            (rev_delta_2_json, skipped_ids) = await self.issuer.revoke_credentials(
                cd_id, reg_id, tails_path, (1,)
            )
            assert not skipped_ids
            rev_delta_2 = json.loads(rev_delta_2_json)

            merged = await self.issuer.merge_revocation_registry_deltas(
                rev_delta_init, rev_delta_2
            )

        pres_json = await self.holder.create_presentation(
            PRES_REQ_REV,
            {
                "requested_attributes": {
                    CRED_REFT: {
                        "cred_id": cred_id,
                        "revealed": True,
                        "timestamp": rev_state_time,
                    }
                }
            },
            {s_id: schema},
            {cd_id: cred_def},
            rev_states={reg_id: {rev_state_time: rev_state_init}},
        )
        pres = json.loads(pres_json)

        reg_def["txnTime"] = rev_state_time
        assert await self.verifier.verify_presentation(
            PRES_REQ_REV,
            pres,
            {s_id: schema},
            {cd_id: cred_def},
            {reg_id: reg_def},
            {reg_id: {rev_state_time: rev_delta_init}},
        )

        await self.holder.delete_credential(cred_id)
