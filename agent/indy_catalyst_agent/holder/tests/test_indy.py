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
