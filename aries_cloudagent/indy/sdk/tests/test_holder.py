import json

import pytest

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

import indy.anoncreds
from indy.error import IndyError, ErrorCode

from ....storage.error import StorageError
from ....storage.record import StorageRecord
from ....protocols.issue_credential.v1_0.messages.inner.credential_preview import (
    CredentialPreview,
)

from ...holder import IndyHolder

from .. import holder as test_module


@pytest.mark.indy
class TestIndySdkHolder(AsyncTestCase):
    def test_init(self):
        holder = test_module.IndySdkHolder("wallet")
        assert holder.wallet == "wallet"
        assert "IndySdkHolder" in str(holder)

    @async_mock.patch("indy.anoncreds.prover_create_credential_req")
    async def test_create_credential_request(self, mock_create_credential_req):
        mock_create_credential_req.return_value = ("{}", "[]")
        mock_wallet = async_mock.MagicMock()

        holder = test_module.IndySdkHolder(mock_wallet)
        cred_req_json, cred_req_meta_json = await holder.create_credential_request(
            "credential_offer", "credential_definition", "did"
        )

        mock_create_credential_req.assert_called_once_with(
            mock_wallet.handle,
            "did",
            json.dumps("credential_offer"),
            json.dumps("credential_definition"),
            mock_wallet.master_secret_id,
        )

        assert (json.loads(cred_req_json), json.loads(cred_req_meta_json)) == ({}, [])

    @async_mock.patch("indy.anoncreds.prover_store_credential")
    async def test_store_credential(self, mock_store_cred):
        mock_store_cred.return_value = "cred_id"
        mock_wallet = async_mock.MagicMock()

        holder = test_module.IndySdkHolder(mock_wallet)

        cred_id = await holder.store_credential(
            "credential_definition", "credential_data", "credential_request_metadata"
        )

        mock_store_cred.assert_called_once_with(
            wallet_handle=mock_wallet.handle,
            cred_id=None,
            cred_req_metadata_json=json.dumps("credential_request_metadata"),
            cred_json=json.dumps("credential_data"),
            cred_def_json=json.dumps("credential_definition"),
            rev_reg_def_json=None,
        )

        assert cred_id == "cred_id"

    @async_mock.patch("indy.anoncreds.prover_store_credential")
    async def test_store_credential_with_mime_types(self, mock_store_cred):
        with async_mock.patch.object(
            test_module, "IndySdkStorage", async_mock.MagicMock()
        ) as mock_storage:
            mock_storage.return_value = async_mock.MagicMock(
                add_record=async_mock.CoroutineMock()
            )

            mock_store_cred.return_value = "cred_id"
            mock_wallet = async_mock.MagicMock()

            holder = test_module.IndySdkHolder(mock_wallet)

            CRED_DATA = {"values": {"cameo": "d29yZCB1cA=="}}
            cred_id = await holder.store_credential(
                "credential_definition",
                CRED_DATA,
                "credential_request_metadata",
                {"cameo": "image/png"},
            )

            mock_store_cred.assert_called_once_with(
                wallet_handle=mock_wallet.handle,
                cred_id=None,
                cred_req_metadata_json=json.dumps("credential_request_metadata"),
                cred_json=json.dumps(CRED_DATA),
                cred_def_json=json.dumps("credential_definition"),
                rev_reg_def_json=None,
            )
            mock_storage.return_value.add_record.assert_called_once()

            assert cred_id == "cred_id"

    @async_mock.patch("indy.non_secrets.get_wallet_record")
    async def test_get_credential_attrs_mime_types(self, mock_nonsec_get_wallet_record):
        cred_id = "credential_id"
        dummy_tags = {"a": "1", "b": "2"}
        dummy_rec = {
            "type": IndyHolder.RECORD_TYPE_MIME_TYPES,
            "id": cred_id,
            "value": "value",
            "tags": dummy_tags,
        }
        mock_nonsec_get_wallet_record.return_value = json.dumps(dummy_rec)

        mock_wallet = async_mock.MagicMock()

        holder = test_module.IndySdkHolder(mock_wallet)

        mime_types = await holder.get_mime_type(cred_id)

        mock_nonsec_get_wallet_record.assert_called_once_with(
            mock_wallet.handle,
            dummy_rec["type"],
            f"{IndyHolder.RECORD_TYPE_MIME_TYPES}::{dummy_rec['id']}",
            json.dumps(
                {"retrieveType": False, "retrieveValue": True, "retrieveTags": True}
            ),
        )

        assert mime_types == dummy_tags

    @async_mock.patch("indy.non_secrets.get_wallet_record")
    async def test_get_credential_attr_mime_type(self, mock_nonsec_get_wallet_record):
        cred_id = "credential_id"
        dummy_tags = {"a": "1", "b": "2"}
        dummy_rec = {
            "type": IndyHolder.RECORD_TYPE_MIME_TYPES,
            "id": cred_id,
            "value": "value",
            "tags": dummy_tags,
        }
        mock_nonsec_get_wallet_record.return_value = json.dumps(dummy_rec)

        mock_wallet = async_mock.MagicMock()

        holder = test_module.IndySdkHolder(mock_wallet)

        a_mime_type = await holder.get_mime_type(cred_id, "a")

        mock_nonsec_get_wallet_record.assert_called_once_with(
            mock_wallet.handle,
            dummy_rec["type"],
            f"{IndyHolder.RECORD_TYPE_MIME_TYPES}::{dummy_rec['id']}",
            json.dumps(
                {"retrieveType": False, "retrieveValue": True, "retrieveTags": True}
            ),
        )

        assert a_mime_type == dummy_tags["a"]

    @async_mock.patch("indy.non_secrets.get_wallet_record")
    async def test_get_credential_attr_mime_type_x(self, mock_nonsec_get_wallet_record):
        cred_id = "credential_id"
        dummy_tags = {"a": "1", "b": "2"}
        dummy_rec = {
            "type": IndyHolder.RECORD_TYPE_MIME_TYPES,
            "id": cred_id,
            "value": "value",
            "tags": dummy_tags,
        }
        mock_nonsec_get_wallet_record.side_effect = test_module.StorageError()
        mock_wallet = async_mock.MagicMock()

        holder = test_module.IndySdkHolder(mock_wallet)

        assert await holder.get_mime_type(cred_id, "a") is None

    @async_mock.patch("indy.anoncreds.prover_search_credentials")
    @async_mock.patch("indy.anoncreds.prover_fetch_credentials")
    @async_mock.patch("indy.anoncreds.prover_close_credentials_search")
    async def test_get_credentials(
        self, mock_close_cred_search, mock_fetch_credentials, mock_search_credentials
    ):
        SIZE = 300
        mock_search_credentials.return_value = ("search_handle", 350)
        mock_fetch_credentials.side_effect = [
            json.dumps([0] * test_module.IndySdkHolder.CHUNK),
            json.dumps([1] * (SIZE % test_module.IndySdkHolder.CHUNK)),
        ]

        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)

        credentials = await holder.get_credentials(0, SIZE, {})

        mock_search_credentials.assert_called_once_with(
            mock_wallet.handle, json.dumps({})
        )

        assert mock_fetch_credentials.call_count == 2
        mock_close_cred_search.assert_called_once_with("search_handle")

        assert len(credentials) == SIZE

        mock_fetch_credentials.side_effect = [
            json.dumps([0] * test_module.IndySdkHolder.CHUNK),
            json.dumps([1] * (SIZE % test_module.IndySdkHolder.CHUNK)),
        ]
        credentials = await holder.get_credentials(0, 0, {})  # check 0 default to all
        assert len(credentials) == SIZE

    @async_mock.patch("indy.anoncreds.prover_search_credentials")
    @async_mock.patch("indy.anoncreds.prover_fetch_credentials")
    @async_mock.patch("indy.anoncreds.prover_close_credentials_search")
    async def test_get_credentials_seek(
        self, mock_close_cred_search, mock_fetch_credentials, mock_search_credentials
    ):
        mock_search_credentials.return_value = ("search_handle", 3)
        mock_fetch_credentials.return_value = "[1,2,3]"

        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)

        credentials = await holder.get_credentials(2, 3, {})

        assert mock_fetch_credentials.call_args_list == [
            (("search_handle", 2),),
            (("search_handle", 3),),
        ]

    @async_mock.patch("indy.anoncreds.prover_search_credentials_for_proof_req")
    @async_mock.patch("indy.anoncreds.prover_fetch_credentials_for_proof_req")
    @async_mock.patch("indy.anoncreds.prover_close_credentials_search_for_proof_req")
    async def test_get_credentials_for_presentation_request_by_referent(
        self,
        mock_prover_close_credentials_search_for_proof_req,
        mock_prover_fetch_credentials_for_proof_req,
        mock_prover_search_credentials_for_proof_req,
    ):
        SIZE = 300
        SKIP = 50
        mock_prover_search_credentials_for_proof_req.return_value = "search_handle"
        mock_prover_fetch_credentials_for_proof_req.side_effect = [
            json.dumps([{"cred_info": {"referent": f"skip-{i}"}} for i in range(SKIP)]),
            json.dumps(
                [
                    {"cred_info": {"referent": f"reft-{i}"}}
                    for i in range(test_module.IndySdkHolder.CHUNK)
                ]
            ),
            json.dumps(
                [
                    {
                        "cred_info": {
                            "referent": f"reft-{test_module.IndySdkHolder.CHUNK + i}"
                        }
                    }
                    for i in range(SIZE % test_module.IndySdkHolder.CHUNK)
                ]
            ),
        ]

        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)

        credentials = await holder.get_credentials_for_presentation_request_by_referent(
            {"proof": "req"}, ("asdb",), 50, SIZE, {"extra": "query"}
        )

        mock_prover_search_credentials_for_proof_req.assert_called_once_with(
            mock_wallet.handle,
            json.dumps({"proof": "req"}),
            json.dumps({"extra": "query"}),
        )

        assert mock_prover_fetch_credentials_for_proof_req.call_count == 3
        mock_prover_close_credentials_search_for_proof_req.assert_called_once_with(
            "search_handle"
        )

        assert len(credentials) == SIZE
        assert all("reft-" in cred["cred_info"]["referent"] for cred in credentials)

    @async_mock.patch("indy.anoncreds.prover_search_credentials_for_proof_req")
    @async_mock.patch("indy.anoncreds.prover_fetch_credentials_for_proof_req")
    @async_mock.patch("indy.anoncreds.prover_close_credentials_search_for_proof_req")
    async def test_get_credentials_for_presentation_request_by_referent_default_refts(
        self,
        mock_prover_close_credentials_search_for_proof_req,
        mock_prover_fetch_credentials_for_proof_req,
        mock_prover_search_credentials_for_proof_req,
    ):
        mock_prover_search_credentials_for_proof_req.return_value = "search_handle"
        mock_prover_fetch_credentials_for_proof_req.return_value = (
            '[{"cred_info": {"referent": "asdb"}}]'
        )

        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)

        PRES_REQ = {
            "requested_attributes": {
                "0_a_uuid": {"...": "..."},
                "1_b_uuid": {"...": "..."},
            },
            "requested_predicates": {"2_c_ge_80": {"...": "..."}},
        }

        credentials = await holder.get_credentials_for_presentation_request_by_referent(
            PRES_REQ,
            None,
            2,
            3,
        )

        mock_prover_search_credentials_for_proof_req.assert_called_once_with(
            mock_wallet.handle, json.dumps(PRES_REQ), json.dumps({})
        )

    @async_mock.patch("indy.anoncreds.prover_get_credential")
    async def test_get_credential(self, mock_get_cred):
        mock_get_cred.return_value = "{}"

        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)

        credential_json = await holder.get_credential("credential_id")

        mock_get_cred.assert_called_once_with(mock_wallet.handle, "credential_id")

        assert json.loads(credential_json) == {}

    @async_mock.patch("indy.anoncreds.prover_get_credential")
    async def test_get_credential_not_found(self, mock_get_cred):
        mock_get_cred.side_effect = IndyError(error_code=ErrorCode.WalletItemNotFound)

        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)

        with self.assertRaises(test_module.WalletNotFoundError):
            await holder.get_credential("credential_id")

    @async_mock.patch("indy.anoncreds.prover_get_credential")
    async def test_get_credential_x(self, mock_get_cred):
        mock_get_cred.side_effect = IndyError("unexpected failure")

        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)

        with self.assertRaises(test_module.IndyHolderError):
            await holder.get_credential("credential_id")

    async def test_credential_revoked(self):
        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)

        ledger = async_mock.MagicMock()
        ledger.__aenter__ = async_mock.CoroutineMock(return_value=ledger)
        ledger.get_revoc_reg_delta = async_mock.CoroutineMock(
            return_value=(
                {"value": {"...": "..."}},
                1234567890,
            )
        )

        with async_mock.patch.object(  # no creds revoked
            holder, "get_credential", async_mock.CoroutineMock()
        ) as mock_get_cred:
            mock_get_cred.return_value = json.dumps(
                {
                    "rev_reg_id": "dummy-rrid",
                    "cred_rev_id": "123",
                    "...": "...",
                }
            )
            result = await holder.credential_revoked("credential_id", ledger)
            assert not result

        with async_mock.patch.object(  # cred not revocable
            holder, "get_credential", async_mock.CoroutineMock()
        ) as mock_get_cred:
            mock_get_cred.return_value = json.dumps(
                {
                    "rev_reg_id": None,
                    "cred_rev_id": None,
                    "...": "...",
                }
            )
            result = await holder.credential_revoked("credential_id", ledger)
            assert not result

        ledger.get_revoc_reg_delta = async_mock.CoroutineMock(
            return_value=(
                {
                    "value": {
                        "revoked": [1, 2, 3],
                        "...": "...",
                    }
                },
                1234567890,
            )
        )
        with async_mock.patch.object(  # cred not revoked
            holder, "get_credential", async_mock.CoroutineMock()
        ) as mock_get_cred:
            mock_get_cred.return_value = json.dumps(
                {
                    "rev_reg_id": "dummy-rrid",
                    "cred_rev_id": "123",
                    "...": "...",
                }
            )
            result = await holder.credential_revoked("credential_id", ledger)
            assert not result

        with async_mock.patch.object(  # cred revoked
            holder, "get_credential", async_mock.CoroutineMock()
        ) as mock_get_cred:
            mock_get_cred.return_value = json.dumps(
                {
                    "rev_reg_id": "dummy-rrid",
                    "cred_rev_id": "2",
                    "...": "...",
                }
            )
            result = await holder.credential_revoked("credential_id", ledger)
            assert result

    @async_mock.patch("indy.anoncreds.prover_delete_credential")
    @async_mock.patch("indy.non_secrets.get_wallet_record")
    @async_mock.patch("indy.non_secrets.delete_wallet_record")
    async def test_delete_credential(
        self,
        mock_nonsec_del_wallet_record,
        mock_nonsec_get_wallet_record,
        mock_prover_del_cred,
    ):
        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)
        mock_nonsec_get_wallet_record.return_value = json.dumps(
            {
                "type": "typ",
                "id": "ident",
                "value": "value",
                "tags": {"a": json.dumps("1"), "b": json.dumps("2")},
            }
        )

        credential = await holder.delete_credential("credential_id")

        mock_prover_del_cred.assert_called_once_with(
            mock_wallet.handle, "credential_id"
        )

    @async_mock.patch("indy.anoncreds.prover_delete_credential")
    @async_mock.patch("indy.non_secrets.get_wallet_record")
    @async_mock.patch("indy.non_secrets.delete_wallet_record")
    async def test_delete_credential_x(
        self,
        mock_nonsec_del_wallet_record,
        mock_nonsec_get_wallet_record,
        mock_prover_del_cred,
    ):
        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)

        mock_nonsec_get_wallet_record.side_effect = test_module.StorageNotFoundError()
        mock_prover_del_cred.side_effect = IndyError(
            error_code=ErrorCode.WalletItemNotFound
        )

        with self.assertRaises(test_module.WalletNotFoundError):
            await holder.delete_credential("credential_id")
        mock_prover_del_cred.assert_called_once_with(
            mock_wallet.handle, "credential_id"
        )

        mock_prover_del_cred.side_effect = IndyError(
            error_code=ErrorCode.CommonInvalidParam1
        )
        with self.assertRaises(test_module.IndyHolderError):
            await holder.delete_credential("credential_id")
        assert mock_prover_del_cred.call_count == 2

    @async_mock.patch("indy.anoncreds.prover_create_proof")
    async def test_create_presentation(self, mock_create_proof):
        mock_create_proof.return_value = "{}"

        mock_wallet = async_mock.MagicMock()
        holder = test_module.IndySdkHolder(mock_wallet)

        presentation_json = await holder.create_presentation(
            "presentation_request",
            "requested_credentials",
            "schemas",
            "credential_definitions",
        )

        mock_create_proof.assert_called_once_with(
            mock_wallet.handle,
            json.dumps("presentation_request"),
            json.dumps("requested_credentials"),
            mock_wallet.master_secret_id,
            json.dumps("schemas"),
            json.dumps("credential_definitions"),
            json.dumps({}),
        )

        assert json.loads(presentation_json) == {}

    async def test_create_revocation_state(self):
        rr_state = {
            "witness": {"omega": "1 ..."},
            "rev_reg": {"accum": "21 ..."},
            "timestamp": 1234567890,
        }
        holder = test_module.IndySdkHolder("wallet")

        with async_mock.patch.object(
            test_module, "create_tails_reader", async_mock.CoroutineMock()
        ) as mock_create_tails_reader, async_mock.patch.object(
            indy.anoncreds, "create_revocation_state", async_mock.CoroutineMock()
        ) as mock_create_rr_state:
            mock_create_rr_state.return_value = json.dumps(rr_state)

            cred_rev_id = "1"
            rev_reg_def = {"def": 1}
            rev_reg_delta = {"delta": 1}
            timestamp = 1234567890
            tails_path = "/tmp/some.tails"

            result = await holder.create_revocation_state(
                cred_rev_id, rev_reg_def, rev_reg_delta, timestamp, tails_path
            )
            assert json.loads(result) == rr_state

            mock_create_rr_state.assert_awaited_once_with(
                mock_create_tails_reader.return_value,
                rev_reg_def_json=json.dumps(rev_reg_def),
                cred_rev_id=cred_rev_id,
                rev_reg_delta_json=json.dumps(rev_reg_delta),
                timestamp=timestamp,
            )
