import pytest

try:
    from indy.libindy import _cdll

    _cdll()
except ImportError:
    pytest.skip(
        "skipping Indy-specific tests: python module not installed",
        allow_module_level=True,
    )
except OSError:
    pytest.skip(
        "skipping Indy-specific tests: shared library not loaded",
        allow_module_level=True,
    )

from indy_catalyst_agent.wallet.basic import BasicWallet
from indy_catalyst_agent.wallet.indy import IndyWallet
from indy_catalyst_agent.postgres import load_postgres_plugin

from . import test_basic_wallet


@pytest.fixture()
async def basic_wallet():
    wallet = BasicWallet()
    await wallet.open()
    yield wallet
    await wallet.close()


@pytest.fixture()
async def wallet():
    wallet = IndyWallet(
        {"auto_create": True, "auto_remove": True, "name": "test-wallet"}
    )
    await wallet.open()
    yield wallet
    await wallet.close()


class TestIndyWallet(test_basic_wallet.TestBasicWallet):
    """Apply all BasicWallet tests against IndyWallet"""


class TestWalletCompat:
    """ """

    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_message = "test message"

    @pytest.mark.asyncio
    async def test_compare_anon_encrypt(self, basic_wallet, wallet):
        """
        Ensure that python-based encrypt/decrypt is compatible with
        indy-sdk implementation
        """
        bin_msg = self.test_message.encode("ascii")

        await basic_wallet.create_local_did(self.test_seed)
        py_enc_message = await basic_wallet.encrypt_message(bin_msg, self.test_verkey)

        await wallet.create_local_did(self.test_seed)
        enc_message = await wallet.encrypt_message(bin_msg, self.test_verkey)

        py_decrypt, from_vk = await basic_wallet.decrypt_message(
            enc_message, self.test_verkey, False
        )
        assert py_decrypt == bin_msg
        assert from_vk is None

        decrypt, from_vk = await wallet.decrypt_message(
            py_enc_message, self.test_verkey, False
        )
        assert decrypt == bin_msg
        assert from_vk is None

    @pytest.mark.asyncio
    async def test_compare_auth_encrypt(self, basic_wallet, wallet):
        """
        Ensure that python-based encrypt/decrypt is compatible
        with indy-sdk implementation
        """
        bin_msg = self.test_message.encode("ascii")

        await basic_wallet.create_local_did(self.test_seed)
        py_enc_message = await basic_wallet.encrypt_message(
            bin_msg, self.test_verkey, self.test_verkey
        )

        await wallet.create_local_did(self.test_seed)
        enc_message = await wallet.encrypt_message(
            bin_msg, self.test_verkey, self.test_verkey
        )

        py_decrypt, from_vk = await basic_wallet.decrypt_message(
            enc_message, self.test_verkey, True
        )
        assert py_decrypt == bin_msg
        assert from_vk == self.test_verkey

        decrypt, from_vk = await wallet.decrypt_message(
            py_enc_message, self.test_verkey, True
        )
        assert decrypt == bin_msg
        assert from_vk == self.test_verkey

    @pytest.mark.asyncio
    async def test_compare_pack(self, basic_wallet, wallet):
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

    # TODO get these to run in docker ci/cd
    # @pytest.mark.asyncio
    async def test_postgres_wallet_works(self):
        """
        Ensure that postgres wallet operations work (create and open wallet, create did, drop wallet)
        """
        load_postgres_plugin()
        postgres_wallet = IndyWallet(
            {
                "auto_create": False,
                "auto_remove": False,
                "name": "test_pg_wallet",
                "key": "my_postgres",
                "storage_type": "postgres_storage",
                "storage_config": '{"url":"host.docker.internal:5432"}',
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
