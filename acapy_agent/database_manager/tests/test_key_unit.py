import pytest

from acapy_agent.database_manager.db_types import KeyAlg, SeedMethod
from acapy_agent.database_manager.key import Key


def test_key_not_implemented_classmethods_and_ops():
    with pytest.raises(NotImplementedError):
        Key.generate(KeyAlg.A128GCM)
    with pytest.raises(NotImplementedError):
        Key.from_seed(KeyAlg.A128GCM, b"seed", method=SeedMethod.BlsKeyGen)
    with pytest.raises(NotImplementedError):
        Key.from_secret_bytes(KeyAlg.A128GCM, b"secret")
    with pytest.raises(NotImplementedError):
        Key.from_public_bytes(KeyAlg.A128GCM, b"public")
    with pytest.raises(NotImplementedError):
        Key.from_jwk({"kty": "oct"})

    k = Key(handle="h1")
    with pytest.raises(NotImplementedError):
        k.convert_key(KeyAlg.A128GCM)
    with pytest.raises(NotImplementedError):
        k.key_exchange(KeyAlg.A128GCM, Key("h2"))
    with pytest.raises(NotImplementedError):
        k.sign_message(b"msg")
    with pytest.raises(NotImplementedError):
        k.verify_signature(b"msg", b"sig")


def test_key_placeholders_and_repr():
    k = Key(handle="h1")
    assert k.handle == "h1"
    assert k.algorithm == KeyAlg.A128GCM
    assert k.ephemeral is False
    assert k.get_public_bytes() == b"public_bytes_placeholder"
    assert k.get_secret_bytes() == b"secret_bytes_placeholder"
    assert k.get_jwk_public() == "jwk_public_placeholder"
    assert k.get_jwk_secret() == b"jwk_secret_placeholder"
    assert k.get_jwk_thumbprint() == "jwk_thumbprint_placeholder"
    assert k.aead_params() == "AeadParams placeholder"
    assert k.aead_random_nonce() == b"nonce_placeholder"
    assert k.aead_encrypt(b"m") == "Encrypted placeholder"
    assert k.aead_decrypt(b"c", nonce=b"n") == b"decrypted placeholder"
    assert k.wrap_key(Key("h2")) == "Encrypted placeholder"
    r = repr(k)
    assert "Key(" in r and "handle=h1" in r
