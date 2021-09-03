from aries_cloudagent.ledger.base import BaseLedger
import json
import pytest

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ....askar.profile import AskarProfileManager
from ....config.injection_context import InjectionContext
from ....ledger.base import BaseLedger

from .. import issuer, holder, verifier


TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
SCHEMA_NAME = "resident"
SCHEMA_VERSION = "1.0"
SCHEMA_TXN = 1234
SCHEMA_ID = f"{TEST_DID}:2:{SCHEMA_NAME}:{SCHEMA_VERSION}"
CRED_DEF_ID = f"{TEST_DID}:3:CL:{SCHEMA_TXN}:default"
# REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:0"
CRED_REFT = "attr_0_uuid"
PRES_REQ = {
    "name": "pres-request",
    "version": "1.0",
    "nonce": "1234567890",
    "requested_attributes": {CRED_REFT: {"names": ["name", "moniker"]}},
    "requested_predicates": {},
}


@pytest.mark.indy_credx
class TestIndyCredxIssuerHolder(AsyncTestCase):
    async def setUp(self):
        context = InjectionContext(enforce_typing=False)
        mock_ledger = async_mock.MagicMock(
            get_credential_definition=async_mock.MagicMock(return_value={"value": {}}),
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
            "cred_ex_id",
            revoc_reg_id=None,
            tails_file_path=None,
        )
        assert cred_rev_id is None
        cred_data = json.loads(cred_json)

        cred_id = await self.holder.store_credential(cred_def, cred_data, cred_req_meta)

        found = await self.holder.get_credential(cred_id)
        assert found
        stored_cred = json.loads(found)

        creds = await self.holder.get_credentials(None, None, None)
        assert len(creds) == 1
        assert creds[0] == stored_cred

        assert not await self.holder.credential_revoked(self.ledger, cred_id)

        pres_creds = (
            await self.holder.get_credentials_for_presentation_request_by_referent(
                PRES_REQ,
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
            PRES_REQ,
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
            PRES_REQ, pres, {s_id: schema}, {cd_id: cred_def}, {}, {}
        )

        await self.holder.delete_credential(cred_id)
