import json
import types
from typing import Any, Dict, Optional

import pytest


@pytest.fixture
def wallet_env(monkeypatch):
    from acapy_agent.wallet import kanon_wallet as module

    class FakeKeyAlg:
        def __init__(self, value: str):
            self.value = value

    class FakeKey:
        _seq = 0

        def __init__(self, alg: Any, pb: bytes, sb: bytes):
            self.algorithm = alg
            self._pb = pb
            self._sb = sb

        @staticmethod
        def generate(alg):
            FakeKey._seq += 1
            return FakeKey(
                FakeKeyAlg(getattr(alg, "value", str(alg))),
                f"pub{FakeKey._seq}".encode(),
                b"sec",
            )

        def get_public_bytes(self):
            return self._pb

        def get_secret_bytes(self):
            return self._sb

        def sign_message(self, m):
            return b"sig" + (m if isinstance(m, bytes) else b"".join(m))

    class _KeyAlg:
        ED25519 = FakeKeyAlg("ed25519")
        X25519 = FakeKeyAlg("x25519")
        P256 = FakeKeyAlg("p256")
        BLS12_381_G2 = FakeKeyAlg("bls12_381_g2")

    monkeypatch.setattr(module, "Key", FakeKey, raising=True)
    monkeypatch.setattr(module, "KeyAlg", _KeyAlg, raising=True)
    monkeypatch.setattr(module, "validate_seed", lambda s: b"seedbytes")

    class FakeAskar:
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

        async def fetch_key(self, name: str, for_update: bool = False):
            entry = self._keys.get(name)
            if not entry:
                return None
            return types.SimpleNamespace(
                key=entry["key"], metadata=entry["metadata"], tags=entry["tags"]
            )

        async def update_key(
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

        async def fetch_all_keys(self, tag_filter: dict, limit: int = 2):
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

    class FakeStore:
        def __init__(self):
            self._rows: Dict[tuple[str, str], Dict[str, Any]] = {}

        def session(self):
            store = self

            class Sess:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, et, ev, tb):
                    return False

                async def fetch(self, cat, name, for_update: bool = False):
                    row = store._rows.get((cat, name))
                    if not row:
                        return None
                    return types.SimpleNamespace(
                        category=cat,
                        name=name,
                        value=row.get("value"),
                        value_json=row.get("value_json"),
                        tags=row.get("tags", {}),
                    )

                async def replace(
                    self, cat, name, value=None, tags=None, value_json=None
                ):
                    row = store._rows.get((cat, name))
                    if not row:
                        return None
                    if value_json is not None:
                        row["value_json"] = value_json
                        row["value"] = json.dumps(value_json)
                    if value is not None:
                        row["value"] = value
                    if tags is not None:
                        row["tags"] = tags

                async def insert(self, cat, name, value=None, tags=None, value_json=None):
                    store._rows[(cat, name)] = {
                        "value": value,
                        "value_json": value_json,
                        "tags": tags or {},
                    }

                async def fetch_all(self, cat, tag_filter=None, **kwargs):
                    res = []
                    for (c, n), row in store._rows.items():
                        if c != cat:
                            continue
                        if tag_filter and any(
                            (row.get("tags", {}).get(k) != v)
                            for k, v in tag_filter.items()
                        ):
                            continue
                        res.append(
                            types.SimpleNamespace(
                                category=c,
                                name=n,
                                value=row.get("value"),
                                value_json=row.get("value_json"),
                                tags=row.get("tags", {}),
                            )
                        )
                    return res

            return Sess()

        async def scan(self, **kwargs):
            if False:
                yield None

    class FakeProfile:
        def __init__(self):
            self.askar_handle = FakeAskar()
            self.store = FakeStore()
            self.context = types.SimpleNamespace(inject=lambda c: None)
            self.profile = types.SimpleNamespace(name="p")

    key_types = module.KeyTypes()

    class _DIDMethods:
        def from_method(self, name):
            return module.SOV

        def from_did(self, did):
            return types.SimpleNamespace(method_name="sov", supports_rotation=True)

    class _FakeDPV:
        def __init__(self, *_):
            pass

        def validate_key_type(self, *_):
            return None

        def validate_or_derive_did(self, method, key_type, verkey_bytes, did):
            return did or "did:sov:testdid"

    monkeypatch.setattr(module, "DIDParametersValidation", _FakeDPV, raising=True)

    profile = FakeProfile()

    class _Session:
        def __init__(self, profile):
            self.askar_handle = profile.askar_handle
            self.store = profile.store
            self.context = types.SimpleNamespace(
                inject=lambda cls: key_types if cls is module.KeyTypes else _DIDMethods()
            )
            self.profile = profile

        def inject(self, cls):
            return key_types if cls is module.KeyTypes else _DIDMethods()

    session = _Session(profile)

    wallet = module.KanonWallet(session)
    return module, wallet, profile


