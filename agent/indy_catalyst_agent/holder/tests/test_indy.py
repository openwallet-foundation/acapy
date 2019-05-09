import json
from unittest import mock

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from indy_catalyst_agent.holder.indy import IndyHolder


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

    @async_mock.patch("indy.anoncreds.prover_get_credentials_for_proof_req")
    async def test_get_credentials_for_presentation_request(
        self, mock_get_creds_for_pr
    ):
        mock_get_creds_for_pr.return_value = "[1,2,3]"

        mock_wallet = async_mock.MagicMock()
        holder = IndyHolder(mock_wallet)

        credentials = await holder.get_credentials_for_presentation_request(
            {}, 2, 3, {}
        )

        mock_get_creds_for_pr.assert_called_once_with(
            mock_wallet.handle, json.dumps({})
        )

        assert credentials == json.loads("[1,2,3]")
