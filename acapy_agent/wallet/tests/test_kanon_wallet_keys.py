import types
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pytest


@dataclass
class FakeKeyAlg:
    value: str


class FakeKey:
    _seq = 0

    def __init__(self, algorithm: FakeKeyAlg, public_bytes: bytes, secret_bytes: bytes):
        self.algorithm = algorithm
        self._public = public_bytes
        self._secret = secret_bytes

    @staticmethod
    def generate(alg: Any):
        FakeKey._seq += 1
        pub = f"pub{FakeKey._seq}".encode()
        return FakeKey(
            FakeKeyAlg(alg.value if hasattr(alg, "value") else str(alg)), pub, b"sec"
        )

    @staticmethod
    def from_secret_bytes(alg: Any, secret: bytes):
        return FakeKey(
            FakeKeyAlg(alg.value if hasattr(alg, "value") else str(alg)), b"pub", secret
        )

    @staticmethod
    def from_seed(alg: Any, seed: Any, method: Any = None):
        return FakeKey(
            FakeKeyAlg(alg.value if hasattr(alg, "value") else str(alg)), b"pub", b"sec"
        )

    @staticmethod
    def from_public_bytes(alg: Any, public: bytes):
        return FakeKey(
            FakeKeyAlg(alg.value if hasattr(alg, "value") else str(alg)), public, b""
        )

    def get_public_bytes(self) -> bytes:
        return self._public

    def get_secret_bytes(self) -> bytes:
        return self._secret

    def sign_message(self, message):  # pragma: no cover - trivial passthrough
        return b"sig" + (message if isinstance(message, bytes) else b"".join(message))


class FakeAskarHandle:
    def __init__(self):
        self._keys: Dict[str, Dict[str, Any]] = {}

    async def insert_key(
        self,
        name: str,
        key: FakeKey,
        metadata: Optional[str] = None,
        tags: Optional[dict] = None,
    ):
        if name in self._keys:

            class _Err(Exception):
                def __init__(self):
                    self.code = "DUPLICATE"

            raise _Err()
        self._keys[name] = {"key": key, "metadata": metadata, "tags": tags or {}}

    def update_key(
        self, name: str, tags: Optional[dict] = None, metadata: Optional[str] = None
    ):
        entry = self._keys.get(name)
        if not entry:

            class _Err(Exception):
                def __init__(self):
                    self.code = "NOT_FOUND"

            raise _Err()
        if tags is not None:
            entry["tags"] = tags
        if metadata is not None:
            entry["metadata"] = metadata

    def fetch_key(self, name: str, for_update: bool = False):
        entry = self._keys.get(name)
        if not entry:
            return None
        return types.SimpleNamespace(
            key=entry["key"], metadata=entry["metadata"], tags=entry["tags"]
        )

    def fetch_all_keys(self, tag_filter: dict, limit: int = 2):
        result = []
        for verkey, entry in self._keys.items():
            if all(entry["tags"].get(k) == v for k, v in (tag_filter or {}).items()):
                result.append(
                    types.SimpleNamespace(
                        key=entry["key"], metadata=entry["metadata"], tags=entry["tags"]
                    )
                )
                if len(result) >= limit:
                    break
        return result


class FakeStoreSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def fetch(self, category: str, name: str, for_update: bool = False):
        return None


class FakeStore:
    def session(self):
        return FakeStoreSession()


class FakeContext:
    def __init__(self, registry: dict):
        self._registry = registry

    def inject(self, cls):
        return self._registry[cls]


class FakeProfile:
    def __init__(self, askar_handle, context, store):
        self.askar_handle = askar_handle
        self.context = context
        self.store = store
        self.profile = types.SimpleNamespace(name="test")


class FakeSession:
    def __init__(self, profile: FakeProfile):
        self.askar_handle = profile.askar_handle
        self.store = profile
        self.context = profile.context
        self.profile = profile

    def inject(self, cls):
        return self.context.inject(cls)


