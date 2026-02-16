import json
import types
from typing import Any, Dict, Optional

import pytest


class FakeKeyAlg:
    def __init__(self, value: str):
        self.value = value


class FakeKey:
    seq = 0

    def __init__(self, algorithm: FakeKeyAlg, public_bytes: bytes, secret_bytes: bytes):
        self.algorithm = algorithm
        self._public = public_bytes
        self._secret = secret_bytes

    @staticmethod
    def generate(alg: Any):
        FakeKey.seq += 1
        pub = f"pub{FakeKey.seq}".encode()
        return FakeKey(FakeKeyAlg(getattr(alg, "value", str(alg))), pub, b"sec")

    @staticmethod
    def from_secret_bytes(alg: Any, secret: bytes):
        prefix = secret[:4] if secret else b"seed"
        pub = b"pub-" + prefix
        return FakeKey(FakeKeyAlg(getattr(alg, "value", str(alg))), pub, secret)

    @staticmethod
    def from_seed(alg: Any, seed: Any, method: Any = None):
        s = seed if isinstance(seed, (bytes, bytearray)) else str(seed).encode()
        pub = b"pubseed-" + (s[:4] if s else b"x")
        return FakeKey(FakeKeyAlg(getattr(alg, "value", str(alg))), pub, b"sec")

    @staticmethod
    def from_public_bytes(alg: Any, public: bytes):
        return FakeKey(FakeKeyAlg(getattr(alg, "value", str(alg))), public, b"")

    def get_public_bytes(self) -> bytes:
        return self._public

    def get_secret_bytes(self) -> bytes:
        return self._secret

    def sign_message(self, message):
        msg = message if isinstance(message, bytes) else b"".join(message)
        return b"sig" + msg

    def verify_signature(self, message, signature):
        msg = message if isinstance(message, bytes) else b"".join(message)
        return signature == (b"sig" + msg)


class FakeDBStoreHandle:
    def __init__(self):
        self._rows: Dict[tuple[str, str], Dict[str, Any]] = {}

    def insert(
        self,
        category: str,
        name: str,
        value: Optional[str] = None,
        tags: Optional[dict] = None,
        value_json: Optional[dict] = None,
    ):
        key = (category, name)
        if key in self._rows:
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.DUPLICATE, "dup")
        stored_value = value
        if value_json is not None and stored_value is None:
            stored_value = json.dumps(value_json)
        self._rows[key] = {
            "category": category,
            "name": name,
            "value": stored_value,
            "value_json": value_json,
            "tags": tags or {},
        }

    def fetch(self, category: str, name: str, for_update: bool = False):
        row = self._rows.get((category, name))
        if not row:
            return None
        return types.SimpleNamespace(
            category=row["category"],
            name=row["name"],
            value=row["value"],
            value_json=row["value_json"],
            tags=row["tags"],
        )

    def replace(
        self,
        category: str,
        name: str,
        value: Optional[str] = None,
        tags: Optional[dict] = None,
        value_json: Optional[dict] = None,
    ):
        key = (category, name)
        row = self._rows.get(key)
        if not row:
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.NOT_FOUND, "nf")
        if value_json is not None:
            row["value_json"] = value_json
            row["value"] = json.dumps(value_json)
        if value is not None:
            row["value"] = value
        if tags is not None:
            row["tags"] = tags

    def fetch_all(self, category: str, tag_filter: Optional[dict] = None, **kwargs):
        results = []
        for (cat, _), row in self._rows.items():
            if cat != category:
                continue
            tags = row["tags"] or {}
            ok = True
            for k, v in (tag_filter or {}).items():
                if tags.get(k) != v:
                    ok = False
                    break
            if ok:
                results.append(
                    types.SimpleNamespace(
                        category=row["category"],
                        name=row["name"],
                        value=row["value"],
                        value_json=row["value_json"],
                        tags=row["tags"],
                    )
                )
        return results


class FakeStoreSession:
    def __init__(self, handle: FakeDBStoreHandle):
        self.handle = handle

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def fetch(self, *args, **kwargs):
        return await self.handle.fetch(*args, **kwargs)

    async def insert(self, *args, **kwargs):
        return await self.handle.insert(*args, **kwargs)

    async def replace(self, *args, **kwargs):
        return await self.handle.replace(*args, **kwargs)

    async def fetch_all(self, *args, **kwargs):
        return await self.handle.fetch_all(*args, **kwargs)


