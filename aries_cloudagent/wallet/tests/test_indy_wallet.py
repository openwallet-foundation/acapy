import base64
import json
import os

import indy.anoncreds
import indy.crypto
import indy.did
import indy.wallet
import pytest
from aries_cloudagent.ledger.endpoint_type import EndpointType
from aries_cloudagent.wallet.in_memory import InMemoryWallet
from aries_cloudagent.wallet.indy import IndyWallet
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import indy as test_module
from . import test_in_memory_wallet


@pytest.fixture()
async def basic_wallet():
    wallet = BasicWallet()
    await wallet.open()
    yield wallet
    await wallet.close()


@pytest.fixture()
async def wallet():
    key = await IndyWallet.generate_wallet_key()
    wallet = IndyWallet(
        {
            "auto_create": True,
            "auto_remove": True,
            "name": "test-wallet",
            "key": key,
            "key_derivation_method": "RAW",  # much slower tests with argon-hashed keys
        }
    )
    await wallet.open()
    yield wallet
    await wallet.close()


@pytest.mark.indy
class TestIndyWallet(test_basic_wallet.TestBasicWallet):
    """Apply all BasicWallet tests against IndyWallet"""

    @pytest.mark.asyncio
    async def test_properties(self, wallet):
        assert wallet.name
        assert wallet.type == "indy"
        assert wallet.handle
        none_wallet = IndyWallet()
        assert none_wallet.name == IndyWallet.DEFAULT_NAME

        assert "IndyWallet" in str(wallet)
        assert wallet.created
        assert wallet.master_secret_id == wallet.name
        assert wallet._wallet_config

    @pytest.mark.asyncio
    async def test_rotate_did_keypair_x(self, wallet):
        info = await wallet.create_local_did(self.test_seed, self.test_did)

        with async_mock.patch.object(
            indy.did, "replace_keys_start", async_mock.CoroutineMock()
        ) as mock_repl_start:
            mock_repl_start.side_effect = test_module.IndyError(
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            with pytest.raises(test_module.WalletError) as excinfo:
                await wallet.rotate_did_keypair_start(self.test_did)
            assert "outlier" in str(excinfo.value)

        with async_mock.patch.object(
            indy.did, "replace_keys_apply", async_mock.CoroutineMock()
        ) as mock_repl_apply:
            mock_repl_apply.side_effect = test_module.IndyError(
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            with pytest.raises(test_module.WalletError) as excinfo:
                await wallet.rotate_did_keypair_apply(self.test_did)
            assert "outlier" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_create_signing_key_x(self, wallet):
        with async_mock.patch.object(
            indy.crypto, "create_key", async_mock.CoroutineMock()
        ) as mock_create_key:
            mock_create_key.side_effect = test_module.IndyError(
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            with pytest.raises(test_module.WalletError) as excinfo:
                await wallet.create_signing_key()
            assert "outlier" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_create_local_did_x(self, wallet):
        with async_mock.patch.object(
            indy.did, "create_and_store_my_did", async_mock.CoroutineMock()
        ) as mock_create:
            mock_create.side_effect = test_module.IndyError(
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            with pytest.raises(test_module.WalletError) as excinfo:
                await wallet.create_local_did()
            assert "outlier" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_set_did_endpoint_ledger(self, wallet):
        mock_ledger = async_mock.MagicMock(
            read_only=False, update_endpoint_for_did=async_mock.CoroutineMock()
        )
        info_pub = await wallet.create_public_did()
        await wallet.set_did_endpoint(info_pub.did, "http://1.2.3.4:8021", mock_ledger)
        mock_ledger.update_endpoint_for_did.assert_called_once_with(
            info_pub.did, "http://1.2.3.4:8021", EndpointType.ENDPOINT
        )
        info_pub2 = await wallet.get_public_did()
        assert info_pub2.metadata["endpoint"] == "http://1.2.3.4:8021"

        with pytest.raises(test_module.LedgerConfigError) as excinfo:
            await wallet.set_did_endpoint(info_pub.did, "http://1.2.3.4:8021", None)
        assert "No ledger available" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_set_did_endpoint_readonly_ledger(self, wallet):
        mock_ledger = async_mock.MagicMock(
            read_only=True, update_endpoint_for_did=async_mock.CoroutineMock()
        )
        info_pub = await wallet.create_public_did()
        await wallet.set_did_endpoint(info_pub.did, "http://1.2.3.4:8021", mock_ledger)
        mock_ledger.update_endpoint_for_did.assert_not_called()
        info_pub2 = await wallet.get_public_did()
        assert info_pub2.metadata["endpoint"] == "http://1.2.3.4:8021"

        with pytest.raises(test_module.LedgerConfigError) as excinfo:
            await wallet.set_did_endpoint(info_pub.did, "http://1.2.3.4:8021", None)
        assert "No ledger available" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_signing_key_x(self, wallet):
        with async_mock.patch.object(
            indy.crypto, "get_key_metadata", async_mock.CoroutineMock()
        ) as mock_signing:
            mock_signing.side_effect = test_module.IndyError(
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            with pytest.raises(test_module.WalletError) as excinfo:
                await wallet.get_signing_key(None)
            assert "outlier" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_get_local_did_x(self, wallet):
        with async_mock.patch.object(
            indy.did, "get_my_did_with_meta", async_mock.CoroutineMock()
        ) as mock_my:
            mock_my.side_effect = test_module.IndyError(
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            with pytest.raises(test_module.WalletError) as excinfo:
                await wallet.get_local_did(None)
            assert "outlier" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_verify_message_x(self, wallet):
        with async_mock.patch.object(
            indy.crypto, "crypto_verify", async_mock.CoroutineMock()
        ) as mock_verify:
            mock_verify.side_effect = test_module.IndyError(  # outlier
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            with pytest.raises(test_module.WalletError) as excinfo:
                await wallet.verify_message(
                    b"hello world", b"signature", self.test_verkey
                )
            assert "outlier" in str(excinfo.value)

            mock_verify.side_effect = test_module.IndyError(  # plain wrong
                test_module.ErrorCode.CommonInvalidStructure
            )
            assert not await wallet.verify_message(
                b"hello world", b"signature", self.test_verkey
            )

    @pytest.mark.asyncio
    async def test_pack_message_x(self, wallet):
        with async_mock.patch.object(
            indy.crypto, "pack_message", async_mock.CoroutineMock()
        ) as mock_pack:
            mock_pack.side_effect = test_module.IndyError(  # outlier
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            with pytest.raises(test_module.WalletError) as excinfo:
                await wallet.pack_message(
                    b"hello world",
                    [
                        self.test_verkey,
                    ],
                )
            assert "outlier" in str(excinfo.value)


@pytest.mark.indy
class TestWalletCompat:
    """ Tests for wallet compatibility."""

    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_message = "test message"

    @pytest.mark.asyncio
    async def test_compare_pack_unpack(self, basic_wallet, wallet):
        """
        Ensure that python-based pack/unpack is compatible with indy-sdk implementation
        """
        await basic_wallet.create_local_did(self.test_seed)
        py_packed = await basic_wallet.pack_message(
            self.test_message, [self.test_verkey], self.test_verkey
        )

        await wallet.create_local_did(self.test_seed)
        packed = await wallet.pack_message(
            self.test_message, [self.test_verkey], self.test_verkey
        )

        py_unpacked, from_vk, to_vk = await basic_wallet.unpack_message(packed)
        assert self.test_message == py_unpacked

        unpacked, from_vk, to_vk = await wallet.unpack_message(py_packed)
        assert self.test_message == unpacked

    @pytest.mark.asyncio
    async def test_mock_coverage(self):
        """
        Coverage through mock framework.
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            fake_wallet = IndyWallet(
                {
                    "auto_create": False,
                    "auto_remove": False,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            mock_load.assert_called_once_with(storage_config_json, storage_creds_json)
            await fake_wallet.create()
            await fake_wallet.open()
            assert fake_wallet._wallet_access
            await fake_wallet.close()
            await fake_wallet.remove()

    @pytest.mark.asyncio
    async def test_mock_coverage_wallet_exists_x(self):
        """
        Coverage through mock framework: raise on creation of existing wallet
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            mock_create.side_effect = test_module.IndyError(
                test_module.ErrorCode.WalletAlreadyExistsError
            )
            fake_wallet = IndyWallet(
                {
                    "auto_create": False,
                    "auto_remove": True,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            with pytest.raises(test_module.WalletError) as excinfo:
                await fake_wallet.create()
            assert "Wallet was not removed by SDK" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_mock_coverage_wallet_create_x(self):
        """
        Coverage through mock framework: raise on creation outlier
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            mock_create.side_effect = test_module.IndyError(
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            fake_wallet = IndyWallet(
                {
                    "auto_create": False,
                    "auto_remove": True,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            with pytest.raises(test_module.WalletError) as excinfo:
                await fake_wallet.create()
            assert "outlier" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_mock_coverage_remove_x(self):
        """
        Coverage through mock framework: exception on removal.
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            mock_delete.side_effect = test_module.IndyError(
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            fake_wallet = IndyWallet(
                {
                    "auto_create": False,
                    "auto_remove": False,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            mock_load.assert_called_once_with(storage_config_json, storage_creds_json)
            await fake_wallet.create()
            await fake_wallet.open()
            assert fake_wallet._wallet_access
            await fake_wallet.close()
            with pytest.raises(test_module.WalletError) as excinfo:
                await fake_wallet.remove()
            assert "outlier" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_mock_coverage_double_open(self):
        """
        Coverage through mock framework: double-open (no-op).
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            fake_wallet = IndyWallet(
                {
                    "auto_create": False,
                    "auto_remove": False,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            mock_load.assert_called_once_with(storage_config_json, storage_creds_json)
            await fake_wallet.create()
            await fake_wallet.open()
            fake_wallet._handle = 1234
            await fake_wallet.open()  # open an open wallet: should be OK
            assert fake_wallet._wallet_access
            await fake_wallet.close()
            await fake_wallet.remove()

    @pytest.mark.asyncio
    async def test_mock_coverage_not_found_after_creation(self):
        """
        Coverage through mock framework: missing created wallet.
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            mock_open.side_effect = test_module.IndyError(
                test_module.ErrorCode.WalletNotFoundError, {"message": "outlier"}
            )
            fake_wallet = IndyWallet(
                {
                    "auto_create": True,
                    "auto_remove": True,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            mock_load.assert_called_once_with(storage_config_json, storage_creds_json)
            await fake_wallet.create()
            with pytest.raises(test_module.WalletError) as excinfo:
                await fake_wallet.open()
            assert "outlier" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_mock_coverage_open_not_found(self):
        """
        Coverage through mock framework: missing wallet on open.
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            mock_open.side_effect = test_module.IndyError(
                test_module.ErrorCode.WalletNotFoundError, {"message": "outlier"}
            )
            fake_wallet = IndyWallet(
                {
                    "auto_create": False,
                    "auto_remove": True,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            mock_load.assert_called_once_with(storage_config_json, storage_creds_json)
            await fake_wallet.create()
            with pytest.raises(test_module.WalletNotFoundError) as excinfo:
                await fake_wallet.open()
            assert "Wallet test_pg_wallet not found" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_mock_coverage_open_indy_already_open_x(self):
        """
        Coverage through mock framework: indy thinks wallet is open, aca-py does not.
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            mock_open.side_effect = test_module.IndyError(
                test_module.ErrorCode.WalletAlreadyOpenedError, {"message": "outlier"}
            )
            fake_wallet = IndyWallet(
                {
                    "auto_create": False,
                    "auto_remove": True,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            mock_load.assert_called_once_with(storage_config_json, storage_creds_json)
            await fake_wallet.create()
            with pytest.raises(test_module.WalletError) as excinfo:
                await fake_wallet.open()
            assert "Wallet test_pg_wallet is already open" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_mock_coverage_open_x(self):
        """
        Coverage through mock framework: outlier on wallet open.
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            mock_open.side_effect = test_module.IndyError(
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            fake_wallet = IndyWallet(
                {
                    "auto_create": False,
                    "auto_remove": True,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            mock_load.assert_called_once_with(storage_config_json, storage_creds_json)
            await fake_wallet.create()
            with pytest.raises(test_module.WalletError) as excinfo:
                await fake_wallet.open()
            assert "outlier" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_mock_coverage_open_master_secret_x(self):
        """
        Coverage through mock framework: outlier on master secret creation
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            mock_master.side_effect = test_module.IndyError(
                test_module.ErrorCode.CommonIOError, {"message": "outlier"}
            )
            fake_wallet = IndyWallet(
                {
                    "auto_create": False,
                    "auto_remove": True,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            mock_load.assert_called_once_with(storage_config_json, storage_creds_json)
            await fake_wallet.create()
            with pytest.raises(test_module.WalletError) as excinfo:
                await fake_wallet.open()
            assert "outlier" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_mock_coverage_open_master_secret_exists(self):
        """
        Coverage through mock framework: open, master secret exists (OK).
        """
        wallet_key = await IndyWallet.generate_wallet_key()
        storage_config_json = json.dumps({"url": "dummy"})
        storage_creds_json = json.dumps(
            {
                "account": "postgres",
                "password": "mysecretpassword",
                "admin_account": "postgres",
                "admin_password": "mysecretpassword",
            },
        )
        with async_mock.patch.object(
            test_module, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            mock_master.side_effect = test_module.IndyError(
                test_module.ErrorCode.AnoncredsMasterSecretDuplicateNameError
            )
            fake_wallet = IndyWallet(
                {
                    "auto_create": False,
                    "auto_remove": False,
                    "name": "test_pg_wallet",
                    "key": wallet_key,
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": storage_config_json,
                    "storage_creds": storage_creds_json,
                }
            )
            mock_load.assert_called_once_with(storage_config_json, storage_creds_json)
            await fake_wallet.create()
            await fake_wallet.open()
            assert fake_wallet._master_secret_id == fake_wallet.name
            fake_wallet._handle = 1234
            await fake_wallet.open()  # open an open wallet: should be OK
            assert fake_wallet._wallet_access
            await fake_wallet.close()
            await fake_wallet.remove()

    # TODO get these to run in docker ci/cd
    @pytest.mark.asyncio
    @pytest.mark.postgres
    async def test_postgres_wallet_works(self):
        """
        Ensure that postgres wallet operations work (create and open wallet, create did, drop wallet)
        """
        postgres_url = os.environ.get("POSTGRES_URL")
        if not postgres_url:
            pytest.fail("POSTGRES_URL not configured")

        wallet_key = await IndyWallet.generate_wallet_key()
        postgres_wallet = IndyWallet(
            {
                "auto_create": False,
                "auto_remove": False,
                "name": "test_pg_wallet",
                "key": wallet_key,
                "key_derivation_method": "RAW",
                "storage_type": "postgres_storage",
                "storage_config": '{"url":"' + postgres_url + '"}',
                "storage_creds": '{"account":"postgres","password":"mysecretpassword","admin_account":"postgres","admin_password":"mysecretpassword"}',
            }
        )
        await postgres_wallet.create()
        await postgres_wallet.open()

        assert postgres_wallet._wallet_access

        await postgres_wallet.create_local_did(self.test_seed)
        py_packed = await postgres_wallet.pack_message(
            self.test_message, [self.test_verkey], self.test_verkey
        )

        await postgres_wallet.close()
        await postgres_wallet.remove()

    # TODO get these to run in docker ci/cd
    @pytest.mark.asyncio
    @pytest.mark.postgres
    async def test_postgres_wallet_scheme_works(self):
        """
        Ensure that postgres wallet operations work (create and open wallet, create did, drop wallet)
        """
        postgres_url = os.environ.get("POSTGRES_URL")
        if not postgres_url:
            pytest.fail("POSTGRES_URL not configured")

        wallet_key = await IndyWallet.generate_wallet_key()
        postgres_wallet = IndyWallet(
            {
                "auto_create": False,
                "auto_remove": False,
                "name": "test_pg_wallet",
                "key": wallet_key,
                "key_derivation_method": "RAW",
                "storage_type": "postgres_storage",
                "storage_config": '{"url":"'
                + postgres_url
                + '", "wallet_scheme":"MultiWalletSingleTable"}',
                "storage_creds": '{"account":"postgres","password":"mysecretpassword","admin_account":"postgres","admin_password":"mysecretpassword"}',
            }
        )
        await postgres_wallet.create()
        await postgres_wallet.open()

        with pytest.raises(WalletError) as excinfo:
            await wallet.create()
        assert "Wallet was not removed" in str(excinfo.value)

        await postgres_wallet.create_local_did(self.test_seed)
        py_packed = await postgres_wallet.pack_message(
            self.test_message, [self.test_verkey], self.test_verkey
        )

        await postgres_wallet.close()
        await postgres_wallet.remove()

    # TODO get these to run in docker ci/cd
    @pytest.mark.asyncio
    @pytest.mark.postgres
    async def test_postgres_wallet_scheme2_works(self):
        """
        Ensure that postgres wallet operations work (create and open wallet, create did, drop wallet)
        """
        postgres_url = os.environ.get("POSTGRES_URL")
        if not postgres_url:
            pytest.fail("POSTGRES_URL not configured")

        wallet_key = await IndyWallet.generate_wallet_key()
        postgres_wallet = IndyWallet(
            {
                "auto_create": False,
                "auto_remove": False,
                "name": "test_pg_wallet",
                "key": wallet_key,
                "key_derivation_method": "RAW",
                "storage_type": "postgres_storage",
                "storage_config": '{"url":"'
                + postgres_url
                + '", "wallet_scheme":"MultiWalletSingleTableSharedPool"}',
                "storage_creds": '{"account":"postgres","password":"mysecretpassword","admin_account":"postgres","admin_password":"mysecretpassword"}',
            }
        )
        await postgres_wallet.create()
        await postgres_wallet.open()

        await postgres_wallet.create_local_did(self.test_seed)
        py_packed = await postgres_wallet.pack_message(
            self.test_message, [self.test_verkey], self.test_verkey
        )

        await postgres_wallet.close()
        await postgres_wallet.remove()
