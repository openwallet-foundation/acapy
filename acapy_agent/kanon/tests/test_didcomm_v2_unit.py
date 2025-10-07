import types

import pytest


@pytest.fixture
def patched_v2(monkeypatch):
    from acapy_agent.kanon.didcomm import v2 as module

    class _KeyAlg:
        A256KW = types.SimpleNamespace(value="a256kw")
        XC20P = types.SimpleNamespace(value="xc20p")
        A256CBC_HS512 = types.SimpleNamespace(value="a256cbc")

    class _Key:
        def __init__(self, alg=None):
            self.algorithm = alg

        @staticmethod
        def generate(alg, *a, **k):
            return _Key(alg)

        @staticmethod
        def from_jwk(jwk):
            return _Key(_KeyAlg.A256KW)

        def get_jwk_public(self):
            return "{}"

        def aead_encrypt(self, message, aad=None):
            return types.SimpleNamespace(ciphertext=b"ct", nonce=b"n", tag=b"t")

        def aead_decrypt(self, *a, **k):
            return b"msg"

    class _Wrap:
        def __init__(self, *a, **k):
            pass

        def sender_wrap_key(self, wrap_alg, epk, recip_key, cek, cc_tag=None):
            return types.SimpleNamespace(ciphertext=b"ek")

        def receiver_unwrap_key(self, *a, **k):
            return _Key(_KeyAlg.XC20P)

    class _Ecdh:
        EcdhEs = _Wrap
        Ecdh1PU = _Wrap

    class _Jwe:
        def __init__(self, *a, **k):
            self._recips = []
            self.protected = {}
            self.protected_bytes = b"p"
            self.ciphertext = b"ct"
            self.tag = b"t"
            self.iv = b"n"
            self.recipient_key_ids = []
            self.combined_aad = b"aad"

        def add_recipient(self, r):
            self._recips.append(r)

        def set_protected(self, prot):
            self.protected = prot

        def set_payload(self, ciphertext, nonce, tag):
            self.ciphertext, self.iv, self.tag = ciphertext, nonce, tag

        def get_recipient(self, kid):
            return types.SimpleNamespace(
                encrypted_key=b"ek", header={"enc": "XC20P", "epk": "{}"}
            )

        def to_json(self):
            return "{}"

        @staticmethod
        def from_json(enc):
            env = _Jwe()
            env.protected = {"alg": "ECDH-ES+A256KW"}
            env.recipient_key_ids = ["rk"]
            return env

    monkeypatch.setattr(module, "KeyAlg", _KeyAlg)
    monkeypatch.setattr(module, "Key", _Key)
    monkeypatch.setattr(module, "ecdh", _Ecdh)
    monkeypatch.setattr(module, "JweEnvelope", _Jwe)

    return module


def _fake_session_with_kid(module, kid="rk"):
    class _Sess:
        async def fetch_all_keys(self, tag_filter=None):
            if tag_filter and tag_filter.get("kid") == kid:
                return [
                    types.SimpleNamespace(key=module.Key.generate(module.KeyAlg.A256KW))
                ]
            return []

    return _Sess()


def test_ecdh_es_encrypt_and_decrypt_flow(patched_v2):
    m = patched_v2
    recip = {"rk": m.Key.generate(m.KeyAlg.A256KW)}
    enc = m.ecdh_es_encrypt(recip, b"{}")
    assert isinstance(enc, (bytes, bytearray))


@pytest.mark.asyncio
async def test_unpack_message_es_success(patched_v2):
    m = patched_v2

    plaintext, recip_kid, sender_kid = await m.unpack_message(
        _fake_session_with_kid(m), b"{}"
    )
    assert plaintext == b"msg"
    assert recip_kid == "rk"
    assert sender_kid is None


@pytest.mark.asyncio
async def test_unpack_message_no_recipient_key(patched_v2):
    m = patched_v2
    with pytest.raises(m.DidcommEnvelopeError):
        await m.unpack_message(_fake_session_with_kid(m, kid="zz"), b"{}")


def test_validate_method_unsupported(patched_v2, monkeypatch):
    m = patched_v2

    class _Jwe(m.JweEnvelope):
        @staticmethod
        def from_json(enc):
            env = m.JweEnvelope()
            env.protected = {"alg": "XYZ"}
            return env

    monkeypatch.setattr(m, "JweEnvelope", _Jwe)
    with pytest.raises(m.DidcommEnvelopeError):
        m._validate_encryption_method(m.JweEnvelope.from_json(b"{}"))