@pytest.mark.asyncio
async def test_input_and_lookup_errors(wallet_env):
    module, wallet, profile = wallet_env

    with pytest.raises(module.WalletNotFoundError):
        await wallet.get_signing_key("")

    with pytest.raises(module.WalletNotFoundError):
        await wallet.replace_signing_key_metadata("nope", {})

    with pytest.raises(module.WalletNotFoundError):
        await wallet.get_key_by_kid("kid-missing")

    info1 = await wallet.create_key(module.ED25519, metadata={}, kid="dup")
    k2 = module.Key.generate(module.ED25519)
    await profile.askar_handle.insert_key(
        name="v2", key=k2, metadata=json.dumps({}), tags={"kid": "dup"}
    )
    with pytest.raises(module.WalletDuplicateError):
        await wallet.get_key_by_kid("dup")

    with pytest.raises(module.WalletError):
        await wallet.sign_message(b"", info1.verkey)
    with pytest.raises(module.WalletError):
        await wallet.sign_message(b"msg", "")
    with pytest.raises(module.WalletError):
        await wallet.verify_message(b"msg", b"", info1.verkey, module.ED25519)
    with pytest.raises(module.WalletError):
        await wallet.verify_message(b"", b"sig", info1.verkey, module.ED25519)


@pytest.mark.asyncio
async def test_set_did_endpoint_and_ledger_errors(wallet_env):
    module, wallet, profile = wallet_env

    did_info = await wallet.create_local_did(
        module.SOV, module.ED25519, metadata={"public": True}
    )
    await wallet.set_public_did(did_info.did)

    with pytest.raises(module.LedgerConfigError):
        await wallet.set_did_endpoint(did_info.did, "http://e", ledger=None)

    class FakeLedger:
        def __init__(self):
            self.read_only = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, et, ev, tb):
            return False

        async def update_endpoint_for_did(
            self,
            did,
            endpoint,
            endpoint_type,
            write_ledger=True,
            endorser_did=None,
            routing_keys=None,
        ):
            return {"did": did, "endpoint": endpoint}

    attrib = await wallet.set_did_endpoint(
        did_info.did, "http://e", ledger=FakeLedger(), write_ledger=False
    )
    assert attrib["did"] == did_info.did


@pytest.mark.asyncio
async def test_assign_kid_and_get_by_kid_success(wallet_env, monkeypatch):
    module, wallet, profile = wallet_env

    info = await wallet.create_key(module.ED25519)
    assigned = await wallet.assign_kid_to_key(info.verkey, "kid-ok")
    assert assigned.kid == "kid-ok"

    got = await wallet.get_key_by_kid("kid-ok")
    assert got.verkey == info.verkey and got.kid == "kid-ok"

    class BadKeyTypes(module.KeyTypes.__class__):
        def from_key_type(self, *_):
            return None

    monkeypatch.setattr(
        wallet.session,
        "inject",
        lambda cls: BadKeyTypes
        if cls is module.KeyTypes
        else wallet.session.context.inject(cls),
    )
    monkeypatch.setattr(module, "ERR_UNKNOWN_KEY_TYPE", "Unknown key type %s")
    with pytest.raises(module.WalletError):
        await wallet.assign_kid_to_key(info.verkey, "kid-bad")


@pytest.mark.asyncio
async def test_get_public_did_populates_and_store_did_paths(wallet_env):
    module, wallet, profile = wallet_env

    did_info = await wallet.create_local_did(
        module.SOV, module.ED25519, metadata={"public": True}
    )
    pub = await wallet.get_public_did()
    assert pub and pub.did == did_info.did

    with pytest.raises(module.WalletDuplicateError):
        await wallet.store_did(did_info)

    new_info = module.DIDInfo(
        did="did:sov:newdid",
        verkey=did_info.verkey,
        metadata={},
        method=module.SOV,
        key_type=module.ED25519,
    )
    stored = await wallet.store_did(new_info)
    assert stored.did == "did:sov:newdid"


