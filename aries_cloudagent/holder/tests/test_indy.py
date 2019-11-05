import json

import pytest

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from indy.error import IndyError, ErrorCode

from aries_cloudagent.holder.indy import IndyHolder
from aries_cloudagent.storage.error import StorageError
from aries_cloudagent.storage.record import StorageRecord
from aries_cloudagent.wallet.indy import IndyWallet

from ...protocols.issue_credential.v1_0.messages.inner.credential_preview import (
    CredentialPreview,
)


@pytest.mark.indy
class TestIndyHolder(AsyncTestCase):
    def test_init(self):
        holder = IndyHolder("wallet")
        assert holder.wallet == "wallet"

    @async_mock.patch("indy.anoncreds.prover_create_credential_req")
    async def test_create_credential_request(self, mock_create_credential_req):
        mock_create_credential_req.return_value = ("{}", "{}")
        mock_wallet = async_mock.MagicMock()

        holder = IndyHolder(mock_wallet)
        cred_req = await holder.create_credential_request(
            "credential_offer", "credential_definition", "did"
        )

        mock_create_credential_req.assert_called_once_with(
            mock_wallet.handle,
            "did",
            json.dumps("credential_offer"),
            json.dumps("credential_definition"),
            mock_wallet.master_secret_id,
        )

        assert cred_req == ({}, {})

    @async_mock.patch("indy.anoncreds.prover_store_credential")
    async def test_store_credential(self, mock_store_cred):
        mock_store_cred.return_value = "cred_id"
        mock_wallet = async_mock.MagicMock()

        holder = IndyHolder(mock_wallet)

        cred_id = await holder.store_credential(
            "credential_definition", "credential_data", "credential_request_metadata"
        )

        mock_store_cred.assert_called_once_with(
            mock_wallet.handle,
            None,
            json.dumps("credential_request_metadata"),
            json.dumps("credential_data"),
            json.dumps("credential_definition"),
            None,
        )

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

        holder = IndyHolder(mock_wallet)

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

        holder = IndyHolder(mock_wallet)

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

    @async_mock.patch("indy.anoncreds.prover_search_credentials")
    @async_mock.patch("indy.anoncreds.prover_fetch_credentials")
    @async_mock.patch("indy.anoncreds.prover_close_credentials_search")
    async def test_get_credentials(
        self, mock_close_cred_search, mock_fetch_credentials, mock_search_credentials
    ):
        mock_search_credentials.return_value = ("search_handle", "record_count")
        mock_fetch_credentials.return_value = "[1,2,3]"

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        credentials = await holder.get_credentials(0, 0, {})

        mock_search_credentials.assert_called_once_with(
            mock_wallet.handle, json.dumps({})
        )

        mock_fetch_credentials.return_value = "[1,2,3]"

        mock_fetch_credentials.assert_called_once_with("search_handle", 0)
        mock_close_cred_search.assert_called_once_with("search_handle")

        assert credentials == json.loads("[1,2,3]")

    @async_mock.patch("indy.anoncreds.prover_search_credentials")
    @async_mock.patch("indy.anoncreds.prover_fetch_credentials")
    @async_mock.patch("indy.anoncreds.prover_close_credentials_search")
    async def test_get_credentials_seek(
        self, mock_close_cred_search, mock_fetch_credentials, mock_search_credentials
    ):
        mock_search_credentials.return_value = ("search_handle", "record_count")
        mock_fetch_credentials.return_value = "[1,2,3]"

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

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
        mock_prover_search_credentials_for_proof_req.return_value = "search_handle"
        mock_prover_fetch_credentials_for_proof_req.return_value = (
            '[{"cred_info": {"referent": "asdb"}}]'
        )

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        credentials = await holder.get_credentials_for_presentation_request_by_referent(
            {"p": "r"}, ("asdb",), 2, 3, {"e": "q"}
        )

        mock_prover_search_credentials_for_proof_req.assert_called_once_with(
            mock_wallet.handle, json.dumps({"p": "r"}), json.dumps({"e": "q"})
        )

        assert mock_prover_fetch_credentials_for_proof_req.call_args_list == [
            (("search_handle", "asdb", 2),),
            (("search_handle", "asdb", 3),),
        ]

        mock_prover_close_credentials_search_for_proof_req.assert_called_once_with(
            "search_handle"
        )

        assert credentials == (
            {"cred_info": {"referent": "asdb"}, "presentation_referents": ["asdb"]},
        )

    @async_mock.patch("indy.anoncreds.prover_get_credential")
    async def test_get_credential(self, mock_get_cred):
        mock_get_cred.return_value = "{}"

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        credential = await holder.get_credential("credential_id")

        mock_get_cred.assert_called_once_with(mock_wallet.handle, "credential_id")

        assert credential == json.loads("{}")

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
        holder = IndyHolder(mock_wallet)
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

    @async_mock.patch("indy.anoncreds.prover_create_proof")
    async def test_create_presentation(self, mock_create_proof):
        mock_create_proof.return_value = "{}"

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        presentation = await holder.create_presentation(
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

        assert presentation == json.loads("{}")
