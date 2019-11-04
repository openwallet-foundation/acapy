import asyncio
import json

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

import pytest

from aries_cloudagent.ledger.indy import (
    IndyErrorHandler,
    IndyError,
    IndyLedger,
    GENESIS_TRANSACTION_PATH,
    BadLedgerRequestError,
    ClosedPoolError,
    LedgerTransactionError,
)
from aries_cloudagent.storage.indy import IndyStorage


@pytest.mark.indy
class TestIndyLedger(AsyncTestCase):
    test_did = "55GkHamhTU1ZbTbV2ab9DE"

    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("builtins.open")
    async def test_init(self, mock_open, mock_create_config):
        mock_open.return_value = async_mock.MagicMock()

        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        ledger = IndyLedger("name", mock_wallet)

        assert ledger.pool_name == "name"
        assert ledger.wallet is mock_wallet

        await ledger.create_pool_config("genesis_transactions")

        mock_open.assert_called_once_with(GENESIS_TRANSACTION_PATH, "w")
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
            "genesis_transactions"
        )
        mock_create_config.assert_called_once_with(
            "name", json.dumps({"genesis_txn": GENESIS_TRANSACTION_PATH})
        )

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    async def test_aenter_aexit(
        self, mock_close_pool, mock_open_ledger, mock_set_proto
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        ledger = IndyLedger("name", mock_wallet)

        async with ledger as l:
            mock_set_proto.assert_called_once_with(2)
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
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        ledger = IndyLedger("name", mock_wallet)

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

        mock_sign_submit.return_value = '{"op": "REPLY"}'

        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_wallet.get_public_did.return_value = None

            with self.assertRaises(BadLedgerRequestError):
                await ledger._submit("{}", True)

            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_did = mock_wallet.get_public_did.return_value
            mock_did.did = self.test_did

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
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did.return_value = future

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            await ledger._submit("{}", False)

            mock_wallet.get_public_did.assert_not_called()

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
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did.return_value = future

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            with self.assertRaises(LedgerTransactionError) as context:
                await ledger._submit("{}", False)
            assert "Ledger rejected transaction request" in str(context.exception)

        mock_submit.return_value = '{"op": "REJECT", "reason": "another reason"}'

        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did.return_value = future

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            with self.assertRaises(LedgerTransactionError) as context:
                await ledger._submit("{}", False)
            assert "Ledger rejected transaction request" in str(context.exception)

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.fetch_schema_by_id")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.fetch_schema_by_seq_no")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.add_record")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_schema_request")
    async def test_send_schema(
        self,
        mock_build_schema_req,
        mock_create_schema,
        mock_add_record,
        mock_fetch_schema_by_seq_no,
        mock_fetch_schema_by_id,
        mock_submit,
        mock_close,
        mock_open,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        ledger = IndyLedger("name", mock_wallet)

        mock_create_schema.return_value = ("schema_issuer_did:name:1.0", "{}")
        mock_fetch_schema_by_id.return_value = None
        mock_fetch_schema_by_seq_no.return_value = None

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_wallet.get_public_did.return_value = None

            with self.assertRaises(BadLedgerRequestError):
                schema_id = await ledger.send_schema(
                    "schema_name", "schema_version", [1, 2, 3]
                )

            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_did = mock_wallet.get_public_did.return_value
            mock_did.did = self.test_did

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

            mock_submit.assert_called_once_with(
                mock_build_schema_req.return_value, public_did=mock_did.did
            )

            assert schema_id == mock_create_schema.return_value[0]

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.check_existing_schema")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.add_record")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_schema_request")
    async def test_send_schema_already_exists(
        self,
        mock_build_schema_req,
        mock_create_schema,
        mock_add_record,
        mock_check_existing,
        mock_close_pool,
        mock_open_ledger,
        mock_create_config,
        mock_set_proto,
    ):
        # mock_did = async_mock.CoroutineMock()

        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did = async_mock.CoroutineMock()
        mock_wallet.get_public_did.return_value.did = "abc"

        mock_create_schema.return_value = (1, 2)

        fetch_schema_id = f"{mock_wallet.get_public_did.return_value.did}:{2}:schema_name:schema_version"
        mock_check_existing.return_value = fetch_schema_id

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            schema_id = await ledger.send_schema(
                "schema_name", "schema_version", [1, 2, 3]
            )
            assert schema_id == fetch_schema_id

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.ledger.build_get_schema_request")
    @async_mock.patch("indy.ledger.parse_get_schema_response")
    async def test_get_schema(
        self,
        mock_parse_get_schema_req,
        mock_build_get_schema_req,
        mock_submit,
        mock_close,
        mock_open,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did = async_mock.CoroutineMock()
        mock_did = mock_wallet.get_public_did.return_value
        mock_did.did = self.test_did

        mock_parse_get_schema_req.return_value = (None, "{}")

        mock_submit.return_value = '{"result":{"seqNo":1}}'

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            response = await ledger.get_schema("schema_id")

            mock_wallet.get_public_did.assert_called_once_with()
            mock_build_get_schema_req.assert_called_once_with(mock_did.did, "schema_id")
            mock_submit.assert_called_once_with(
                mock_build_get_schema_req.return_value, public_did=mock_did.did
            )
            mock_parse_get_schema_req.assert_called_once_with(mock_submit.return_value)

            assert response == json.loads(mock_parse_get_schema_req.return_value[1])

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.get_schema")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy.IndyLedger.fetch_credential_definition"
    )
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.add_record")
    @async_mock.patch("indy.anoncreds.issuer_create_and_store_credential_def")
    @async_mock.patch("indy.ledger.build_cred_def_request")
    async def test_send_credential_definition(
        self,
        mock_build_cred_def,
        mock_create_store_cred_def,
        mock_add_record,
        mock_submit,
        mock_fetch_cred_def,
        mock_close,
        mock_open,
        mock_get_schema,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_get_schema.return_value = "{}"
        cred_id = "cred_id"
        cred_json = "[]"
        mock_create_store_cred_def.return_value = (cred_id, cred_json)

        mock_fetch_cred_def.return_value = None

        ledger = IndyLedger("name", mock_wallet)

        schema_id = "schema_issuer_did:name:1.0"
        tag = "tag"

        async with ledger:

            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_wallet.get_public_did.return_value = None

            with self.assertRaises(BadLedgerRequestError):
                await ledger.send_credential_definition(schema_id, tag)

            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_did = mock_wallet.get_public_did.return_value

            result_id = await ledger.send_credential_definition(schema_id, tag)
            assert result_id == cred_id

            mock_wallet.get_public_did.assert_called_once_with()
            mock_get_schema.assert_called_once_with(schema_id)

            mock_build_cred_def.assert_called_once_with(mock_did.did, cred_json)

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_get_cred_def_request")
    @async_mock.patch("indy.ledger.parse_get_cred_def_response")
    async def test_get_credential_definition(
        self,
        mock_parse_get_cred_def_req,
        mock_build_get_cred_def_req,
        mock_create_schema,
        mock_submit,
        mock_close,
        mock_open,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did = async_mock.CoroutineMock()
        mock_did = mock_wallet.get_public_did.return_value

        mock_parse_get_cred_def_req.return_value = (None, "{}")

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            response = await ledger.get_credential_definition("cred_def_id")

            mock_wallet.get_public_did.assert_called_once_with()
            mock_build_get_cred_def_req.assert_called_once_with(
                mock_did.did, "cred_def_id"
            )
            mock_submit.assert_called_once_with(
                mock_build_get_cred_def_req.return_value, public_did=mock_did.did
            )
            mock_parse_get_cred_def_req.assert_called_once_with(
                mock_submit.return_value
            )

            assert response == json.loads(mock_parse_get_cred_def_req.return_value[1])

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.get_schema")
    async def test_credential_definition_id2schema_id(
        self, mock_get_schema, mock_close, mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        S_ID = f"{TestIndyLedger.test_did}:2:favourite_drink:1.0"
        SEQ_NO = "9999"
        mock_get_schema.return_value = {"id": S_ID}

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            s_id_short = await ledger.credential_definition_id2schema_id(
                f"{TestIndyLedger.test_did}:3:CL:{SEQ_NO}:tag"
            )

            mock_get_schema.assert_called_once_with(SEQ_NO)

            assert s_id_short == S_ID
            s_id_long = await ledger.credential_definition_id2schema_id(
                f"{TestIndyLedger.test_did}:3:CL:{s_id_short}:tag"
            )
            assert s_id_long == s_id_short

    def test_error_handler(self):
        with self.assertRaises(LedgerTransactionError):
            with IndyErrorHandler("message", LedgerTransactionError):
                raise IndyError(error_code=1)