@pytest.mark.asyncio
async def test_set_public_did_with_didinfo_and_pack_message_errors(wallet_env):
    module, wallet, profile = wallet_env

    did_info = await wallet.create_local_did(module.SOV, module.ED25519)
    info = await wallet.set_public_did(did_info)
    assert info.did == did_info.did

    with pytest.raises(module.WalletError):
        await wallet.pack_message(None, ["v1"])  # message None
    with pytest.raises(module.WalletNotFoundError):
        await wallet.pack_message("{}", ["v1"], from_verkey="missing")


@pytest.mark.asyncio
async def test_get_local_did_and_replace_metadata_errors(wallet_env):
    module, wallet, profile = wallet_env

    with pytest.raises(module.WalletNotFoundError):
        await wallet.get_local_did("")

    with pytest.raises(module.WalletNotFoundError):
        await wallet.replace_local_did_metadata("did:missing", {})


@pytest.mark.asyncio
async def test_create_key_askar_error_non_duplicate(wallet_env, monkeypatch):
    module, wallet, profile = wallet_env

    class LocalErr(Exception):
        def __init__(self, code):
            self.code = code

    monkeypatch.setattr(module, "AskarError", LocalErr)
    monkeypatch.setattr(
        module, "AskarErrorCode", types.SimpleNamespace(DUPLICATE="DUP", INPUT="INPUT")
    )

    async def _raise(*a, **kw):
        raise LocalErr("BUSY")

    monkeypatch.setattr(profile.askar_handle, "insert_key", _raise)

    with pytest.raises(module.WalletError):
        await wallet.create_key(module.ED25519)


@pytest.mark.asyncio
async def test_create_local_did_duplicate_updates_metadata(wallet_env, monkeypatch):
    module, wallet, profile = wallet_env

    did = "did:sov:dupmeta"
    verkey = "samevk"
    async with profile.store.session() as s:
        await s.insert(
            "did",
            did,
            value_json={
                "did": did,
                "method": "sov",
                "verkey": verkey,
                "verkey_type": "ed25519",
                "metadata": {"a": 1},
            },
            tags={"method": "sov", "verkey": verkey, "verkey_type": "ed25519"},
        )

    class LocalErr(Exception):
        def __init__(self, code):
            self.code = code

    monkeypatch.setattr(module, "AskarError", LocalErr)
    monkeypatch.setattr(module, "AskarErrorCode", types.SimpleNamespace(DUPLICATE="DUP"))

    async def _dup(*a, **kw):
        raise LocalErr("DUP")

    monkeypatch.setattr(profile.askar_handle, "insert_key", _dup)

    class _DPV:
        def __init__(self, *_):
            pass

        def validate_key_type(self, *_):
            return None

        def validate_or_derive_did(self, *_):
            return did

    monkeypatch.setattr(module, "DIDParametersValidation", _DPV)

    async def _fetch_key(name, *a, **kw):
        return types.SimpleNamespace(
            key=types.SimpleNamespace(
                get_public_bytes=lambda: b"irrelevant",
                algorithm=types.SimpleNamespace(value="ed25519"),
            )
        )

    monkeypatch.setattr(profile.askar_handle, "fetch_key", _fetch_key)

    monkeypatch.setattr(module, "bytes_to_b58", lambda *_: "samevk")
    updated = await wallet.create_local_did(module.SOV, module.ED25519, metadata={})
    assert updated.did == did
    info = await wallet.get_local_did(did)
    assert info.metadata == {}


@pytest.mark.asyncio
async def test_get_local_did_db_error_mapping(wallet_env, monkeypatch):
    module, wallet, profile = wallet_env

    class BadSess:
        async def __aenter__(self):
            return self

        async def __aexit__(self, et, ev, tb):
            return False

        async def fetch(self, *a, **kw):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.BUSY, "x")

    def _session_factory():
        return BadSess()

    monkeypatch.setattr(profile.store, "session", _session_factory)
    from acapy_agent.storage import kanon_storage as storage_module

    async def _get_record_mock(*a, **kw):
        raise storage_module.StorageNotFoundError("not found")

    monkeypatch.setattr(storage_module.KanonStorage, "get_record", _get_record_mock)
    with pytest.raises(module.WalletError):
        await wallet.get_local_did("did:any")


