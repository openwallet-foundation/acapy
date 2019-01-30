import pytest

_indy = pytest.importorskip("indy")

from indy_catalyst_agent.wallet.basic import BasicWallet
from indy_catalyst_agent.wallet.error import WalletException, WalletNotFoundException
from indy_catalyst_agent.wallet.indy import IndyWallet

from indy import crypto, did, wallet

import json

@pytest.fixture()
def basic_wallet():
    yield BasicWallet()

@pytest.fixture()
def wallet():
    yield IndyWallet({
        "auto_create": True,
        "auto_remove": True,
        "name": "test-wallet",
        "seed": "testseed00000000000000000000skip",
    })


class TestIndyWallet:
    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_metadata = {"meta": True}
    test_update_metadata = {"meta": False}
    test_message = "test message"
    missing_did = "55GkHamhTU1ZbTbV2ab9DF"
    missing_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRy"
    test_signature = b"\xd6\x98\x04\x88\xd2-\xc1D\x02\x15\xc9Z\x9bK \x8f\xe0\x8b5\xd0Z$" \
                     b"\xe3\x02\x19\xa1\xb3\x86\xfa2\x07\xc8\xbd3-\x1c\xc4\x8d\x8e\xa3\x9be" \
                     b"\xea\xcf\x8bc\xfa_\x0c\xb2jE\xe4}\x12+\xbc0\x01l\xdb\x97\xf6\x02"

    @pytest.mark.asyncio
    async def test_open_close_wallet(self, wallet):
        await wallet.open()
        await wallet.close()

    @pytest.mark.asyncio
    async def test_create_local_random(self, wallet):
        await wallet.open()
        try:
            did = await wallet.create_local_did(None, None)
            assert did
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_create_local_seeded(self, wallet):
        await wallet.open()
        try:
            did = await wallet.create_local_did(self.test_seed, None)
            assert did == self.test_did
            verkey = await wallet.get_local_verkey_for_did(did)
            assert verkey == self.test_verkey
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_create_local_with_did(self, wallet):
        await wallet.open()
        try:
            did = await wallet.create_local_did(None, self.test_did)
            assert did == self.test_did
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_create_invalid_seed(self, wallet):
        await wallet.open()
        try:
            with pytest.raises(WalletException):
                _did = await wallet.create_local_did("invalid-seed", None)
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_local_verkey(self, wallet):
        await wallet.open()
        try:
            did = await wallet.create_local_did(self.test_seed, self.test_did)
            did2 = await wallet.get_local_did_for_verkey(self.test_verkey)
            assert did == did2
            verkey = await wallet.get_local_verkey_for_did(self.test_did)
            assert verkey == self.test_verkey

            with pytest.raises(WalletNotFoundException):
                _did = await wallet.get_local_did_for_verkey(self.missing_verkey)
            with pytest.raises(WalletNotFoundException):
                _vk = await wallet.get_local_verkey_for_did(self.missing_did)
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_local_metadata(self, wallet):
        await wallet.open()
        try:
            did = await wallet.create_local_did(self.test_seed, self.test_did, self.test_metadata)
            meta = await wallet.get_local_did_metadata(did)
            assert meta == self.test_metadata
            await wallet.replace_local_did_metadata(did, self.test_update_metadata)
            meta2 = await wallet.get_local_did_metadata(did)
            assert meta2 == self.test_update_metadata

            with pytest.raises(WalletNotFoundException):
                meta3 = await wallet.get_local_did_metadata(self.missing_did)
            with pytest.raises(WalletNotFoundException):
                await wallet.replace_local_did_metadata(self.missing_did, self.test_update_metadata)
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_sign_verify(self, wallet):
        await wallet.open()
        try:
            did = await wallet.create_local_did(self.test_seed, self.test_did)
            verkey = await wallet.get_local_verkey_for_did(did)
            message_bin = self.test_message.encode("ascii")
            signature = await wallet.sign_message(message_bin, verkey)
            assert signature == self.test_signature
            verify = await wallet.verify_message(message_bin, signature, verkey)
            assert verify
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_bad_signature(self, wallet):
        await wallet.open()
        try:
            did = await wallet.create_local_did(self.test_seed, self.test_did)
            verkey = await wallet.get_local_verkey_for_did(did)
            message_bin = self.test_message.encode("ascii")
            signature = await wallet.sign_message(message_bin, verkey)
            assert signature == self.test_signature
            verify = await wallet.verify_message(message_bin, signature, verkey)
            assert verify
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_pack_unpack(self, wallet):
        await wallet.open()
        try:
            did = await wallet.create_local_did(self.test_seed, self.test_did)
            packed_anon = await wallet.pack_message(self.test_message, [self.test_verkey])
            unpacked_anon, from_verkey, to_verkey = await wallet.unpack_message(packed_anon)
            assert unpacked_anon == self.test_message
            assert from_verkey is None
            assert to_verkey == self.test_verkey

            packed_auth = await wallet.pack_message(self.test_message, [self.test_verkey], self.test_verkey)
            unpacked_auth, from_verkey, to_verkey = await wallet.unpack_message(packed_auth)
            assert unpacked_auth == self.test_message
            assert from_verkey == self.test_verkey
            assert to_verkey == self.test_verkey
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_compare_pack(self, basic_wallet, wallet):
        """
        Ensure that python-based pack/unpack is compatible with indy-sdk implementation
        """
        await basic_wallet.open()
        await basic_wallet.create_local_did(self.test_seed)
        py_packed = await basic_wallet.pack_message(
            self.test_message,
            [self.test_verkey],
            self.test_verkey,
        )

        await wallet.open()
        try:
            await wallet.create_local_did(self.test_seed)
            packed = await wallet.pack_message(
                self.test_message,
                [self.test_verkey],
                self.test_verkey,
            )

            py_unpacked, from_vk, to_vk = await basic_wallet.unpack_message(packed)

            assert self.test_message == py_unpacked

            unpacked, from_vk, to_vk = await wallet.unpack_message(py_packed)

            assert self.test_message == unpacked
        finally:
            await wallet.close()
        await basic_wallet.close()
