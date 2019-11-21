import json

import pytest

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from indy.error import IndyError, ErrorCode

from aries_cloudagent.issuer.indy import IndyIssuer, IssuerError
from aries_cloudagent.wallet.indy import IndyWallet


@pytest.mark.indy
class TestIndyIssuer(AsyncTestCase):
    def test_init(self):
        mock_wallet = async_mock.MagicMock()
        issuer = IndyIssuer(mock_wallet)
        assert issuer.wallet is mock_wallet

    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    async def test_create_credential_offer(self, mock_create_offer):
        test_offer = {"test": "offer"}
        test_cred_def_id = "test-cred-def-id"
        mock_create_offer.return_value = json.dumps(test_offer)
        mock_wallet = async_mock.MagicMock()
        issuer = IndyIssuer(mock_wallet)
        offer = await issuer.create_credential_offer(test_cred_def_id)
        assert offer == test_offer
        mock_create_offer.assert_awaited_once_with(mock_wallet.handle, test_cred_def_id)

    @async_mock.patch("indy.anoncreds.issuer_create_credential")
    async def test_create_credential(self, mock_create_credential):
        mock_wallet = async_mock.MagicMock()
        issuer = IndyIssuer(mock_wallet)

        test_schema = {"attrNames": ["attr1"]}
        test_offer = {"test": "offer"}
        test_request = {"test": "request"}
        test_values = {"attr1": "value1"}
        test_credential = {"test": "credential"}
        test_revoc_id = "revoc-id"
        mock_create_credential.return_value = (
            json.dumps(test_credential),
            test_revoc_id,
            None,
        )

        cred, revoc_id = await issuer.create_credential(
            test_schema, test_offer, test_request, test_values
        )
        assert cred == test_credential
        assert revoc_id == test_revoc_id
        mock_create_credential.assert_awaited_once()
        (
            call_wallet,
            call_offer,
            call_request,
            call_values,
            call_etc1,
            call_etc2,
        ) = mock_create_credential.call_args[0]
        assert call_wallet is mock_wallet.handle
        assert json.loads(call_offer) == test_offer
        assert json.loads(call_request) == test_request
        values = json.loads(call_values)
        assert "attr1" in values

        with self.assertRaises(IssuerError):
            # missing attribute
            cred, revoc_id = await issuer.create_credential(
                test_schema, test_offer, test_request, {}
            )
