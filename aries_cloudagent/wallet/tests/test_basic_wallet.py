import time

import pytest

from aries_cloudagent.wallet.basic import BasicWallet
from aries_cloudagent.wallet.error import (
    WalletError,
    WalletDuplicateError,
    WalletNotFoundError,
)

from aries_cloudagent.messaging.decorators.signature_decorator import SignatureDecorator


@pytest.fixture()
async def wallet():
    wallet = BasicWallet()
    await wallet.open()
    yield wallet
    await wallet.close()


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
    test_message_bytes = b"test message bytes"
    missing_did = "YVnYBGTdjZUoQXKQjHV87i"
    missing_verkey = "JAfHCRDH9ZW5E7m4mofjr8cpAHaZdiRQ94it75aXUPK3"
    test_signature = (
        b"\xd6\x98\x04\x88\xd2-\xc1D\x02\x15\xc9Z\x9bK \x8f\xe0\x8b5\xd0Z$"
        b"\xe3\x02\x19\xa1\xb3\x86\xfa2\x07\xc8\xbd3-\x1c\xc4\x8d\x8e\xa3\x9be"
        b"\xea\xcf\x8bc\xfa_\x0c\xb2jE\xe4}\x12+\xbc0\x01l\xdb\x97\xf6\x02"
    )

    @pytest.mark.asyncio
    async def test_create_signing_key_random(self, wallet):
        info = await wallet.create_signing_key()
        assert info and info.verkey

    @pytest.mark.asyncio
    async def test_create_signing_key_seeded(self, wallet):
        info = await wallet.create_signing_key(self.test_seed)
        assert info.verkey == self.test_verkey

        with pytest.raises(WalletDuplicateError):
            await wallet.create_signing_key(self.test_seed)
        with pytest.raises(WalletError):
            await wallet.create_signing_key("invalid-seed", None)

    @pytest.mark.asyncio
    async def test_signing_key_metadata(self, wallet):
        info = await wallet.create_signing_key(self.test_seed, self.test_metadata)
        assert info.metadata == self.test_metadata
        info2 = await wallet.get_signing_key(self.test_verkey)
        assert info2.metadata == self.test_metadata
        await wallet.replace_signing_key_metadata(
            self.test_verkey, self.test_update_metadata
        )
        info3 = await wallet.get_signing_key(self.test_verkey)
        assert info3.metadata == self.test_update_metadata

        with pytest.raises(WalletNotFoundError):
            await wallet.replace_signing_key_metadata(
                self.missing_verkey, self.test_update_metadata
            )

    @pytest.mark.asyncio
    async def test_create_local_random(self, wallet):
        info = await wallet.create_local_did(None, None)
        assert info and info.did and info.verkey

    @pytest.mark.asyncio
    async def test_create_local_seeded(self, wallet):
        info = await wallet.create_local_did(self.test_seed, None)
        assert info.did == self.test_did
        assert info.verkey == self.test_verkey

        # should not raise WalletDuplicateError - same verkey
        await wallet.create_local_did(self.test_seed, None)

        with pytest.raises(WalletError):
            _ = await wallet.create_local_did("invalid-seed", None)

    @pytest.mark.asyncio
    async def test_create_local_with_did(self, wallet):
        info = await wallet.create_local_did(None, self.test_did)
        assert info.did == self.test_did

        with pytest.raises(WalletDuplicateError):
            await wallet.create_local_did(None, self.test_did)

    @pytest.mark.asyncio
    async def test_local_verkey(self, wallet):
        info = await wallet.create_local_did(self.test_seed, self.test_did)
        assert info.did == self.test_did
        assert info.verkey == self.test_verkey

        info2 = await wallet.get_local_did(self.test_did)
        assert info2.did == self.test_did
        assert info2.verkey == self.test_verkey

        info3 = await wallet.get_local_did_for_verkey(self.test_verkey)
        assert info3.did == self.test_did
        assert info3.verkey == self.test_verkey

        with pytest.raises(WalletNotFoundError):
            _ = await wallet.get_local_did(self.missing_did)
        with pytest.raises(WalletNotFoundError):
            _ = await wallet.get_local_did_for_verkey(self.missing_verkey)

    @pytest.mark.asyncio
    async def test_local_metadata(self, wallet):
        info = await wallet.create_local_did(
            self.test_seed, self.test_did, self.test_metadata
        )
        assert info.metadata == self.test_metadata
        info2 = await wallet.get_local_did(self.test_did)
        assert info2.metadata == self.test_metadata
        await wallet.replace_local_did_metadata(
            self.test_did, self.test_update_metadata
        )
        info3 = await wallet.get_local_did(self.test_did)
        assert info3.metadata == self.test_update_metadata

        with pytest.raises(WalletNotFoundError):
            await wallet.replace_local_did_metadata(
                self.missing_did, self.test_update_metadata
            )

    @pytest.mark.asyncio
    async def test_create_public_did(self, wallet):
        info = await wallet.create_local_did(
            self.test_seed, self.test_did, self.test_metadata
        )
        assert not info.metadata.get("public")

        info_public = await wallet.create_public_did()
        assert info_public.metadata.get("public")

        # test replace
        info_replace = await wallet.create_public_did()
        assert info_replace.metadata.get("public")
        info_check = await wallet.get_local_did(info_public.did)
        assert not info_check.metadata.get("public")

    @pytest.mark.asyncio
    async def test_set_public_did(self, wallet):
        info = await wallet.create_local_did(
            self.test_seed, self.test_did, self.test_metadata
        )
        assert not info.metadata.get("public")

        with pytest.raises(WalletNotFoundError):
            await wallet.set_public_did("55GkHamhTU1ZbTbV2ab9DF")

        # test assign
        info_same = await wallet.set_public_did(info.did)
        assert info_same.did == info.did
        assert info_same.metadata.get("public")

        info_new = await wallet.create_local_did()
        assert info_new.did != info_same.did
        assert not info_new.metadata.get("public")

        # test replace
        info_final = await wallet.set_public_did(info_new.did)
        assert info_final.did == info_new.did
        assert info_final.metadata.get("public")

    @pytest.mark.asyncio
    async def test_sign_verify(self, wallet):
        info = await wallet.create_local_did(self.test_seed, self.test_did)
        message_bin = self.test_message.encode("ascii")
        signature = await wallet.sign_message(message_bin, info.verkey)
        assert signature == self.test_signature
        verify = await wallet.verify_message(message_bin, signature, info.verkey)
        assert verify

        bad_sig = b"x" + signature[1:]
        verify = await wallet.verify_message(message_bin, bad_sig, info.verkey)
        assert not verify
        bad_msg = b"x" + message_bin[1:]
        verify = await wallet.verify_message(bad_msg, signature, info.verkey)
        assert not verify
        verify = await wallet.verify_message(
            message_bin, signature, self.test_target_verkey
        )
        assert not verify

    @pytest.mark.asyncio
    async def test_pack_unpack(self, wallet):
        await wallet.create_local_did(self.test_seed, self.test_did)
        packed_anon = await wallet.pack_message(self.test_message, [self.test_verkey])
        unpacked_anon, from_verkey, to_verkey = await wallet.unpack_message(packed_anon)
        assert unpacked_anon == self.test_message
        assert from_verkey is None
        assert to_verkey == self.test_verkey

        await wallet.create_local_did(self.test_target_seed, self.test_target_did)
        packed_auth = await wallet.pack_message(
            self.test_message, [self.test_target_verkey], self.test_verkey
        )
        unpacked_auth, from_verkey, to_verkey = await wallet.unpack_message(packed_auth)
        assert unpacked_auth == self.test_message
        assert from_verkey == self.test_verkey
        assert to_verkey == self.test_target_verkey

        with pytest.raises(WalletError):
            unpacked_auth, from_verkey, to_verkey = await wallet.unpack_message(b"bad")
        with pytest.raises(WalletError):
            unpacked_auth, from_verkey, to_verkey = await wallet.unpack_message(b"{}")

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_dids(self, wallet):
        await wallet.create_local_did(self.test_seed, self.test_did)
        encrypted_msg = await wallet.encrypt_message(
            self.test_message_bytes, self.test_verkey
        )
        decrypted_msg, sender_verkey = await wallet.decrypt_message(
            encrypted_msg, self.test_verkey, False
        )
        assert decrypted_msg == self.test_message_bytes
        assert sender_verkey is None

        await wallet.create_local_did(self.test_target_seed, self.test_target_did)
        encrypted_msg = await wallet.encrypt_message(
            self.test_message_bytes, self.test_target_verkey, self.test_verkey
        )
        decrypted_msg, sender_verkey = await wallet.decrypt_message(
            encrypted_msg, self.test_target_verkey, True
        )
        assert decrypted_msg == self.test_message_bytes
        assert sender_verkey == self.test_verkey

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_keys(self, wallet):
        key_info = await wallet.create_signing_key()
        encrypted_msg = await wallet.encrypt_message(
            self.test_message_bytes, key_info.verkey
        )
        decrypted_msg, sender_verkey = await wallet.decrypt_message(
            encrypted_msg, key_info.verkey, False
        )
        assert decrypted_msg == self.test_message_bytes
        assert sender_verkey is None

        target_key_info = await wallet.create_signing_key()
        encrypted_msg = await wallet.encrypt_message(
            self.test_message_bytes, target_key_info.verkey, key_info.verkey
        )
        decrypted_msg, sender_verkey = await wallet.decrypt_message(
            encrypted_msg, target_key_info.verkey, True
        )
        assert decrypted_msg == self.test_message_bytes
        assert sender_verkey == key_info.verkey

    @pytest.mark.asyncio
    async def test_signature_round_trip(self, wallet):
        key_info = await wallet.create_signing_key()
        msg = {"test": "signed field"}
        timestamp = int(time.time())
        sig = await SignatureDecorator.create(msg, key_info.verkey, wallet, timestamp)
        verified = await sig.verify(wallet)
        assert verified
        msg_decode, ts_decode = sig.decode()
        assert msg_decode == msg
        assert ts_decode == timestamp
