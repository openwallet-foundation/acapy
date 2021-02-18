from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest

from ....ledger.base import BaseLedger
from ....wallet.base import BaseWallet, DIDInfo

from .. import wallet_plugin as test_module


class TestWalletCrypto(AsyncTestCase):
    def setUp(self):
        test_module.LOADED = False

    async def test_file_ext(self):
        assert test_module.file_ext()

    def test_load_postgres_plugin(self):
        storage_config = '{"wallet_scheme":"MultiWalletSingleTable"}'
        storage_creds = '{"account":"test"}'
        mock_stg_lib = async_mock.MagicMock(
            postgresstorage_init=async_mock.MagicMock(return_value=0),
            init_storagetype=async_mock.MagicMock(return_value=0),
        )
        with async_mock.patch.object(
            test_module.cdll, "LoadLibrary", async_mock.Mock()
        ) as mock_load:
            mock_load.return_value = mock_stg_lib
            test_module.load_postgres_plugin(storage_config, storage_creds)

            assert test_module.LOADED

    def test_load_postgres_plugin_init_x_raise(self):
        storage_config = '{"wallet_scheme":"MultiWalletSingleTable"}'
        storage_creds = '{"account":"test"}'
        mock_stg_lib = async_mock.MagicMock(
            postgresstorage_init=async_mock.MagicMock(return_value=2)
        )
        with async_mock.patch.object(
            test_module.cdll, "LoadLibrary", async_mock.Mock()
        ) as mock_load:
            mock_load.return_value = mock_stg_lib
            with self.assertRaises(OSError) as context:
                test_module.load_postgres_plugin(
                    storage_config, storage_creds, raise_exc=True
                )
            assert "unable to load postgres" in str(context.exception)

    def test_load_postgres_plugin_init_x_exit(self):
        storage_config = '{"wallet_scheme":"MultiWalletSingleTable"}'
        storage_creds = '{"account":"test"}'
        mock_stg_lib = async_mock.MagicMock(
            postgresstorage_init=async_mock.MagicMock(return_value=2)
        )
        with async_mock.patch.object(
            test_module.cdll, "LoadLibrary", async_mock.Mock()
        ) as mock_load:
            mock_load.return_value = mock_stg_lib
            with self.assertRaises(SystemExit):
                test_module.load_postgres_plugin(
                    storage_config, storage_creds, raise_exc=False
                )

    def test_load_postgres_plugin_config_x_raise(self):
        storage_config = '{"wallet_scheme":"MultiWalletSingleTable"}'
        storage_creds = '{"account":"test"}'
        mock_stg_lib = async_mock.MagicMock(
            postgresstorage_init=async_mock.MagicMock(return_value=0),
            init_storagetype=async_mock.MagicMock(return_value=2),
        )
        with async_mock.patch.object(
            test_module.cdll, "LoadLibrary", async_mock.Mock()
        ) as mock_load:
            mock_load.return_value = mock_stg_lib
            with self.assertRaises(OSError) as context:
                test_module.load_postgres_plugin(
                    storage_config, storage_creds, raise_exc=True
                )
            assert "unable to configure postgres" in str(context.exception)

    def test_load_postgres_plugin_config_x_exit(self):
        storage_config = '{"wallet_scheme":"MultiWalletSingleTable"}'
        storage_creds = '{"account":"test"}'
        mock_stg_lib = async_mock.MagicMock(
            postgresstorage_init=async_mock.MagicMock(return_value=0),
            init_storagetype=async_mock.MagicMock(return_value=2),
        )
        with async_mock.patch.object(
            test_module.cdll, "LoadLibrary", async_mock.Mock()
        ) as mock_load:
            mock_load.return_value = mock_stg_lib
            with self.assertRaises(SystemExit):
                test_module.load_postgres_plugin(
                    storage_config, storage_creds, raise_exc=False
                )

    def test_load_postgres_plugin_bad_json_x_raise(self):
        storage_config = '{"wallet_scheme":"MultiWalletSingleTable"}'
        storage_creds = '"account":"test"'
        mock_stg_lib = async_mock.MagicMock(
            postgresstorage_init=async_mock.MagicMock(return_value=0),
            init_storagetype=async_mock.MagicMock(return_value=2),
        )
        with async_mock.patch.object(
            test_module.cdll, "LoadLibrary", async_mock.Mock()
        ) as mock_load:
            mock_load.return_value = mock_stg_lib
            with self.assertRaises(OSError) as context:
                test_module.load_postgres_plugin(
                    storage_config, storage_creds, raise_exc=True
                )
            assert "Invalid stringified JSON input" in str(context.exception)

    def test_load_postgres_plugin_bad_json_x_exit(self):
        storage_config = '"wallet_scheme":"MultiWalletSingleTable"'
        storage_creds = '{"account":"test"}'
        mock_stg_lib = async_mock.MagicMock(
            postgresstorage_init=async_mock.MagicMock(return_value=0),
            init_storagetype=async_mock.MagicMock(return_value=2),
        )
        with async_mock.patch.object(
            test_module.cdll, "LoadLibrary", async_mock.Mock()
        ) as mock_load:
            mock_load.return_value = mock_stg_lib
            with self.assertRaises(SystemExit):
                test_module.load_postgres_plugin(
                    storage_config, storage_creds, raise_exc=False
                )
