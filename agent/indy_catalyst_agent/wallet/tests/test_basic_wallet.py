import pytest

from indy_catalyst_agent.wallet.basic import BasicWallet
from indy_catalyst_agent.wallet.error import (
    WalletException, WalletDuplicateException, WalletNotFoundException,
)


@pytest.fixture()
def wallet():
    yield BasicWallet()


class TestBasicWallet:
    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_target_seed = "testseed000000000000000000000002"
    test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
    test_target_verkey = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
    test_metadata = {"meta": True}
    test_update_metadata = {"meta": False}
    test_message = "test message"
    missing_did = "YVnYBGTdjZUoQXKQjHV87i"
    missing_verkey = "JAfHCRDH9ZW5E7m4mofjr8cpAHaZdiRQ94it75aXUPK3"
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
            info = await wallet.create_local_did(None, None)
            assert info and info.did and info.verkey
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_create_local_seeded(self, wallet):
        await wallet.open()
        try:
            info = await wallet.create_local_did(self.test_seed, None)
            assert info.did == self.test_did
            assert info.verkey == self.test_verkey

            with pytest.raises(WalletDuplicateException):
                await wallet.create_local_did(self.test_seed, None)
            with pytest.raises(WalletException):
                _info = await wallet.create_local_did("invalid-seed", None)
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_create_local_with_did(self, wallet):
        await wallet.open()
        try:
            info = await wallet.create_local_did(None, self.test_did)
            assert info.did == self.test_did

            with pytest.raises(WalletDuplicateException):
                await wallet.create_local_did(None, self.test_did)
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_local_verkey(self, wallet):
        await wallet.open()
        try:
            info = await wallet.create_local_did(self.test_seed, self.test_did)
            assert info.did == self.test_did
            assert info.verkey == self.test_verkey

            info2 = await wallet.get_local_did(self.test_did)
            assert info2.did == self.test_did
            assert info2.verkey == self.test_verkey

            info3 = await wallet.get_local_did_for_verkey(self.test_verkey)
            assert info3.did == self.test_did
            assert info3.verkey == self.test_verkey

            with pytest.raises(WalletNotFoundException):
                _info = await wallet.get_local_did(self.missing_did)
            with pytest.raises(WalletNotFoundException):
                _info = await wallet.get_local_did_for_verkey(self.missing_verkey)
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_local_metadata(self, wallet):
        await wallet.open()
        try:
            info = await wallet.create_local_did(
                self.test_seed, self.test_did, self.test_metadata)
            assert info.metadata == self.test_metadata
            info2 = await wallet.get_local_did(self.test_did)
            assert info2.metadata == self.test_metadata
            await wallet.replace_local_did_metadata(
                self.test_did, self.test_update_metadata)
            info3 = await wallet.get_local_did(self.test_did)
            assert info3.metadata == self.test_update_metadata

            with pytest.raises(WalletNotFoundException):
                await wallet.replace_local_did_metadata(
                    self.missing_did, self.test_update_metadata)
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_create_pairwise(self, wallet):
        await wallet.open()
        try:
            await wallet.create_local_did(self.test_seed, self.test_did)
            pair_created = await wallet.create_pairwise(
                self.test_target_did, self.test_target_verkey, None, self.test_metadata)
            assert pair_created.their_did == self.test_target_did
            assert pair_created.their_verkey == self.test_target_verkey
            assert pair_created.my_did
            assert pair_created.my_verkey
            assert pair_created.metadata == self.test_metadata

            pair_info = await wallet.get_pairwise_for_did(self.test_target_did)
            assert pair_info == pair_created

            pair_info_vk = await wallet.get_pairwise_for_verkey(self.test_target_verkey)
            assert pair_info_vk == pair_created

            pair_infos = await wallet.get_pairwise_list()
            found = False
            for info in pair_infos:
                if info == pair_created:
                    assert not found
                    found = True
            assert found

            # TODO - test metadata update

            with pytest.raises(WalletDuplicateException):
                await wallet.create_pairwise(
                    self.test_target_did, self.test_target_verkey, None, self.test_metadata)
            with pytest.raises(WalletNotFoundException):
                await wallet.get_pairwise_for_did(self.missing_did)
            with pytest.raises(WalletNotFoundException):
                await wallet.replace_pairwise_metadata(
                    self.missing_did, self.test_update_metadata)
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_sign_verify(self, wallet):
        await wallet.open()
        try:
            info = await wallet.create_local_did(self.test_seed, self.test_did)
            message_bin = self.test_message.encode("ascii")
            signature = await wallet.sign_message(message_bin, info.verkey)
            assert signature == self.test_signature
            verify = await wallet.verify_message(message_bin, signature, info.verkey)
            assert verify

            bad_sig = b'x' + signature[1:]
            verify = await wallet.verify_message(message_bin, bad_sig, info.verkey)
            assert not verify
            bad_msg = b'x' + message_bin[1:]
            verify = await wallet.verify_message(bad_msg, signature, info.verkey)
            assert not verify
            verify = await wallet.verify_message(
                message_bin, signature, self.test_target_verkey)
            assert not verify
        finally:
            await wallet.close()

    @pytest.mark.asyncio
    async def test_pack_unpack(self, wallet):
        await wallet.open()
        try:
            await wallet.create_local_did(self.test_seed, self.test_did)
            packed_anon = await wallet.pack_message(self.test_message, [self.test_verkey])
            unpacked_anon, from_verkey, to_verkey = await wallet.unpack_message(packed_anon)
            assert unpacked_anon == self.test_message
            assert from_verkey is None
            assert to_verkey == self.test_verkey

            await wallet.create_local_did(self.test_target_seed, self.test_target_did)
            packed_auth = await wallet.pack_message(
                self.test_message, [self.test_target_verkey], self.test_verkey)
            unpacked_auth, from_verkey, to_verkey = await wallet.unpack_message(packed_auth)
            assert unpacked_auth == self.test_message
            assert from_verkey == self.test_verkey
            assert to_verkey == self.test_target_verkey
        finally:
            await wallet.close()
