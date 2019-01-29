import pytest

from indy_catalyst_agent.wallet import WalletException
from indy_catalyst_agent.wallet.basic import BasicWallet

@pytest.fixture()
def wallet():
    yield BasicWallet()


class TestBasicWallet:
    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_metadata = {"meta": True}
    test_update_metadata = {"meta": False}
    test_message = "test message"
    missing_verkey = "__missing__"
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
        did = await wallet.create_local_did(None, None)
        assert did

    @pytest.mark.asyncio
    async def test_create_local_seeded(self, wallet):
        await wallet.open()
        did = await wallet.create_local_did(self.test_seed, None)
        assert did == self.test_did
        verkey = await wallet.get_local_verkey_for_did(did)
        assert verkey == self.test_verkey
        await wallet.close()

    @pytest.mark.asyncio
    async def test_create_local_with_did(self, wallet):
        await wallet.open()
        did = await wallet.create_local_did(None, self.test_did)
        assert did is self.test_did
        await wallet.close()

    @pytest.mark.asyncio
    async def test_create_invalid_seed(self, wallet):
        await wallet.open()
        with pytest.raises(WalletException):
            _did = await wallet.create_local_did("invalid-seed", None)
        await wallet.close()

    @pytest.mark.asyncio
    async def test_missing_verkey(self, wallet):
        await wallet.open()
        with pytest.raises(WalletException):
            _did = await wallet.get_local_did_for_verkey(self.missing_verkey)
        await wallet.close()

    @pytest.mark.asyncio
    async def test_local_metadata(self, wallet):
        await wallet.open()
        did = await wallet.create_local_did(self.test_seed, self.test_did, self.test_metadata)
        meta = await wallet.get_local_did_metadata(did)
        assert meta == self.test_metadata
        await wallet.replace_local_did_metadata(did, self.test_update_metadata)
        meta2 = await wallet.get_local_did_metadata(did)
        assert meta2 == self.test_update_metadata

    @pytest.mark.asyncio
    async def test_sign_verify(self, wallet):
        await wallet.open()
        did = await wallet.create_local_did(self.test_seed, self.test_did)
        verkey = await wallet.get_local_verkey_for_did(did)
        message_bin = self.test_message.encode("ascii")
        signature = await wallet.sign_message(message_bin, verkey)
        assert signature == self.test_signature
        verify = await wallet.verify_message(message_bin, signature, verkey)
        assert verify

    @pytest.mark.asyncio
    async def test_bad_signature(self, wallet):
        await wallet.open()
        did = await wallet.create_local_did(self.test_seed, self.test_did)
        verkey = await wallet.get_local_verkey_for_did(did)
        message_bin = self.test_message.encode("ascii")
        signature = await wallet.sign_message(message_bin, verkey)
        assert signature == self.test_signature
        verify = await wallet.verify_message(message_bin, signature, verkey)
        assert verify

    @pytest.mark.asyncio
    async def test_pack_unpack_anon(self, wallet):
        await wallet.open()
        packed = await wallet.pack_message(self.test_message, [self.test_verkey])
        did = await wallet.create_local_did(self.test_seed, self.test_did)
        unpacked, from_verkey = await wallet.unpack_message(packed)
        assert self.test_message == unpacked
        assert from_verkey is None

    @pytest.mark.asyncio
    async def test_pack_unpack_auth(self, wallet):
        await wallet.open()
        did = await wallet.create_local_did(self.test_seed, self.test_did)
        packed = await wallet.pack_message(self.test_message, [self.test_verkey], self.test_verkey)
        unpacked, from_verkey = await wallet.unpack_message(packed)
        assert self.test_message == unpacked
        assert from_verkey == self.test_verkey
