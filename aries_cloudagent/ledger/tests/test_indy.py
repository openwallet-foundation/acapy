import asyncio
import json

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

import pytest

from aries_cloudagent.cache.basic import BasicCache
from aries_cloudagent.ledger.indy import (
    BadLedgerRequestError,
    ClosedPoolError,
    ErrorCode,
    IndyErrorHandler,
    IndyError,
    IndyLedger,
    GENESIS_TRANSACTION_PATH,
    LedgerConfigError,
    LedgerError,
    LedgerTransactionError,
    TAA_ACCEPTED_RECORD_TYPE,
)
from aries_cloudagent.storage.indy import IndyStorage
from aries_cloudagent.storage.record import StorageRecord
from aries_cloudagent.wallet.base import DIDInfo


@pytest.mark.indy
class TestIndyLedger(AsyncTestCase):
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"

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
        assert ledger.did_to_nym(ledger.nym_to_did(self.test_did)) == self.test_did

    @async_mock.patch("indy.pool.list_pools")
    @async_mock.patch("builtins.open")
    async def test_init_do_not_recreate(self, mock_open, mock_list_pools):
        mock_open.return_value = async_mock.MagicMock()
        mock_list_pools.return_value = [
            {"pool": "name"},
            {"pool": "another"}
        ]

        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        ledger = IndyLedger("name", mock_wallet)

        assert ledger.pool_name == "name"
        assert ledger.wallet is mock_wallet

        with self.assertRaises(LedgerConfigError):
            await ledger.create_pool_config("genesis_transactions", recreate=False)

        mock_open.assert_called_once_with(GENESIS_TRANSACTION_PATH, "w")

    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.delete_pool_ledger_config")
    @async_mock.patch("indy.pool.list_pools")
    @async_mock.patch("builtins.open")
    async def test_init_recreate(
        self,
        mock_open,
        mock_list_pools,
        mock_delete_config,
        mock_create_config
    ):
        mock_open.return_value = async_mock.MagicMock()
        mock_list_pools.return_value = [
            {"pool": "name"},
            {"pool": "another"}
        ]
        mock_delete_config.return_value = None

        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        ledger = IndyLedger("name", mock_wallet)

        assert ledger.pool_name == "name"
        assert ledger.wallet is mock_wallet

        await ledger.create_pool_config("genesis_transactions", recreate=True)

        mock_open.assert_called_once_with(GENESIS_TRANSACTION_PATH, "w")
        mock_delete_config.assert_called_once_with("name")
        mock_create_config.assert_called_once_with(
            "name", json.dumps({"genesis_txn": GENESIS_TRANSACTION_PATH})
        )

    async def test_init_non_indy(self):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "non-indy"
        with self.assertRaises(LedgerConfigError):
            IndyLedger("name", mock_wallet)

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
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    async def test_aenter_aexit_nested_keepalive(
        self, mock_close_pool, mock_open_ledger, mock_set_proto
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        ledger = IndyLedger("name", mock_wallet, keepalive=1)

        async with ledger as led0:
            mock_set_proto.assert_called_once_with(2)
            mock_open_ledger.assert_called_once_with("name", "{}")
            assert led0 == ledger
            mock_close_pool.assert_not_called()
            assert led0.pool_handle == mock_open_ledger.return_value

        async with ledger as led1:
            assert ledger.ref_count == 1

        mock_close_pool.assert_not_called()  # it's a future
        assert ledger.pool_handle

        await asyncio.sleep(1.01)
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

            await ledger._submit("{}", True, False)

            mock_wallet.get_public_did.assert_called_once_with()

            mock_sign_submit.assert_called_once_with(
                ledger.pool_handle, mock_wallet.handle, mock_did.did, "{}"
            )

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    @async_mock.patch("indy.ledger.sign_and_submit_request")
    @async_mock.patch("indy.ledger.append_txn_author_agreement_acceptance_to_request")
    async def test_submit_signed_taa_accept(
        self,
        mock_append_taa,
        mock_sign_submit,
        mock_close_pool,
        mock_open_ledger,
        mock_create_config,
        mock_set_proto,
    ):

        mock_append_taa.return_value = "{}"
        mock_sign_submit.return_value = '{"op": "REPLY"}'

        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        ledger = IndyLedger("name", mock_wallet)
        ledger.get_latest_txn_author_acceptance = async_mock.CoroutineMock(
            return_value={
                "text": "sample",
                "version": "0.0",
                "digest": "digest",
                "mechanism": "dummy",
                "time": "now"
            }
        )

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_did = mock_wallet.get_public_did.return_value
            mock_did.did = self.test_did

            await ledger._submit(
                request_json="{}",
                sign=None,
                taa_accept=True,
                public_did=self.test_did
            )

            mock_wallet.get_public_did.assert_not_called()
            mock_append_taa.assert_called_once_with(
                "{}",
                "sample",
                "0.0",
                "digest",
                "dummy",
                "now"
            )
            mock_sign_submit.assert_called_once_with(
                ledger.pool_handle, ledger.wallet.handle, self.test_did, "{}"
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
    async def test_submit_unsigned_ledger_transaction_error(
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

        mock_submit.return_value = '{"op": "NO-SUCH-OP"}'

        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did.return_value = future

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            with self.assertRaises(LedgerTransactionError):
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

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.check_existing_schema")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.add_record")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_schema_request")
    async def test_send_schema_ledger_transaction_error_already_exists(
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

        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did = async_mock.CoroutineMock()
        mock_wallet.get_public_did.return_value.did = "abc"

        mock_create_schema.return_value = (1, 2)

        fetch_schema_id = f"{mock_wallet.get_public_did.return_value.did}:{2}:schema_name:schema_version"
        mock_check_existing.side_effect = [None, fetch_schema_id]

        ledger = IndyLedger("name", mock_wallet)
        ledger._submit = async_mock.CoroutineMock(
            side_effect=LedgerTransactionError("UnauthorizedClientRequest")
        )

        async with ledger:
            schema_id = await ledger.send_schema(
                "schema_name", "schema_version", [1, 2, 3]
            )
            assert schema_id == fetch_schema_id

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.check_existing_schema")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.add_record")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_schema_request")
    async def test_send_schema_ledger_transaction_error(
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

        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did = async_mock.CoroutineMock()
        mock_wallet.get_public_did.return_value.did = "abc"

        mock_create_schema.return_value = (1, 2)

        fetch_schema_id = (
            f"{mock_wallet.get_public_did.return_value.did}:{2}:"
            "schema_name:schema_version"
        )
        mock_check_existing.side_effect = [None, fetch_schema_id]

        ledger = IndyLedger("name", mock_wallet)
        ledger._submit = async_mock.CoroutineMock(
            side_effect=LedgerTransactionError("Some other error message")
        )

        async with ledger:
            with self.assertRaises(LedgerTransactionError):
                await ledger.send_schema(
                    "schema_name", "schema_version", [1, 2, 3]
                )

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.fetch_schema_by_id")
    async def test_check_existing_schema(
        self,
        mock_fetch_schema_by_id,
        mock_close,
        mock_open,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did = async_mock.CoroutineMock()
        mock_did = mock_wallet.get_public_did.return_value
        mock_did.did = self.test_did

        mock_fetch_schema_by_id.return_value = {
            "attrNames": ['a', 'b', 'c']
        }

        ledger = IndyLedger("name", mock_wallet)
        async with ledger:
            schema_id = await ledger.check_existing_schema(
                public_did=self.test_did,
                schema_name="test",
                schema_version="1.0",
                attribute_names=['c', 'b', 'a']
            )
            assert schema_id == f"{self.test_did}:2:test:1.0"

            with self.assertRaises(LedgerTransactionError):
                await ledger.check_existing_schema(
                    public_did=self.test_did,
                    schema_name="test",
                    schema_version="1.0",
                    attribute_names=['a', 'b', 'c', 'd']
                )

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.ledger.build_get_schema_request")
    @async_mock.patch("indy.ledger.parse_get_schema_response")
    async def test_get_schema(
        self,
        mock_parse_get_schema_resp,
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

        mock_parse_get_schema_resp.return_value = (None, '{"attrNames": ["a", "b"]}')

        mock_submit.return_value = '{"result":{"seqNo":1}}'

        ledger = IndyLedger("name", mock_wallet, cache=BasicCache())

        async with ledger:
            response = await ledger.get_schema("schema_id")

            mock_wallet.get_public_did.assert_called_once_with()
            mock_build_get_schema_req.assert_called_once_with(mock_did.did, "schema_id")
            mock_submit.assert_called_once_with(
                mock_build_get_schema_req.return_value, public_did=mock_did.did
            )
            mock_parse_get_schema_resp.assert_called_once_with(mock_submit.return_value)

            assert response == json.loads(mock_parse_get_schema_resp.return_value[1])

            response == await ledger.get_schema("schema_id")  # cover get-from-cache
            assert response == json.loads(mock_parse_get_schema_resp.return_value[1])

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.ledger.build_get_schema_request")
    async def test_get_schema_not_found(
        self,
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

        mock_submit.return_value = json.dumps({"result": {"seqNo": None}})

        ledger = IndyLedger("name", mock_wallet, cache=BasicCache())

        async with ledger:
            response = await ledger.get_schema("schema_id")

            mock_wallet.get_public_did.assert_called_once_with()
            mock_build_get_schema_req.assert_called_once_with(mock_did.did, "schema_id")
            mock_submit.assert_called_once_with(
                mock_build_get_schema_req.return_value, public_did=mock_did.did
            )

            assert response is None

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.ledger.build_get_txn_request")
    @async_mock.patch("indy.ledger.build_get_schema_request")
    @async_mock.patch("indy.ledger.parse_get_schema_response")
    async def test_get_schema_by_seq_no(
        self,
        mock_parse_get_schema_resp,
        mock_build_get_schema_req,
        mock_build_get_txn_req,
        mock_submit,
        mock_close,
        mock_open,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did = async_mock.CoroutineMock()
        mock_did = mock_wallet.get_public_did.return_value
        mock_did.did = self.test_did

        mock_parse_get_schema_resp.return_value = (None, '{"attrNames": ["a", "b"]}')

        submissions = [
            json.dumps(
                {
                    "result": {
                        "data": {
                            "txn": {
                                "type": "101",
                                "metadata": {
                                    "from": self.test_did
                                },
                                "data": {
                                    "data": {
                                        "name": "preferences",
                                        "version": "1.0"
                                    }
                                }
                            }
                        }
                    }
                }
            ),
            json.dumps(
                {"result": {"seqNo": 999}}
            )
        ]  # need to subscript these in assertions later
        mock_submit.side_effect = [
            sub for sub in submissions
        ]  # becomes list iterator, unsubscriptable, in mock object

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            response = await ledger.get_schema("999")

            mock_wallet.get_public_did.assert_called_once_with()
            mock_build_get_txn_req.assert_called_once_with(None, None, seq_no=999)
            mock_build_get_schema_req.assert_called_once_with(
                mock_did.did,
                f"{self.test_did}:2:preferences:1.0"
            )
            mock_submit.assert_has_calls(
                [
                    async_mock.call(mock_build_get_txn_req.return_value),
                    async_mock.call(
                        mock_build_get_schema_req.return_value,
                        public_did=mock_did.did
                    )
                ]
            )
            mock_parse_get_schema_resp.assert_called_once_with(submissions[1])

            assert response == json.loads(mock_parse_get_schema_resp.return_value[1])

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.ledger.build_get_txn_request")
    @async_mock.patch("indy.ledger.build_get_schema_request")
    @async_mock.patch("indy.ledger.parse_get_schema_response")
    async def test_get_schema_by_wrong_seq_no(
        self,
        mock_parse_get_schema_resp,
        mock_build_get_schema_req,
        mock_build_get_txn_req,
        mock_submit,
        mock_close,
        mock_open,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"
        mock_wallet.get_public_did = async_mock.CoroutineMock()
        mock_did = mock_wallet.get_public_did.return_value
        mock_did.did = self.test_did

        mock_parse_get_schema_resp.return_value = (None, '{"attrNames": ["a", "b"]}')

        submissions = [
            json.dumps(
                {
                    "result": {
                        "data": {
                            "txn": {
                                "type": "102",  # not a schema
                            }
                        }
                    }
                }
            ),
            json.dumps(
                {"result": {"seqNo": 999}}
            )
        ]  # need to subscript these in assertions later
        mock_submit.side_effect = [
            sub for sub in submissions
        ]  # becomes list iterator, unsubscriptable, in mock object

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            with self.assertRaises(LedgerTransactionError):
                await ledger.get_schema("999")

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.get_schema")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy.IndyLedger.fetch_credential_definition"
    )
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.search_records")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.add_record")
    @async_mock.patch("indy.anoncreds.issuer_create_and_store_credential_def")
    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    @async_mock.patch("indy.ledger.build_cred_def_request")
    async def test_send_credential_definition(
        self,
        mock_build_cred_def,
        mock_create_offer,
        mock_create_store_cred_def,
        mock_add_record,
        mock_search_records,
        mock_submit,
        mock_fetch_cred_def,
        mock_close,
        mock_open,
        mock_get_schema,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_search_records.return_value.fetch_all = async_mock.CoroutineMock(
            return_value=[]
        )

        mock_create_offer.side_effect = IndyError(
            error_code=ErrorCode.CommonInvalidStructure
        )
        mock_get_schema.return_value = {'seqNo': 999}
        cred_def_id = f"{self.test_did}:3:CL:999:default"
        cred_def_value = {
            "primary": {
                "n": "...",
                "s": "...",
                "r": "...",
                "revocation": None
            }
        }
        cred_def = {
            "ver": "1.0",
            "id": cred_def_id,
            "schemaId": "999",
            "type": "CL",
            "tag": "default",
            "value": cred_def_value
        }
        cred_def_json = json.dumps(cred_def)

        mock_create_store_cred_def.return_value = (cred_def_id, cred_def_json)

        mock_fetch_cred_def.side_effect = [None, cred_def]

        ledger = IndyLedger("name", mock_wallet)

        schema_id = "schema_issuer_did:name:1.0"
        tag = "default"

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_wallet.get_public_did.return_value = None

            with self.assertRaises(BadLedgerRequestError):
                await ledger.send_credential_definition(schema_id, tag)

            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_wallet.get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None
            )
            mock_did = mock_wallet.get_public_did.return_value

            result_id = await ledger.send_credential_definition(schema_id, tag)
            assert result_id == cred_def_id

            mock_wallet.get_public_did.assert_called_once_with()
            mock_get_schema.assert_called_once_with(schema_id)

            mock_build_cred_def.assert_called_once_with(mock_did.did, cred_def_json)

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.get_schema")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    async def test_send_credential_definition_no_such_schema(
        self,
        mock_close,
        mock_open,
        mock_get_schema,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_get_schema.return_value = {}

        ledger = IndyLedger("name", mock_wallet)

        schema_id = "schema_issuer_did:name:1.0"
        tag = "default"

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock()

            with self.assertRaises(LedgerError):
                await ledger.send_credential_definition(schema_id, tag)

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.get_schema")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy.IndyLedger.fetch_credential_definition"
    )
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.search_records")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.add_record")
    @async_mock.patch("indy.anoncreds.issuer_create_and_store_credential_def")
    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    @async_mock.patch("indy.ledger.build_cred_def_request")
    async def test_send_credential_definition_offer_exception(
        self,
        mock_build_cred_def,
        mock_create_offer,
        mock_create_store_cred_def,
        mock_add_record,
        mock_search_records,
        mock_submit,
        mock_fetch_cred_def,
        mock_close,
        mock_open,
        mock_get_schema,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_search_records.return_value.fetch_all = async_mock.CoroutineMock(
            return_value=[]
        )

        mock_create_offer.side_effect = IndyError(
            error_code=ErrorCode.CommonIOError,
            error_details={"message": "cover indy error message wrapping"}
        )
        mock_get_schema.return_value = {'seqNo': 999}

        ledger = IndyLedger("name", mock_wallet)

        schema_id = "schema_issuer_did:name:1.0"
        tag = "default"

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock()

            with self.assertRaises(LedgerError):
                await ledger.send_credential_definition(schema_id, tag)

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.get_schema")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy.IndyLedger.fetch_credential_definition"
    )
    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    async def test_send_credential_definition_cred_def_in_wallet_not_ledger(
        self,
        mock_create_offer,
        mock_fetch_cred_def,
        mock_close,
        mock_open,
        mock_get_schema,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_get_schema.return_value = {'seqNo': 999}
        cred_def_id = f"{self.test_did}:3:CL:999:default"
        cred_def_value = {
            "primary": {
                "n": "...",
                "s": "...",
                "r": "...",
                "revocation": None
            }
        }
        cred_def = {
            "ver": "1.0",
            "id": cred_def_id,
            "schemaId": "999",
            "type": "CL",
            "tag": "default",
            "value": cred_def_value
        }
        cred_def_json = json.dumps(cred_def)

        mock_fetch_cred_def.return_value = {}

        ledger = IndyLedger("name", mock_wallet)

        schema_id = "schema_issuer_did:name:1.0"
        tag = "default"

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock()

            with self.assertRaises(LedgerError):
                await ledger.send_credential_definition(schema_id, tag)

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.get_schema")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy.IndyLedger.fetch_credential_definition"
    )
    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    async def test_send_credential_definition_cred_def_on_ledger_not_in_wallet(
        self,
        mock_create_offer,
        mock_fetch_cred_def,
        mock_close,
        mock_open,
        mock_get_schema,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_get_schema.return_value = {'seqNo': 999}
        cred_def_id = f"{self.test_did}:3:CL:999:default"
        cred_def_value = {
            "primary": {
                "n": "...",
                "s": "...",
                "r": "...",
                "revocation": None
            }
        }
        cred_def = {
            "ver": "1.0",
            "id": cred_def_id,
            "schemaId": "999",
            "type": "CL",
            "tag": "default",
            "value": cred_def_value
        }
        cred_def_json = json.dumps(cred_def)

        mock_fetch_cred_def.return_value = cred_def

        mock_create_offer.side_effect = IndyError(
            error_code=ErrorCode.CommonInvalidStructure
        )

        ledger = IndyLedger("name", mock_wallet)

        schema_id = "schema_issuer_did:name:1.0"
        tag = "default"

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock()

            with self.assertRaises(LedgerError):
                await ledger.send_credential_definition(schema_id, tag)

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.get_schema")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy.IndyLedger.fetch_credential_definition"
    )
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.search_records")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.add_record")
    @async_mock.patch("indy.anoncreds.issuer_create_and_store_credential_def")
    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    @async_mock.patch("indy.ledger.build_cred_def_request")
    async def test_send_credential_definition_on_ledger_in_wallet(
        self,
        mock_build_cred_def,
        mock_create_offer,
        mock_create_store_cred_def,
        mock_add_record,
        mock_search_records,
        mock_submit,
        mock_fetch_cred_def,
        mock_close,
        mock_open,
        mock_get_schema,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_search_records.return_value.fetch_all = async_mock.CoroutineMock(
            return_value=[]
        )

        mock_get_schema.return_value = {'seqNo': 999}
        cred_def_id = f"{self.test_did}:3:CL:999:default"
        cred_def_value = {
            "primary": {
                "n": "...",
                "s": "...",
                "r": "...",
                "revocation": None
            }
        }
        cred_def = {
            "ver": "1.0",
            "id": cred_def_id,
            "schemaId": "999",
            "type": "CL",
            "tag": "default",
            "value": cred_def_value
        }
        cred_def_json = json.dumps(cred_def)

        mock_create_store_cred_def.return_value = (cred_def_id, cred_def_json)

        mock_fetch_cred_def.return_value = cred_def

        ledger = IndyLedger("name", mock_wallet)

        schema_id = "schema_issuer_did:name:1.0"
        tag = "default"

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_wallet.get_public_did.return_value = None

            with self.assertRaises(BadLedgerRequestError):
                await ledger.send_credential_definition(schema_id, tag)

            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_wallet.get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None
            )
            mock_did = mock_wallet.get_public_did.return_value

            result_id = await ledger.send_credential_definition(schema_id, tag)
            assert result_id == cred_def_id

            mock_wallet.get_public_did.assert_called_once_with()
            mock_get_schema.assert_called_once_with(schema_id)

            mock_build_cred_def.assert_not_called()

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger.get_schema")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch(
        "aries_cloudagent.ledger.indy.IndyLedger.fetch_credential_definition"
    )
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.search_records")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.add_record")
    @async_mock.patch("indy.anoncreds.issuer_create_and_store_credential_def")
    @async_mock.patch("indy.anoncreds.issuer_create_credential_offer")
    @async_mock.patch("indy.ledger.build_cred_def_request")
    async def test_send_credential_definition_create_cred_def_exception(
        self,
        mock_build_cred_def,
        mock_create_offer,
        mock_create_store_cred_def,
        mock_add_record,
        mock_search_records,
        mock_submit,
        mock_fetch_cred_def,
        mock_close,
        mock_open,
        mock_get_schema,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_search_records.return_value.fetch_all = async_mock.CoroutineMock(
            return_value=[]
        )

        mock_create_offer.side_effect = IndyError(
            error_code=ErrorCode.CommonInvalidStructure
        )
        mock_get_schema.return_value = {'seqNo': 999}
        cred_def_id = f"{self.test_did}:3:CL:999:default"
        cred_def_value = {
            "primary": {
                "n": "...",
                "s": "...",
                "r": "...",
                "revocation": None
            }
        }
        cred_def = {
            "ver": "1.0",
            "id": cred_def_id,
            "schemaId": "999",
            "type": "CL",
            "tag": "default",
            "value": cred_def_value
        }
        cred_def_json = json.dumps(cred_def)

        mock_create_store_cred_def.side_effect = IndyError(
            error_code=ErrorCode.CommonInvalidStructure
        )

        mock_fetch_cred_def.return_value = None

        ledger = IndyLedger("name", mock_wallet)

        schema_id = "schema_issuer_did:name:1.0"
        tag = "default"

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock()
            mock_wallet.get_public_did.return_value = DIDInfo(
                self.test_did,
                self.test_verkey,
                None
            )

            with self.assertRaises(LedgerError):
                await ledger.send_credential_definition(schema_id, tag)

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_get_cred_def_request")
    @async_mock.patch("indy.ledger.parse_get_cred_def_response")
    async def test_get_credential_definition(
        self,
        mock_parse_get_cred_def_resp,
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

        mock_parse_get_cred_def_resp.return_value = (
            None,
            json.dumps({'result': {'seqNo': 1}})
        )

        ledger = IndyLedger("name", mock_wallet, cache=BasicCache())

        async with ledger:
            response = await ledger.get_credential_definition("cred_def_id")

            mock_wallet.get_public_did.assert_called_once_with()
            mock_build_get_cred_def_req.assert_called_once_with(
                mock_did.did, "cred_def_id"
            )
            mock_submit.assert_called_once_with(
                mock_build_get_cred_def_req.return_value, public_did=mock_did.did
            )
            mock_parse_get_cred_def_resp.assert_called_once_with(
                mock_submit.return_value
            )

            assert response == json.loads(mock_parse_get_cred_def_resp.return_value[1])

            response == await ledger.get_credential_definition(  # cover get-from-cache
                "cred_def_id"
            )
            assert response == json.loads(mock_parse_get_cred_def_resp.return_value[1])

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    @async_mock.patch("indy.anoncreds.issuer_create_schema")
    @async_mock.patch("indy.ledger.build_get_cred_def_request")
    @async_mock.patch("indy.ledger.parse_get_cred_def_response")
    async def test_get_credential_definition_ledger_not_found(
        self,
        mock_parse_get_cred_def_resp,
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

        mock_parse_get_cred_def_resp.side_effect = IndyError(
            error_code=ErrorCode.LedgerNotFound,
            error_details={'message': 'not today'}
        )

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
            mock_parse_get_cred_def_resp.assert_called_once_with(
                mock_submit.return_value
            )

            assert response is None

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("indy.ledger.build_get_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    async def test_get_key_for_did(
        self,
        mock_submit,
        mock_build_get_nym_req,
        mock_close,
        mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_submit.return_value = json.dumps(
            {
                "result": {
                    "data": json.dumps({"verkey": self.test_verkey})
                }
            }
        )
        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock(
                return_value = DIDInfo(
                    self.test_did, self.test_verkey, None
                )
            )
            response = await ledger.get_key_for_did(self.test_did)

            assert mock_build_get_nym_req.called_once_with(
                self.test_did,
                ledger.did_to_nym(self.test_did)
            )
            assert mock_submit.called_once_with(
                mock_build_get_nym_req.return_value,
                public_did=self.test_did
            )
            assert response == self.test_verkey

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("indy.ledger.build_get_attrib_request")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    async def test_get_endpoint_for_did(
        self,
        mock_submit,
        mock_build_get_attrib_req,
        mock_close,
        mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        endpoint = "http://aries.ca"
        mock_submit.return_value = json.dumps(
            {
                "result": {
                    "data": json.dumps(
                        {
                            "endpoint": {
                                "endpoint": endpoint
                            }
                        }
                    )
                }
            }
        )
        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock(
                return_value = DIDInfo(
                    self.test_did, self.test_verkey, None
                )
            )
            response = await ledger.get_endpoint_for_did(self.test_did)

            assert mock_build_get_attrib_req.called_once_with(
                self.test_did,
                ledger.did_to_nym(self.test_did),
                "endpoint",
                None,
                None
            )
            assert mock_submit.called_once_with(
                mock_build_get_attrib_req.return_value,
                public_did=self.test_did
            )
            assert response == endpoint

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("indy.ledger.build_get_attrib_request")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    async def test_get_endpoint_for_did_address_none(
        self,
        mock_submit,
        mock_build_get_attrib_req,
        mock_close,
        mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_submit.return_value = json.dumps(
            {
                "result": {
                    "data": json.dumps(
                        {
                            "endpoint": None
                        }
                    )
                }
            }
        )
        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock(
                return_value = DIDInfo(
                    self.test_did, self.test_verkey, None
                )
            )
            response = await ledger.get_endpoint_for_did(self.test_did)

            assert mock_build_get_attrib_req.called_once_with(
                self.test_did,
                ledger.did_to_nym(self.test_did),
                "endpoint",
                None,
                None
            )
            assert mock_submit.called_once_with(
                mock_build_get_attrib_req.return_value,
                public_did=self.test_did
            )
            assert response is None

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("indy.ledger.build_get_attrib_request")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    async def test_get_endpoint_for_did_no_endpoint(
        self,
        mock_submit,
        mock_build_get_attrib_req,
        mock_close,
        mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        mock_submit.return_value = json.dumps(
            {
                "result": {
                    "data": None
                }
            }
        )
        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock(
                return_value = DIDInfo(
                    self.test_did, self.test_verkey, None
                )
            )
            response = await ledger.get_endpoint_for_did(self.test_did)

            assert mock_build_get_attrib_req.called_once_with(
                self.test_did,
                ledger.did_to_nym(self.test_did),
                "endpoint",
                None,
                None
            )
            assert mock_submit.called_once_with(
                mock_build_get_attrib_req.return_value,
                public_did=self.test_did
            )
            assert response is None

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("indy.ledger.build_get_attrib_request")
    @async_mock.patch("indy.ledger.build_attrib_request")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    async def test_update_endpoint_for_did(
        self,
        mock_submit,
        mock_build_attrib_req,
        mock_build_get_attrib_req,
        mock_close,
        mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        endpoint = ["http://old.aries.ca", "http://new.aries.ca"]
        mock_submit.side_effect = [
            json.dumps(
                {
                    "result": {
                        "data": json.dumps(
                            {
                                "endpoint": {
                                    "endpoint": endpoint[i]
                                }
                            }
                        )
                    }
                }
            ) for i in range(len(endpoint))
        ]
        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock(
                return_value = DIDInfo(
                    self.test_did, self.test_verkey, None
                )
            )
            response = await ledger.update_endpoint_for_did(self.test_did, endpoint[1])

            assert mock_build_get_attrib_req.called_once_with(
                self.test_did,
                ledger.did_to_nym(self.test_did),
                "endpoint",
                None,
                None
            )
            mock_submit.assert_has_calls(
                [
                    async_mock.call(
                        mock_build_get_attrib_req.return_value,
                        public_did=self.test_did
                    ),
                    async_mock.call(
                        mock_build_attrib_req.return_value,
                        True,
                        True
                    )
                ]
            )
            assert response

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("indy.ledger.build_get_attrib_request")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    async def test_update_endpoint_for_did_duplicate(
        self,
        mock_submit,
        mock_build_get_attrib_req,
        mock_close,
        mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        endpoint = "http://aries.ca"
        mock_submit.return_value = json.dumps(
            {
                "result": {
                    "data": json.dumps(
                        {
                            "endpoint": {
                                "endpoint": endpoint
                            }
                        }
                    )
                }
            }
        )
        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock(
                return_value = DIDInfo(
                    self.test_did, self.test_verkey, None
                )
            )
            response = await ledger.update_endpoint_for_did(self.test_did, endpoint)

            assert mock_build_get_attrib_req.called_once_with(
                self.test_did,
                ledger.did_to_nym(self.test_did),
                "endpoint",
                None,
                None
            )
            assert mock_submit.called_once_with(
                mock_build_get_attrib_req.return_value,
                public_did=self.test_did
            )
            assert not response

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("indy.ledger.build_nym_request")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    async def test_register_nym(
        self,
        mock_submit,
        mock_build_nym_req,
        mock_close,
        mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock(
                return_value = DIDInfo(
                    self.test_did, self.test_verkey, None
                )
            )
            await ledger.register_nym(
                self.test_did,
                self.test_verkey,
                "alias",
                None
            )

            assert mock_build_nym_req.called_once_with(
                self.test_did,
                self.test_did,
                self.test_verkey,
                "alias",
                None
            )
            assert mock_submit.called_once_with(
                mock_build_nym_req.return_value,
                True,
                True,
                public_did=self.test_did
            )

    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    async def test_taa_digest_bad_value(
        self,
        mock_close_pool,
        mock_open_ledger,
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            with self.assertRaises(ValueError):
                await ledger.taa_digest(None, None)

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("indy.ledger.build_get_acceptance_mechanisms_request")
    @async_mock.patch("indy.ledger.build_get_txn_author_agreement_request")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._submit")
    async def test_get_txn_author_agreement(
        self,
        mock_submit,
        mock_build_get_taa_req,
        mock_build_get_acc_mech_req,
        mock_close,
        mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        txn_result_data = {"text": "text", "version": "1.0"}
        mock_submit.side_effect = [
            json.dumps(
                {
                    "result": {
                        "data": txn_result_data
                    }
                }
            ) for i in range(2)
        ]

        ledger = IndyLedger("name", mock_wallet)

        async with ledger:
            mock_wallet.get_public_did = async_mock.CoroutineMock(
                return_value = DIDInfo(
                    self.test_did, self.test_verkey, None
                )
            )
            response = await ledger.get_txn_author_agreement(reload=True)

            assert mock_build_get_acc_mech_req.called_once_with(
                self.test_did,
                None,
                None
            )
            assert mock_build_get_taa_req.called_once_with(self.test_did, None)
            mock_submit.assert_has_calls(
                [
                    async_mock.call(
                        mock_build_get_acc_mech_req.return_value,
                        public_did=self.test_did
                    ),
                    async_mock.call(
                        mock_build_get_taa_req.return_value,
                        public_did=self.test_did
                    )
                ]
            )
            assert response == {
                "aml_record": txn_result_data,
                "taa_record": {
                    **txn_result_data,
                    "digest": ledger.taa_digest(
                        txn_result_data["version"],
                        txn_result_data["text"]
                    )
                },
                "taa_required": True
            }

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.add_record")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.search_records")
    async def test_accept_and_get_latest_txn_author_agreement(
        self,
        mock_search_records,
        mock_add_record,
        mock_close,
        mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        ledger = IndyLedger("name", mock_wallet, cache=BasicCache())

        accept_time = ledger.taa_rough_timestamp()
        taa_record = {
            "text": "text",
            "version": "1.0",
            "digest": "abcd1234",
        }
        acceptance = {
            "text": taa_record["text"],
            "version": taa_record["version"],
            "digest": taa_record["digest"],
            "mechanism": "dummy",
            "time": accept_time,
        }

        mock_search_records.return_value.fetch_all = async_mock.CoroutineMock(
            return_value=[
                StorageRecord(
                    TAA_ACCEPTED_RECORD_TYPE,
                    json.dumps(acceptance),
                    {"pool_name": ledger.pool_name},
                )
            ]
        )

        async with ledger:
            await ledger.accept_txn_author_agreement(
                taa_record=taa_record,
                mechanism="dummy",
                accept_time=None
            )

            await ledger.cache.clear(f"{TAA_ACCEPTED_RECORD_TYPE}::{ledger.pool_name}")
            for i in range(2):  # populate, then get from, cache
                response = await ledger.get_latest_txn_author_acceptance()
                assert response == acceptance

    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_open")
    @async_mock.patch("aries_cloudagent.ledger.indy.IndyLedger._context_close")
    @async_mock.patch("aries_cloudagent.storage.indy.IndyStorage.search_records")
    async def test_get_latest_txn_author_agreement_none(
        self,
        mock_search_records,
        mock_close,
        mock_open
    ):
        mock_wallet = async_mock.MagicMock()
        mock_wallet.WALLET_TYPE = "indy"

        ledger = IndyLedger("name", mock_wallet, cache=BasicCache())

        mock_search_records.return_value.fetch_all = async_mock.CoroutineMock(
            return_value=[]
        )

        async with ledger:
            await ledger.cache.clear(f"{TAA_ACCEPTED_RECORD_TYPE}::{ledger.pool_name}")
            response = await ledger.get_latest_txn_author_acceptance()
            assert response == {}

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

        ledger = IndyLedger("name", mock_wallet, cache=BasicCache())

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
