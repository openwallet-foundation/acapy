import types

import pytest


@pytest.fixture
def patched_v1(monkeypatch):
    from acapy_agent.kanon.didcomm import v1 as module

    class _KeyAlg:
        ED25519 = types.SimpleNamespace(value="ed25519")
        X25519 = types.SimpleNamespace(value="x25519")
        C20P = types.SimpleNamespace(value="c20p")

    class _Key:
        def __init__(self, alg=None):
            self._alg = alg
            self._handle = object()

        @staticmethod
        def generate(alg, *a, **k):
            return _Key(alg)

        @staticmethod
        def from_secret_bytes(alg, secret):
            return _Key(alg)

        @staticmethod
        def from_public_bytes(alg, public):
            return _Key(alg)

        def get_public_bytes(self):
            return b"pub"

        def convert_key(self, alg):
            return self

        def aead_encrypt(self, message, aad=None):
            return types.SimpleNamespace(parts=(b"ct", b"tag", b"iv"))

        def aead_decrypt(self, *a, **k):
            return b"msg"

    class _Jwe:
        def __init__(self, *a, **k):
            self._recips = []
            self.protected = {}
            self.protected_bytes = b"p"
            self.ciphertext = b"ct"
            self.tag = b"tag"
            self.iv = b"iv"

        def add_recipient(self, r):
            self._recips.append(r)

        def set_protected(self, prot):
            self.protected = prot

        def set_payload(self, ciphertext, nonce, tag):
            self.ciphertext, self.iv, self.tag = ciphertext, nonce, tag

        def to_json(self):
            return "{}"

        @staticmethod
        def from_json(enc):
            env = _Jwe()
            env.protected = {"alg": "Anoncrypt"}
            env.recipients = []
            return env

    # crypto helpers
    monkeypatch.setattr(module, "KeyAlg", _KeyAlg)
    monkeypatch.setattr(module, "Key", _Key)
    monkeypatch.setattr(module, "key_get_secret_bytes", lambda h: b"sek")
    monkeypatch.setattr(module, "JweEnvelope", _Jwe)
    monkeypatch.setattr(module, "b58_to_bytes", lambda s: b"vk")
    monkeypatch.setattr(module, "bytes_to_b58", lambda b: "vk")

    class _CryptoBox:
        @staticmethod
        def crypto_box_seal(pk, msg):
            return b"sender"

        @staticmethod
        def random_nonce():
            return b"n"

        @staticmethod
        def crypto_box(pk, sk, cek_b, nonce):
            return b"k"

    monkeypatch.setattr(module, "crypto_box", _CryptoBox)

    return module


@pytest.mark.asyncio
async def test_pack_message_anon_and_auth(patched_v1):
    m = patched_v1
    out = m.pack_message(["vk1"], None, b"{}")
    assert isinstance(out, (bytes, bytearray))
    fk = m.Key.generate(m.KeyAlg.ED25519)
    out2 = m.pack_message(["vk1"], fk, b"{}")
    assert isinstance(out2, (bytes, bytearray))


@pytest.mark.asyncio
async def test_unpack_message_no_recipient_key(patched_v1, monkeypatch):
    m = patched_v1
    monkeypatch.setattr(m, "extract_pack_recipients", lambda recips: {"vkX": {}})

    class _Sess:
        async def fetch_key(self, name):
            return None

    with pytest.raises(m.WalletError):
        await m.unpack_message(_Sess(), b"{}")


@pytest.mark.asyncio
async def test_unpack_message_auth_missing_sender(patched_v1, monkeypatch):
    m = patched_v1

    class _Jwe(m.JweEnvelope):
        @staticmethod
        def from_json(enc):
            env = m.JweEnvelope()
            env.protected = {"alg": "Authcrypt"}
            env.recipients = []
            return env

    monkeypatch.setattr(m, "JweEnvelope", _Jwe)
    monkeypatch.setattr(m, "extract_pack_recipients", lambda recips: {"vkX": {}})

    class _Sess:
        async def fetch_key(self, name):
            return types.SimpleNamespace(key=m.Key.generate(m.KeyAlg.ED25519))

    monkeypatch.setattr(m, "_extract_payload_key", lambda s, k: (b"cek", None))
    with pytest.raises(m.WalletError):
        await m.unpack_message(_Sess(), b"{}")


@pytest.mark.asyncio
async def test_unpack_message_success(patched_v1, monkeypatch):
    m = patched_v1
    monkeypatch.setattr(m, "extract_pack_recipients", lambda recips: {"vkX": {}})

    class _Sess:
        async def fetch_key(self, name):
            return types.SimpleNamespace(key=m.Key.generate(m.KeyAlg.ED25519))

    monkeypatch.setattr(m, "_extract_payload_key", lambda s, k: (b"cek", "sender"))
    msg, recip, sender = await m.unpack_message(_Sess(), b"{}")
    assert msg == b"msg"
    assert recip == "vkX"
    assert sender == "sender"