@pytest.fixture
def patched_wallet(monkeypatch):
    from acapy_agent.wallet import kanon_wallet as module

    class _KeyAlg:
        ED25519 = FakeKeyAlg("ed25519")
        X25519 = FakeKeyAlg("x25519")
        P256 = FakeKeyAlg("p256")
        BLS12_381_G2 = FakeKeyAlg("bls12_381_g2")

    monkeypatch.setattr(module, "Key", FakeKey, raising=True)
    monkeypatch.setattr(module, "KeyAlg", _KeyAlg, raising=True)
    monkeypatch.setattr(module, "validate_seed", lambda s: b"seedbytes")
    monkeypatch.setattr(module, "pack_message", lambda to, fk, m: b"packed")
    monkeypatch.setattr(module, "unpack_message", lambda h, em: (b"{ }", "r", "s"))

    key_types = module.KeyTypes()

    askar = FakeAskarHandle()
    context = FakeContext({module.KeyTypes: key_types})
    profile = FakeProfile(askar, context, FakeStore())
    session = FakeSession(profile)

    wallet = module.KanonWallet(session)
    return module, wallet, askar


@pytest.mark.asyncio
async def test_create_key_and_get_signing_key_success(patched_wallet):
    module, wallet, _ = patched_wallet

    info = await wallet.create_key(module.ED25519, metadata={"k": 1}, kid="kid-1")
    assert info.verkey  # base58 string from bytes
    assert info.metadata == {"k": 1}
    assert info.kid == "kid-1"

    fetched = await wallet.get_signing_key(info.verkey)
    assert fetched.verkey == info.verkey
    assert fetched.key_type.key_type == module.ED25519.key_type


@pytest.mark.asyncio
async def test_assign_kid_to_key_and_get_by_kid(patched_wallet):
    module, wallet, askar = patched_wallet

    created = await wallet.create_key(module.ED25519, metadata={})

    updated = await wallet.assign_kid_to_key(created.verkey, "kid-xyz")
    assert updated.kid == "kid-xyz"

    looked = await wallet.get_key_by_kid("kid-xyz")
    assert looked.kid == "kid-xyz"
    assert looked.verkey == created.verkey


@pytest.mark.asyncio
async def test_get_signing_key_not_found_raises(patched_wallet):
    module, wallet, _ = patched_wallet
    with pytest.raises(module.WalletNotFoundError):
        await wallet.get_signing_key("")


@pytest.mark.asyncio
async def test_create_signing_key_wrapper(patched_wallet):
    module, wallet, _ = patched_wallet
    info = await wallet.create_signing_key(module.ED25519, metadata={"m": 1})
    assert info.metadata == {"m": 1}


@pytest.mark.asyncio
async def test_get_key_by_kid_not_found_and_duplicate(patched_wallet):
    module, wallet, _ = patched_wallet
    with pytest.raises(module.WalletNotFoundError):
        await wallet.get_key_by_kid("nope")

    await wallet.create_key(module.ED25519, metadata={}, kid="dup")
    await wallet.create_key(module.ED25519, metadata={}, kid="dup")
    with pytest.raises(module.WalletDuplicateError):
        await wallet.get_key_by_kid("dup")


@pytest.mark.asyncio
async def test_replace_signing_key_metadata_requires_verkey(patched_wallet):
    module, wallet, _ = patched_wallet
    with pytest.raises(module.WalletNotFoundError):
        await wallet.replace_signing_key_metadata("", {"x": 1})


@pytest.mark.asyncio
async def test_sign_message_and_verify_missing_inputs_and_missing_key(patched_wallet):
    module, wallet, _ = patched_wallet
    with pytest.raises(module.WalletError):
        await wallet.sign_message(b"", "vk")
    with pytest.raises(module.WalletError):
        await wallet.sign_message(b"m", "")
    with pytest.raises(module.WalletNotFoundError):
        await wallet.sign_message(b"m", "unknown")

    k = await wallet.create_key(module.ED25519, metadata={})
    sig = await wallet.sign_message(b"m", k.verkey)
    with pytest.raises(module.WalletError):
        await wallet.verify_message(b"m", sig, "", module.ED25519)
    with pytest.raises(module.WalletError):
        await wallet.verify_message(b"", sig, k.verkey, module.ED25519)
    with pytest.raises(module.WalletError):
        await wallet.verify_message(b"m", b"", k.verkey, module.ED25519)


@pytest.mark.asyncio
async def test_pack_message_missing_from_key_raises(patched_wallet):
    module, wallet, _ = patched_wallet
    with pytest.raises(module.WalletNotFoundError):
        await wallet.pack_message("{}", ["vk"], from_verkey="vk")


@pytest.mark.asyncio
async def test_get_signing_key_unknown_key_type_raises(patched_wallet):
    module, wallet, askar = patched_wallet

    await askar.insert_key("vkU", FakeKey(FakeKeyAlg("unknown"), b"pubU", b"sec"))
    with pytest.raises(module.WalletError):
        await wallet.get_signing_key("vkU")