class FakeProfile:
    def __init__(self):
        self._handle = FakeDBStoreHandle()
        self.store = self
        self.dbstore_handle = self._handle
        self.profile = types.SimpleNamespace(name="test")

    def session(self):
        return FakeStoreSession(self._handle)

    def transaction(self):
        return FakeStoreSession(self._handle)

    def opened(self):
        return types.SimpleNamespace(db_store=self.store)

    def scan(self, *args, **kwargs):
        async def _gen():
            yield None

        return _gen()


class FakeContext:
    def __init__(self, registry: dict):
        self._registry = registry

    def inject(self, cls):
        return self._registry[cls]


class FakeSession:
    def __init__(self, askar_handle, context, profile: FakeProfile):
        self.askar_handle = askar_handle
        self.context = context
        self.store = profile
        self.profile = profile

    def inject(self, cls):
        return self.context.inject(cls)


@pytest.fixture
def wallet_with_did_env(monkeypatch):
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

    def _unpack(h, em):
        return (b"{ }", "r", "s")

    monkeypatch.setattr(module, "unpack_message", _unpack)

    class _FakeDPV:
        def __init__(self, *_):
            pass

        def validate_key_type(self, *_):
            return None

        def validate_or_derive_did(self, method, key_type, verkey_bytes, did):
            return did or "did:sov:testdid"

    monkeypatch.setattr(module, "DIDParametersValidation", _FakeDPV, raising=True)

    key_types = module.KeyTypes()

    class _DIDMethods:
        def from_method(self, name):
            return module.SOV

        def from_did(self, did):
            return types.SimpleNamespace(method_name="sov", supports_rotation=True)

    context = FakeContext({module.KeyTypes: key_types, module.DIDMethods: _DIDMethods()})

    class _AskarHandle:
        def __init__(self):
            self._keys: Dict[str, Dict[str, Any]] = {}

        def insert_key(
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

        def fetch_key(self, name: str, for_update: bool = False):
            entry = self._keys.get(name)
            if not entry:
                return None
            return types.SimpleNamespace(
                key=entry["key"], metadata=entry["metadata"], tags=entry["tags"]
            )

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

        def fetch_all_keys(self, tag_filter: dict, limit: int = 2):
            results = []
            for _, entry in self._keys.items():
                if all(entry["tags"].get(k) == v for k, v in (tag_filter or {}).items()):
                    results.append(
                        types.SimpleNamespace(
                            key=entry["key"],
                            metadata=entry["metadata"],
                            tags=entry["tags"],
                        )
                    )
                    if len(results) >= limit:
                        break
            return results

    askar = _AskarHandle()
    profile = FakeProfile()
    session = FakeSession(askar, context, profile)

    wallet = module.KanonWallet(session)
    return module, wallet


@pytest.mark.asyncio
async def test_create_local_did_and_get_set_public(wallet_with_did_env):
    module, wallet = wallet_with_did_env

    did_info = await wallet.create_local_did(
        module.SOV, module.ED25519, metadata={"public": True}
    )
    assert did_info.did.startswith("did:sov:")

    public = await wallet.get_public_did()
    assert public is not None and public.did == did_info.did

    updated = await wallet.set_public_did(did_info.did)
    assert updated.did == did_info.did


@pytest.mark.asyncio
async def test_sign_verify_and_pack_unpack(wallet_with_did_env):
    module, wallet = wallet_with_did_env

    key_info = await wallet.create_key(module.ED25519, metadata={})

    msg = b"hello"
    sig = await wallet.sign_message(msg, key_info.verkey)
    assert await wallet.verify_message(msg, sig, key_info.verkey, module.ED25519)

    packed = await wallet.pack_message(
        "{}", [key_info.verkey], from_verkey=key_info.verkey
    )
    assert packed == b"packed"

    unpacked_json, sender, recipient = await wallet.unpack_message(b"xxx")
    assert isinstance(unpacked_json, str) and sender and recipient


@pytest.mark.asyncio
async def test_rotate_did_keypair_flow(wallet_with_did_env):
    module, wallet = wallet_with_did_env
    did_info = await wallet.create_local_did(
        module.SOV, module.ED25519, metadata={"public": True}
    )
    await wallet.set_public_did(did_info.did)
    next_verkey = await wallet.rotate_did_keypair_start(did_info.did, next_seed="seed")
    assert isinstance(next_verkey, str)
    applied = await wallet.rotate_did_keypair_apply(did_info.did)
    assert applied.did == did_info.did
    assert applied.verkey == next_verkey
