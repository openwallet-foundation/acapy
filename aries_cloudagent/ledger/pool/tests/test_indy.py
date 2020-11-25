import asyncio
import json
from os import path
import tempfile
from indy.error import ErrorCode
import pytest

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ...pool.indy import (
    IndyError,
    GENESIS_TRANSACTION_FILE,
    IndyLegderPool,
    LedgerConfigError,
    LedgerError,
)


@pytest.mark.indy
class TestIndyLedgerPool(AsyncTestCase):
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("builtins.open")
    async def test_init(self, mock_open, mock_create_config):
        mock_open.return_value = async_mock.MagicMock()

        pool = IndyLegderPool("name")

        assert pool.name == "name"

        await pool.create_pool_config("genesis_transactions")

        txn_path = path.join(tempfile.gettempdir(), f"name_{GENESIS_TRANSACTION_FILE}")

        mock_open.assert_called_once_with(txn_path, "w")
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
            "genesis_transactions"
        )
        mock_create_config.assert_called_once_with(
            "name", json.dumps({"genesis_txn": txn_path})
        )

    @async_mock.patch("indy.pool.list_pools")
    @async_mock.patch("builtins.open")
    async def test_init_do_not_recreate(self, mock_open, mock_list_pools):
        mock_open.return_value = async_mock.MagicMock()
        mock_list_pools.return_value = [{"pool": "name"}, {"pool": "another"}]

        pool = IndyLegderPool("name")
        assert pool.type == "indy"
        assert pool.name == "name"

        with self.assertRaises(LedgerConfigError):
            await pool.create_pool_config("genesis_transactions", recreate=False)

        txn_path = path.join(tempfile.gettempdir(), f"name_{GENESIS_TRANSACTION_FILE}")
        mock_open.assert_called_once_with(txn_path, "w")

    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("indy.pool.delete_pool_ledger_config")
    @async_mock.patch("indy.pool.list_pools")
    @async_mock.patch("builtins.open")
    async def test_init_recreate(
        self, mock_open, mock_list_pools, mock_delete_config, mock_create_config
    ):
        mock_open.return_value = async_mock.MagicMock()
        mock_list_pools.return_value = [{"pool": "name"}, {"pool": "another"}]
        mock_delete_config.return_value = None

        pool = IndyLegderPool("name")
        txn_path = path.join(tempfile.gettempdir(), f"name_{GENESIS_TRANSACTION_FILE}")

        assert pool.name == "name"

        await pool.create_pool_config("genesis_transactions", recreate=True)

        mock_open.assert_called_once_with(txn_path, "w")
        mock_delete_config.assert_called_once_with("name")
        mock_create_config.assert_called_once_with(
            "name", json.dumps({"genesis_txn": txn_path})
        )

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    async def test_aenter_aexit(self, mock_close_pool, mock_open_pool, mock_set_proto):
        pool = IndyLegderPool("name")

        async with pool as po:
            mock_set_proto.assert_called_once_with(2)
            mock_open_pool.assert_called_once_with("name", "{}")
            assert po == pool
            mock_close_pool.assert_not_called()
            assert po.handle == mock_open_pool.return_value

        mock_close_pool.assert_called_once()
        assert pool.handle == None

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    async def test_aenter_aexit_nested_keepalive(
        self, mock_close_pool, mock_open_pool, mock_set_proto
    ):
        pool = IndyLegderPool("name", keepalive=1)

        async with pool as po0:
            mock_set_proto.assert_called_once_with(2)
            mock_open_pool.assert_called_once_with("name", "{}")
            assert po0 == pool
            mock_close_pool.assert_not_called()
            assert po0.handle == mock_open_pool.return_value

        async with pool as po0:
            assert pool.ref_count == 1

        mock_close_pool.assert_not_called()  # it's a future
        assert pool.handle

        await asyncio.sleep(1.01)
        mock_close_pool.assert_called_once()
        assert pool.handle == None

    @async_mock.patch("indy.pool.set_protocol_version")
    @async_mock.patch("indy.pool.open_pool_ledger")
    @async_mock.patch("indy.pool.close_pool_ledger")
    async def test_aenter_aexit_close_x(
        self, mock_close_pool, mock_open_pool, mock_set_proto
    ):
        mock_close_pool.side_effect = IndyError(ErrorCode.PoolLedgerTimeout)
        pool = IndyLegderPool("name")

        with self.assertRaises(LedgerError):
            async with pool as po:
                assert po.handle == mock_open_pool.return_value

        assert pool.handle == mock_open_pool.return_value
        assert pool.ref_count == 1