@pytest.mark.asyncio
async def test_set_public_did_metadata_update_db_error(wallet_env, monkeypatch):
    module, wallet, profile = wallet_env

    did_info = await wallet.create_local_did(module.SOV, module.ED25519, metadata={})

    class BadSess:
        async def __aenter__(self):
            return self

        async def __aexit__(self, et, ev, tb):
            return False

        async def fetch(self, *a, **kw):
            return None

        async def replace(self, *a, **kw):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.BUSY, "fail")

    async def _get_public():
        return did_info

    monkeypatch.setattr(wallet, "get_public_did", _get_public)
    monkeypatch.setattr(profile.store, "session", lambda: BadSess())
    with pytest.raises(module.WalletError):
        await wallet.set_public_did(did_info.did)


@pytest.mark.asyncio
async def test_verify_message_fallback_path(wallet_env, monkeypatch):
    module, wallet, profile = wallet_env

    monkeypatch.setattr(module, "verify_signed_message", lambda **kw: True)
    ok = await wallet.verify_message(b"m", b"s", "3sj3", module.BLS12381G2)
    assert ok is True


@pytest.mark.asyncio
async def test_get_local_did_for_verkey_multi_peer4_choice(wallet_env):
    module, wallet, profile = wallet_env

    verkey = "vx1"
    async with profile.store.session() as s:
        await s.insert(
            "did",
            "did:peer:4longer",
            value_json={
                "did": "did:peer:4longer",
                "method": "sov",
                "verkey": verkey,
                "verkey_type": "ed25519",
                "metadata": {},
            },
            tags={"method": "sov", "verkey": verkey, "verkey_type": "ed25519"},
        )
        await s.insert(
            "did",
            "did:peer:4x",
            value_json={
                "did": "did:peer:4x",
                "method": "sov",
                "verkey": verkey,
                "verkey_type": "ed25519",
                "metadata": {},
            },
            tags={"method": "sov", "verkey": verkey, "verkey_type": "ed25519"},
        )
    got = await wallet.get_local_did_for_verkey(verkey)
    assert got.did == "did:peer:4x"


@pytest.mark.asyncio
async def test_get_public_did_reads_existing_record(wallet_env):
    module, wallet, profile = wallet_env

    did_info = await wallet.create_local_did(module.SOV, module.ED25519)
    async with profile.store.session() as s:
        await s.insert(
            "config",
            "default_public_did",
            value=json.dumps({"did": did_info.did}),
            tags={},
        )
    pub = await wallet.get_public_did()
    assert pub and pub.did == did_info.did


@pytest.mark.asyncio
async def test_replace_local_did_metadata_success(wallet_env):
    module, wallet, profile = wallet_env

    did_info = await wallet.create_local_did(
        module.SOV, module.ED25519, metadata={"a": 1}
    )
    await wallet.replace_local_did_metadata(did_info.did, {"a": 2})
    got = await wallet.get_local_did(did_info.did)
    assert got.metadata == {"a": 2}


@pytest.mark.asyncio
async def test_sign_message_bls_path(wallet_env, monkeypatch):
    module, wallet, profile = wallet_env

    bls_key = wallet.session.askar_handle._keys
    k = types.SimpleNamespace(
        algorithm=module.KeyAlg.BLS12_381_G2,
        get_public_bytes=lambda: b"blspub",
        get_secret_bytes=lambda: b"blssec",
    )
    await profile.askar_handle.insert_key("blsver", k, metadata=json.dumps({}), tags={})
    monkeypatch.setattr(module, "sign_message", lambda **kw: b"blssig")
    sig = await wallet.sign_message(b"m", "blsver")
    assert sig == b"blssig"


@pytest.mark.asyncio
async def test_set_public_did_replaces_existing_record(wallet_env):
    module, wallet, profile = wallet_env

    did1 = await wallet.create_local_did(
        module.SOV, module.ED25519, did="did:sov:one", metadata={}
    )
    did2 = await wallet.create_local_did(
        module.SOV, module.ED25519, did="did:sov:two", metadata={}
    )

    async with profile.store.session() as s:
        await s.insert(
            "config",
            "default_public_did",
            value=json.dumps({"did": did1.did}),
            tags={},
        )

    res = await wallet.set_public_did(did2)
    assert res.did == did2.did

    async with profile.store.session() as s:
        cfg = await s.fetch("config", "default_public_did")
        assert json.loads(cfg.value)["did"] == did2.did
    got2 = await wallet.get_local_did(did2.did)
    assert got2.metadata.get("posted") is True
