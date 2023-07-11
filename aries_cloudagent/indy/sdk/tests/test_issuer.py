import json
import pytest

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from indy.error import (
    AnoncredsRevocationRegistryFullError,
    ErrorCode,
    IndyError,
    WalletItemNotFound,
)

from ....config.injection_context import InjectionContext
from ....indy.sdk.profile import IndySdkProfile
from ....indy.sdk.wallet_setup import IndyWalletConfig
from ....wallet.indy import IndySdkWallet
from ....ledger.indy import IndySdkLedgerPool

from ...issuer import IndyIssuerRevocationRegistryFullError

from .. import issuer as test_module


TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
SCHEMA_NAME = "resident"
SCHEMA_VERSION = "1.0"
SCHEMA_TXN = 1234
SCHEMA_ID = f"{TEST_DID}:2:{SCHEMA_NAME}:{SCHEMA_VERSION}"
CRED_DEF_ID = f"{TEST_DID}:3:CL:{SCHEMA_TXN}:default"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:0"
TEST_RR_DELTA = {
    "ver": "1.0",
    "value": {"prevAccum": "1 ...", "accum": "21 ...", "issued": [1, 2, 12, 42]},
}


@pytest.mark.indy
class TestIndySdkIssuer(AsyncTestCase):
    async def setUp(self):
        self.context = InjectionContext()
        self.context.injector.bind_instance(
            IndySdkLedgerPool, IndySdkLedgerPool("name")
        )

        self.wallet = await IndyWalletConfig(
            {
                "auto_recreate": True,
                "auto_remove": True,
                "key": await IndySdkWallet.generate_wallet_key(),
                "key_derivation_method": "RAW",
                "name": "test-wallet",
            }
        ).create_wallet()
        with async_mock.patch.object(IndySdkProfile, "_make_finalizer"):
            self.profile = IndySdkProfile(self.wallet, self.context)
        self.issuer = test_module.IndySdkIssuer(self.profile)

    async def tearDown(self):
        await self.profile.close()

    async def test_repr(self):
        assert "IndySdkIssuer" in str(self.issuer)  # cover __repr__

    @async_mock.patch("indy.anoncreds.issuer_create_and_store_credential_def")
    async def test_schema_cred_def(self, mock_indy_cred_def):
        assert (
            self.issuer.make_schema_id(TEST_DID, SCHEMA_NAME, SCHEMA_VERSION)
            == SCHEMA_ID
        )

        (s_id, schema_json) = await self.issuer.create_schema(
            TEST_DID,
            SCHEMA_NAME,
            SCHEMA_VERSION,
            ["name", "moniker", "genre", "effective"],
        )
        assert s_id == SCHEMA_ID
        schema = json.loads(schema_json)
        schema["seqNo"] = SCHEMA_TXN

        assert (
            self.issuer.make_credential_definition_id(TEST_DID, schema, tag="default")
            == CRED_DEF_ID
        )

        mock_indy_cred_def.return_value = (
            CRED_DEF_ID,
            json.dumps({"dummy": "cred-def"}),
        )
        assert (CRED_DEF_ID, json.dumps({"dummy": "cred-def"})) == (
            await self.issuer.create_and_store_credential_definition(
                TEST_DID, schema, support_revocation=True
            )
        )

    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    async def test_credential_definition_in_wallet(self, mock_indy_create_offer):
        mock_indy_create_offer.return_value = {"sample": "offer"}
        assert await self.issuer.credential_definition_in_wallet(CRED_DEF_ID)

    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    async def test_credential_definition_in_wallet_no(self, mock_indy_create_offer):
        mock_indy_create_offer.side_effect = WalletItemNotFound(
            error_code=ErrorCode.WalletItemNotFound
        )
        assert not await self.issuer.credential_definition_in_wallet(CRED_DEF_ID)

    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    async def test_credential_definition_in_wallet_x(self, mock_indy_create_offer):
        mock_indy_create_offer.side_effect = IndyError(
            error_code=ErrorCode.WalletInvalidHandle
        )
        with self.assertRaises(test_module.IndyIssuerError):
            await self.issuer.credential_definition_in_wallet(CRED_DEF_ID)

    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    async def test_create_credential_offer(self, mock_create_offer):
        test_offer = {"test": "offer"}
        test_cred_def_id = "test-cred-def-id"
        mock_create_offer.return_value = json.dumps(test_offer)
        mock_profile = async_mock.MagicMock()
        issuer = test_module.IndySdkIssuer(mock_profile)
        offer_json = await issuer.create_credential_offer(test_cred_def_id)
        assert json.loads(offer_json) == test_offer
        mock_create_offer.assert_called_once_with(
            mock_profile.wallet.handle, test_cred_def_id
        )

    @async_mock.patch("indy.anoncreds.issuer_create_credential")
    @async_mock.patch.object(test_module, "create_tails_reader", autospec=True)
    @async_mock.patch("indy.anoncreds.issuer_revoke_credential")
    @async_mock.patch("indy.anoncreds.issuer_merge_revocation_registry_deltas")
    async def test_create_revoke_credentials(
        self,
        mock_indy_merge_rr_deltas,
        mock_indy_revoke_credential,
        mock_tails_reader,
        mock_indy_create_credential,
    ):
        test_schema = {"attrNames": ["attr1"]}
        test_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "key_correctness_proof": {"c": "...", "xz_cap": "...", "xr_cap": ["..."]},
            "nonce": "...",
        }
        test_request = {"test": "request"}
        test_values = {"attr1": "value1"}
        test_cred = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "rev_reg_id": REV_REG_ID,
            "values": {"attr1": {"raw": "value1", "encoded": "123456123899216581404"}},
            "signature": {"...": "..."},
            "signature_correctness_proof": {"...": "..."},
            "rev_reg": {"accum": "21 12E8..."},
            "witness": {"omega": "21 1369..."},
        }
        test_cred_rev_ids = ["42", "54"]
        test_rr_delta = TEST_RR_DELTA
        mock_indy_create_credential.side_effect = [
            (
                json.dumps(test_cred),
                cr_id,
                test_rr_delta,
            )
            for cr_id in test_cred_rev_ids
        ]

        with self.assertRaises(test_module.IndyIssuerError):  # missing attribute
            cred_json, revoc_id = await self.issuer.create_credential(
                test_schema,
                test_offer,
                test_request,
                {},
            )

        (cred_json, cred_rev_id) = await self.issuer.create_credential(  # main line
            test_schema,
            test_offer,
            test_request,
            test_values,
            REV_REG_ID,
            "/tmp/tails/path/dummy",
        )
        mock_indy_create_credential.assert_called_once()
        (
            call_wallet,
            call_offer,
            call_request,
            call_values,
            call_etc1,
            call_etc2,
        ) = mock_indy_create_credential.call_args[0]
        assert call_wallet is self.wallet.handle
        assert json.loads(call_offer) == test_offer
        assert json.loads(call_request) == test_request
        values = json.loads(call_values)
        assert "attr1" in values

        mock_indy_revoke_credential.return_value = json.dumps(TEST_RR_DELTA)
        mock_indy_merge_rr_deltas.return_value = json.dumps(TEST_RR_DELTA)
        (result, failed) = await self.issuer.revoke_credentials(
            CRED_DEF_ID,
            REV_REG_ID,
            tails_file_path="dummy",
            cred_rev_ids=test_cred_rev_ids,
        )
        assert json.loads(result) == TEST_RR_DELTA
        assert not failed
        assert mock_indy_revoke_credential.call_count == 2
        mock_indy_merge_rr_deltas.assert_called_once()

    @async_mock.patch("indy.anoncreds.issuer_create_credential")
    @async_mock.patch.object(test_module, "create_tails_reader", autospec=True)
    @async_mock.patch("indy.anoncreds.issuer_revoke_credential")
    @async_mock.patch("indy.anoncreds.issuer_merge_revocation_registry_deltas")
    async def test_create_revoke_credentials_x(
        self,
        mock_indy_merge_rr_deltas,
        mock_indy_revoke_credential,
        mock_tails_reader,
        mock_indy_create_credential,
    ):
        test_schema = {"attrNames": ["attr1"]}
        test_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "key_correctness_proof": {"c": "...", "xz_cap": "...", "xr_cap": ["..."]},
            "nonce": "...",
        }
        test_request = {"test": "request"}
        test_values = {"attr1": "value1"}
        test_cred = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "rev_reg_id": REV_REG_ID,
            "values": {"attr1": {"raw": "value1", "encoded": "123456123899216581404"}},
            "signature": {"...": "..."},
            "signature_correctness_proof": {"...": "..."},
            "rev_reg": {"accum": "21 12E8..."},
            "witness": {"omega": "21 1369..."},
        }
        test_cred_rev_ids = ["42", "54", "103"]
        test_rr_delta = TEST_RR_DELTA
        mock_indy_create_credential.side_effect = [
            (
                json.dumps(test_cred),
                cr_id,
                test_rr_delta,
            )
            for cr_id in test_cred_rev_ids
        ]

        with self.assertRaises(test_module.IndyIssuerError):  # missing attribute
            cred_json, revoc_id = await self.issuer.create_credential(
                test_schema,
                test_offer,
                test_request,
                {},
            )

        (cred_json, cred_rev_id) = await self.issuer.create_credential(  # main line
            test_schema,
            test_offer,
            test_request,
            test_values,
            REV_REG_ID,
            "/tmp/tails/path/dummy",
        )
        mock_indy_create_credential.assert_called_once()
        (
            call_wallet,
            call_offer,
            call_request,
            call_values,
            call_etc1,
            call_etc2,
        ) = mock_indy_create_credential.call_args[0]
        assert call_wallet is self.wallet.handle
        assert json.loads(call_offer) == test_offer
        assert json.loads(call_request) == test_request
        values = json.loads(call_values)
        assert "attr1" in values

        def mock_revoke(_h, _t, _r, cred_rev_id):
            if cred_rev_id == "42":
                return json.dumps(TEST_RR_DELTA)
            if cred_rev_id == "54":
                raise IndyError(
                    error_code=ErrorCode.AnoncredsInvalidUserRevocId,
                    error_details={"message": "already revoked"},
                )
            raise IndyError(
                error_code=ErrorCode.UnknownCryptoTypeError,
                error_details={"message": "truly an outlier"},
            )

        mock_indy_revoke_credential.side_effect = mock_revoke
        mock_indy_merge_rr_deltas.return_value = json.dumps(TEST_RR_DELTA)
        (result, failed) = await self.issuer.revoke_credentials(
            CRED_DEF_ID,
            REV_REG_ID,
            tails_file_path="dummy",
            cred_rev_ids=test_cred_rev_ids,
        )
        assert json.loads(result) == TEST_RR_DELTA
        assert failed == ["54", "103"]
        assert mock_indy_revoke_credential.call_count == 3
        mock_indy_merge_rr_deltas.assert_not_called()

    @async_mock.patch("indy.anoncreds.issuer_create_credential")
    @async_mock.patch.object(test_module, "create_tails_reader", autospec=True)
    async def test_create_credential_rr_full(
        self,
        mock_tails_reader,
        mock_indy_create_credential,
    ):
        test_schema = {"attrNames": ["attr1"]}
        test_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "key_correctness_proof": {"c": "...", "xz_cap": "...", "xr_cap": ["..."]},
            "nonce": "...",
        }
        test_request = {"test": "request"}
        test_values = {"attr1": "value1"}
        test_credential = {"test": "credential"}
        test_cred_rev_id = "42"
        test_rr_delta = TEST_RR_DELTA
        mock_indy_create_credential.side_effect = AnoncredsRevocationRegistryFullError(
            error_code=ErrorCode.AnoncredsRevocationRegistryFullError
        )

        with self.assertRaises(IndyIssuerRevocationRegistryFullError):
            await self.issuer.create_credential(
                test_schema,
                test_offer,
                test_request,
                test_values,
            )

    @async_mock.patch("indy.anoncreds.issuer_create_credential")
    @async_mock.patch.object(test_module, "create_tails_reader", autospec=True)
    async def test_create_credential_x_indy(
        self,
        mock_tails_reader,
        mock_indy_create_credential,
    ):
        test_schema = {"attrNames": ["attr1"]}
        test_offer = {
            "schema_id": SCHEMA_ID,
            "cred_def_id": CRED_DEF_ID,
            "key_correctness_proof": {"c": "...", "xz_cap": "...", "xr_cap": ["..."]},
            "nonce": "...",
        }
        test_request = {"test": "request"}
        test_values = {"attr1": "value1"}
        test_credential = {"test": "credential"}
        test_cred_rev_id = "42"
        test_rr_delta = TEST_RR_DELTA

        mock_indy_create_credential.side_effect = IndyError(
            error_code=ErrorCode.WalletInvalidHandle
        )

        with self.assertRaises(test_module.IndyIssuerError):
            await self.issuer.create_credential(
                test_schema,
                test_offer,
                test_request,
                test_values,
            )

    @async_mock.patch("indy.anoncreds.issuer_create_and_store_revoc_reg")
    @async_mock.patch.object(test_module, "create_tails_writer", autospec=True)
    async def test_create_and_store_revocation_registry(
        self, mock_indy_tails_writer, mock_indy_rr
    ):
        mock_indy_rr.return_value = ("a", "b", "c")
        (
            rr_id,
            rrdef_json,
            rre_json,
        ) = await self.issuer.create_and_store_revocation_registry(
            TEST_DID, CRED_DEF_ID, "CL_ACCUM", "rr-tag", 100, "/tmp/tails/path"
        )
        assert (rr_id, rrdef_json, rre_json) == ("a", "b", "c")

    @async_mock.patch("indy.anoncreds.issuer_merge_revocation_registry_deltas")
    async def test_merge_revocation_registry_deltas(self, mock_indy_merge):
        mock_indy_merge.return_value = json.dumps({"net": "delta"})
        assert {"net": "delta"} == json.loads(
            await self.issuer.merge_revocation_registry_deltas(
                {"fro": "delta"}, {"to": "delta"}
            )
        )
