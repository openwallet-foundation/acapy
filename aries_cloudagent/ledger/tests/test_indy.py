import asyncio
import json

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

import pytest

from aries_cloudagent.ledger.indy import (
    IndyLedger,
    GENESIS_TRANSACTION_PATH,
    ClosedPoolError,
    LedgerTransactionError,
    DuplicateSchemaError,
)


@pytest.mark.indy
class TestIndyLedger(AsyncTestCase):
    @async_mock.patch("builtins.open")
    def test_init(self, mock_open):
        mock_open.return_value = async_mock.MagicMock()

        ledger = IndyLedger("name", "wallet", "genesis_transactions")

        assert ledger.name == "name"
        assert ledger.wallet == "wallet"

        mock_open.assert_called_once_with(GENESIS_TRANSACTION_PATH, "w")
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
            "genesis_transactions"
        )

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    async def test_aenter_aexit(
        self, mock_close_pool, mock_open_ledger, mock_create_config, mock_set_proto
    ):
        ledger = IndyLedger("name", "wallet", "genesis_transactions")

        async with ledger as l:
            mock_set_proto.assert_called_once_with(2)
            mock_create_config.assert_called_once_with(
                "name", json.dumps({"genesis_txn": GENESIS_TRANSACTION_PATH})
            )
            mock_open_ledger.assert_called_once_with("name", "{}")
            assert l == ledger
            mock_close_pool.assert_not_called()
            assert l.pool_handle == mock_open_ledger.return_value

        mock_close_pool.assert_called_once()
        assert ledger.pool_handle == None

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    async def test_submit_pool_closed(
        self, mock_close_pool, mock_open_ledger, mock_create_config, mock_set_proto
    ):
        ledger = IndyLedger("name", "wallet", "genesis_transactions")

        with self.assertRaises(ClosedPoolError) as context:
            await ledger._submit("{}")
        assert "sign and submit request to closed pool" in str(context.exception)

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    @async_mock.patch("indy.ledger.sign_and_submit_request")
    async def test_submit_signed(
        self,
        mock_sign_submit,
        mock_close_pool,
        mock_open_ledger,
        mock_create_config,
        mock_set_proto,
    ):

        mock_did = async_mock.MagicMock()

        future = asyncio.Future()
        future.set_result(mock_did)

        mock_sign_submit.return_value = '{"op": "REPLY"}'

        mock_wallet = async_mock.MagicMock()
        mock_wallet.get_public_did.return_value = future

        ledger = IndyLedger("name", mock_wallet, "genesis_transactions")

        async with ledger:
            await ledger._submit("{}", True)

            mock_wallet.get_public_did.assert_called_once_with()

            mock_sign_submit.assert_called_once_with(
                ledger.pool_handle, mock_wallet.handle, mock_did.did, "{}"
            )

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    @async_mock.patch("indy.ledger.submit_request")
    async def test_submit_unsigned(
        self,
        mock_submit,
        mock_close_pool,
        mock_open_ledger,
        mock_create_config,
        mock_set_proto,
    ):

        mock_did = async_mock.MagicMock()

        future = asyncio.Future()
        future.set_result(mock_did)

        mock_submit.return_value = '{"op": "REPLY"}'

        mock_wallet = async_mock.MagicMock()
        mock_wallet.get_public_did.return_value = future

        ledger = IndyLedger("name", mock_wallet, "genesis_transactions")

        async with ledger:
            await ledger._submit("{}", False)

            mock_wallet.get_public_did.assert_called_once_with()

            mock_submit.assert_called_once_with(ledger.pool_handle, "{}")

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    @async_mock.patch("indy.ledger.submit_request")
    async def test_submit_rejected(
        self,
        mock_submit,
        mock_close_pool,
        mock_open_ledger,
        mock_create_config,
        mock_set_proto,
    ):

        mock_did = async_mock.MagicMock()

        future = asyncio.Future()
        future.set_result(mock_did)

        mock_submit.return_value = '{"op": "REQNACK", "reason": "a reason"}'

        mock_wallet = async_mock.MagicMock()
        mock_wallet.get_public_did.return_value = future

        ledger = IndyLedger("name", mock_wallet, "genesis_transactions")

        async with ledger:
            with self.assertRaises(LedgerTransactionError) as context:
                await ledger._submit("{}", False)
            assert "Ledger rejected transaction request" in str(context.exception)

        mock_submit.return_value = '{"op": "REJECT", "reason": "another reason"}'

        mock_wallet = async_mock.MagicMock()
        mock_wallet.get_public_did.return_value = future

        ledger = IndyLedger("name", mock_wallet, "genesis_transactions")

        async with ledger:
            with self.assertRaises(LedgerTransactionError) as context:
                await ledger._submit("{}", False)
            assert "Ledger rejected transaction request" in str(context.exception)

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.__aenter__")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.__aexit__")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_schema_request")
    async def test_send_schema(
        self,
        mock_build_schema_req,
        mock_create_schema,
        mock_submit,
        mock_aexit,
        mock_aenter,
    ):
        mock_did = async_mock.MagicMock()

        mock_wallet = async_mock.MagicMock()
        mock_wallet.get_public_did.return_value = mock_did

        ledger = IndyLedger("name", mock_wallet, "genesis_transactions")

        async with ledger:
            schema_id = await ledger.send_schema(
                "schema_name", "schema_version", [1, 2, 3]
            )

            mock_wallet.get_public_did.assert_called_once_with()
            mock_create_schema.assert_called_once_with(
                mock_did.did, "schema_name", "schema_version", json.dumps([1, 2, 3])
            )

            mock_build_schema_req.assert_called_once_with(
                mock_did.did, mock_create_schema.return_value[1]
            )

            mock_submit.assert_called_once_with(mock_build_schema_req.return_value)

            assert schema_id == mock_create_schema.return_value[0]

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_schema_request")
    async def test_send_schema_already_exists(
        self,
        mock_build_schema_req,
        mock_create_schema,
        mock_submit,
        mock_close_pool,
        mock_open_ledger,
        mock_create_config,
        mock_set_proto,
    ):
        # mock_did = async_mock.CoroutineMock()

        mock_wallet = async_mock.CoroutineMock()
        mock_wallet.get_public_did = async_mock.CoroutineMock()
        mock_wallet.get_public_did.return_value.did = "abc"

        mock_create_schema.return_value = (1, 2)

        mock_submit.side_effect = DuplicateSchemaError

        ledger = IndyLedger("name", mock_wallet, "genesis_transactions")

        async with ledger:
            schema_id = await ledger.send_schema(
                "schema_name", "schema_version", [1, 2, 3]
            )
            assert (
                schema_id
                == f"{mock_wallet.get_public_did.return_value.did}:{2}:schema_name:schema_version"
            )

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.__aenter__")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.__aexit__")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_get_schema_request")
    @async_mock.patch("indy.ledger.parse_get_schema_response")
    async def test_get_schema(
        self,
        mock_parse_get_schema_req,
        mock_build_get_schema_req,
        mock_create_schema,
        mock_submit,
        mock_aexit,
        mock_aenter,
    ):
        mock_did = async_mock.MagicMock()

        mock_wallet = async_mock.MagicMock()
        mock_wallet.get_public_did.return_value = mock_did

        mock_parse_get_schema_req.return_value = (None, "{}")

        ledger = IndyLedger("name", mock_wallet, "genesis_transactions")

        async with ledger:
            response = await ledger.get_schema("schema_id")

            mock_wallet.get_public_did.assert_called_once_with()
            mock_build_get_schema_req.assert_called_once_with(mock_did.did, "schema_id")
            mock_submit.assert_called_once_with(mock_build_get_schema_req.return_value)
            mock_parse_get_schema_req.assert_called_once_with(mock_submit.return_value)

            assert response == json.loads(mock_parse_get_schema_req.return_value[1])

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.get_schema")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.__aenter__")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.__aexit__")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_schema_request")
    async def test_send_credential_definition(
        self,
        mock_build_schema_req,
        mock_create_schema,
        mock_submit,
        mock_aexit,
        mock_aenter,
        mock_get_schema,
    ):
        mock_did = async_mock.MagicMock()

        mock_wallet = async_mock.MagicMock()
        mock_wallet.get_public_did.return_value = mock_did

        mock_get_schema.return_value = "{}"

        ledger = IndyLedger("name", mock_wallet, "genesis_transactions")

        async with ledger:
            credential_definition_id = await ledger.get_schema("schema_id", "tag")

            mock_wallet.get_public_did.assert_called_once_with()
            mock_get_schema.assert_called_once_with(
                mock_wallet.get_public_did.return_value
            )
