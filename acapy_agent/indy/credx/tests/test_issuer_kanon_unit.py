import types

import pytest


class _Handle:
    def __init__(self):
        self.rows = {}

    async def fetch(self, cat, name, for_update=False):
        return self.rows.get((cat, name))

    async def insert(self, cat, name, value=None, tags=None, value_json=None):
        if value is None and value_json is not None:
            self.rows[(cat, name)] = types.SimpleNamespace(
                raw_value=None, value_json=value_json, tags=tags or {}
            )
        else:
            self.rows[(cat, name)] = types.SimpleNamespace(
                raw_value=value,
                value_json=value if isinstance(value, dict) else None,
                tags=tags or {},
            )

    async def replace(
        self, cat, name, value=None, tags=None, expiry_ms=None, value_json=None
    ):
        rec = self.rows.get((cat, name))
        if not rec:
            if value is None and value_json is not None:
                self.rows[(cat, name)] = types.SimpleNamespace(
                    raw_value=None, value_json=value_json, tags=tags or {}
                )
            else:
                self.rows[(cat, name)] = types.SimpleNamespace(
                    raw_value=value,
                    value_json=value if isinstance(value, dict) else None,
                    tags=tags or {},
                )
        else:
            if value is not None:
                rec.raw_value = value
                if isinstance(value, dict):
                    rec.value_json = value
            if value_json is not None:
                rec.value_json = value_json


class _Sess:
    def __init__(self, h):
        self.handle = h

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Txn(_Sess):
    def __init__(self, h):
        super().__init__(h)
        self.handle = h

    async def commit(self):
        return None


class _Profile:
    def __init__(self):
        self.h = _Handle()
        self.settings = {}

    def session(self):
        return _Sess(self.h)

    def transaction(self):
        return _Txn(self.h)


@pytest.fixture
def patched_issuer(monkeypatch):
    from acapy_agent.indy.credx import issuer_kanon as module

    assert hasattr(module.KanonIndyCredxIssuer, "merge_revocation_registry_deltas")
    assert hasattr(module.KanonIndyCredxIssuer, "create_and_store_revocation_registry")

    class _Schema:
        def __init__(self):
            self.id = "sch"

        @staticmethod
        def create(did, name, ver, attrs):
            return _Schema()

        def to_json(self):
            return "{}"

    class _CredDef:
        def __init__(self):
            self.id = "cd"

        @staticmethod
        def create(*a, **k):
            return (
                _CredDef(),
                types.SimpleNamespace(to_json_buffer=lambda: b"{}"),
                types.SimpleNamespace(to_json_buffer=lambda: b"{}"),
            )

        def to_json(self):
            return "{}"

        @staticmethod
        def load(raw):
            return _CredDef()

    class _Offer:
        @staticmethod
        def create(schema_id, cred_def, key_proof):
            return types.SimpleNamespace(to_json=lambda: "{}")

    class _RevRegDef:
        def __init__(self):
            self.id = "rrd"
            self.max_cred_num = 5

        @staticmethod
        def create(*a, **k):
            return (
                _RevRegDef(),
                types.SimpleNamespace(to_json_buffer=lambda: b"{}"),
                types.SimpleNamespace(to_json=lambda: "{}"),
                types.SimpleNamespace(to_json=lambda: "{}"),
            )

        @staticmethod
        def load(raw):
            return _RevRegDef()

    class _RevReg:
        def to_json(self):
            return "{}"

        @staticmethod
        def load(raw):
            return _RevReg()

        def update(self, *a, **k):
            return types.SimpleNamespace(to_json=lambda: "{}")

    class _Delta:
        @staticmethod
        def load(x):
            return _Delta()

        def update_with(self, y):
            pass

        def to_json(self):
            return "{}"

    class _Credential:
        @staticmethod
        def create(*a, **k):
            return types.SimpleNamespace(to_json=lambda: "{}"), None, None

    monkeypatch.setattr(module, "Schema", _Schema)
    monkeypatch.setattr(module, "CredentialDefinition", _CredDef)
    monkeypatch.setattr(module, "CredentialOffer", _Offer)
    monkeypatch.setattr(module, "RevocationRegistryDefinition", _RevRegDef)
    monkeypatch.setattr(module, "RevocationRegistry", _RevReg)
    monkeypatch.setattr(module, "RevocationRegistryDelta", _Delta)
    monkeypatch.setattr(module, "Credential", _Credential)

    return module


@pytest.mark.asyncio
async def test_create_schema_and_cred_def_and_offer(patched_issuer):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(
            self,
            origin_did: str,
            cred_def_id: str,
            revoc_def_type: str,
            tag: str,
            max_cred_num: int,
            tails_base_path: str,
        ):
            return ("revreg", "{}", "{}")

    issuer = _TestIssuer(prof)
    sid, sjson = await issuer.create_schema("did:sov:abc", "s", "1.0", ["name"])
    assert sid == "sch"
    cdid, cdjson = await issuer.create_and_store_credential_definition(
        "did:sov:abc", {"id": "sch"}
    )
    assert cdid == "cd"
    async with prof.session() as s:
        await s.handle.insert(m.CATEGORY_CRED_DEF_KEY_PROOF, cdid, b"{}")
    off = await issuer.create_credential_offer(cdid)
    assert isinstance(off, str)


@pytest.mark.asyncio
async def test_build_raw_values_missing_attribute_raises(patched_issuer):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)
    with pytest.raises(m.IndyIssuerError):
        issuer._build_raw_values({"attrNames": ["name", "age"]}, {"name": "Alice"})


@pytest.mark.asyncio
async def test_create_credential_offer_missing_components(patched_issuer):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)
    with pytest.raises(m.IndyIssuerError):
        await issuer.create_credential_offer("cd")


@pytest.mark.asyncio
async def test_create_credential_missing_components(patched_issuer):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)
    with pytest.raises(m.IndyIssuerError):
        await issuer.create_credential(
            {"attrNames": ["name"]},
            {"cred_def_id": "cd"},
            {"prover_did": "did:sov:abc"},
            {"name": "Alice"},
        )


def test_classify_revocation_ids_paths(patched_issuer):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)
    rev_info = {"curr_id": 5, "used_ids": [2, 4]}
    valid, failed = issuer._classify_revocation_ids(rev_info, 5, [0, 2, 3, 6, 7, 5], "rr")
    assert 3 in valid and 5 in valid
    assert {0, 2, 6, 7}.issubset(failed)


@pytest.mark.asyncio
async def test_revoke_credentials_retry_and_success(patched_issuer, monkeypatch):
    m = patched_issuer
    prof = _Profile()
    calls = {"n": 0}

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

        async def _attempt_revocation(self, *a, **k):
            calls["n"] += 1
            if calls["n"] < 2:
                raise m.IndyIssuerRetryableError("retry")
            return types.SimpleNamespace(to_json=lambda: "{}"), set()

    issuer = _TestIssuer(prof)
    delta, failed = await issuer.revoke_credentials("cd", "rr", "tails", ["1"])
    assert isinstance(delta, str)
    assert failed == []


@pytest.mark.asyncio
async def test_save_revocation_updates_missing_and_concurrent(
    patched_issuer, monkeypatch
):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)

    class _SessMissing(_Txn):
        def __init__(self, h):
            super().__init__(h)

            class _H:
                async def fetch(self, cat, name, for_update=False):
                    return None

            self.handle = _H()

    class _ProfMissing(_Profile):
        def transaction(self):
            return _SessMissing(self.h)

    issuer2 = _TestIssuer(_ProfMissing())
    await issuer2._save_revocation_updates(
        "rr", types.SimpleNamespace(to_json_buffer=lambda: b"{}"), {"curr_id": 1}, set()
    )

    class _SessConcurrent(_Txn):
        def __init__(self, h):
            super().__init__(h)

            class _H:
                async def fetch(self, cat, name, for_update=False):
                    if str(cat).endswith("info"):
                        return types.SimpleNamespace(
                            value_json={"curr_id": 2, "used_ids": []}
                        )
                    return types.SimpleNamespace(raw_value=b"{}")

            self.handle = _H()

    class _ProfConcurrent(_Profile):
        def transaction(self):
            return _SessConcurrent(self.h)

    issuer3 = _TestIssuer(_ProfConcurrent())
    with pytest.raises(m.IndyIssuerRetryableError):
        await issuer3._save_revocation_updates(
            "rr",
            types.SimpleNamespace(to_json_buffer=lambda: b"{}"),
            {"curr_id": 1, "used_ids": []},
            {1},
        )


@pytest.mark.asyncio
async def test_create_schema_errors(patched_issuer, monkeypatch):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)

    # creation error
    def _raise_credx(*a, **k):
        raise m.CredxError(1, "x")

    monkeypatch.setattr(m, "Schema", types.SimpleNamespace(create=_raise_credx))
    with pytest.raises(m.IndyIssuerError):
        await issuer.create_schema("did:sov:abc", "s", "1.0", ["name"])

    # store error
    class _BadHandle(_Handle):
        async def insert(self, *a, **k):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.WRAPPER, "x")

    class _BadProfile(_Profile):
        def __init__(self):
            super().__init__()
            self.h = _BadHandle()

    prof2 = _BadProfile()
    issuer2 = _TestIssuer(prof2)

    class _OkSchema:
        def __init__(self):
            self.id = "sch"

        @staticmethod
        def create(*a, **k):
            return _OkSchema()

        def to_json(self):
            return "{}"

    monkeypatch.setattr(m, "Schema", _OkSchema)
    with pytest.raises(m.IndyIssuerError):
        await issuer2.create_schema("did:sov:abc", "s", "1.0", ["name"])


@pytest.mark.asyncio
async def test_create_cred_def_store_error_and_offer_create_error(
    patched_issuer, monkeypatch
):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)

    class _TxnFail(_Txn):
        async def commit(self):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.WRAPPER, "x")

    class _ProfFail(_Profile):
        def transaction(self):
            return _TxnFail(self.h)

    issuerf = _TestIssuer(_ProfFail())

    class _OkCredDef:
        def __init__(self):
            self.id = "cd"
            self.schema_id = "sch"

        @staticmethod
        def create(*a, **k):
            return (
                _OkCredDef(),
                types.SimpleNamespace(to_json_buffer=lambda: b"{}"),
                types.SimpleNamespace(to_json_buffer=lambda: b"{}"),
            )

        def to_json(self):
            return "{}"

        @staticmethod
        def load(raw):
            return _OkCredDef()

    monkeypatch.setattr(m, "CredentialDefinition", _OkCredDef)
    with pytest.raises(m.IndyIssuerError):
        await issuerf.create_and_store_credential_definition("did:sov:abc", {"id": "sch"})

    class _OfferBad:
        @staticmethod
        def create(*a, **k):
            raise m.CredxError(1, "x")

    monkeypatch.setattr(m, "CredentialOffer", _OfferBad)
    async with prof.session() as s:
        await s.handle.insert(m.CATEGORY_CRED_DEF, "cd", b"{}")
        await s.handle.insert(m.CATEGORY_CRED_DEF_KEY_PROOF, "cd", b"{}")
    with pytest.raises(m.IndyIssuerError):
        await issuer.create_credential_offer("cd")


@pytest.mark.asyncio
async def test_create_credential_revocation_full_and_success(patched_issuer, monkeypatch):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)

    class _RevCfg:
        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(m, "CredentialRevocationConfig", _RevCfg)
    async with prof.transaction() as t:
        await t.handle.insert(
            m.CATEGORY_REV_REG, "rr", types.SimpleNamespace(to_json_buffer=lambda: b"{}")
        )
        await t.handle.insert(
            m.CATEGORY_REV_REG_INFO, "rr", {"curr_id": 5, "used_ids": []}
        )
        await t.handle.insert(m.CATEGORY_REV_REG_DEF, "rr", b"{}")
        await t.handle.insert(m.CATEGORY_REV_REG_DEF_PRIVATE, "rr", b"{}")
    async with prof.session() as s:
        await s.handle.insert(m.CATEGORY_CRED_DEF, "cd", b"{}")
        await s.handle.insert(m.CATEGORY_CRED_DEF_PRIVATE, "cd", b"{}")
    with pytest.raises(m.IndyIssuerRevocationRegistryFullError):
        await issuer.create_credential(
            {"attrNames": ["name"]},
            {"cred_def_id": "cd"},
            {"prover_did": "did:sov:abc"},
            {"name": "Alice"},
            revoc_reg_id="rr",
        )
    async with prof.transaction() as t:
        await t.handle.insert(
            m.CATEGORY_REV_REG_INFO, "rr", {"curr_id": 0, "used_ids": []}
        )
    cred_json, cred_rev_id = await issuer.create_credential(
        {"attrNames": ["name"]},
        {"cred_def_id": "cd"},
        {"prover_did": "did:sov:abc"},
        {"name": "Alice"},
        revoc_reg_id="rr",
    )
    assert isinstance(cred_json, str)
    assert isinstance(cred_rev_id, (str, type(None)))


@pytest.mark.asyncio
async def test_credential_definition_in_wallet_true_false(patched_issuer):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)
    assert (await issuer.credential_definition_in_wallet("cd")) is False
    async with prof.session() as s:
        await s.handle.insert(m.CATEGORY_CRED_DEF_PRIVATE, "cd", b"{}")
    assert (await issuer.credential_definition_in_wallet("cd")) is True


@pytest.mark.asyncio
async def test_create_credential_offer_success(patched_issuer, monkeypatch):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)
    async with prof.session() as s:
        await s.handle.insert(m.CATEGORY_CRED_DEF, "cd", b"{}", tags={"schema_id": "sch"})
        await s.handle.insert(m.CATEGORY_CRED_DEF_KEY_PROOF, "cd", b"{}")

    class _Offer:
        @staticmethod
        def create(schema_id, cred_def, key_proof):
            return types.SimpleNamespace(to_json=lambda: "{}")

    monkeypatch.setattr(m, "CredentialOffer", _Offer)
    out = await issuer.create_credential_offer("cd")
    assert isinstance(out, str)


@pytest.mark.asyncio
async def test_create_credential_without_revocation_success(patched_issuer, monkeypatch):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)
    async with prof.session() as s:
        await s.handle.insert(m.CATEGORY_CRED_DEF, "cd", b"{}")
        await s.handle.insert(m.CATEGORY_CRED_DEF_PRIVATE, "cd", b"{}")

    class _Cred:
        @staticmethod
        def create(*a, **k):
            return types.SimpleNamespace(to_json=lambda: "{}"), None, None

    monkeypatch.setattr(m, "Credential", _Cred)
    cred_json, cred_rev_id = await issuer.create_credential(
        {"attrNames": ["name"]},
        {"cred_def_id": "cd"},
        {"prover_did": "did:sov:abc"},
        {"name": "Alice"},
    )
    assert isinstance(cred_json, str)
    assert cred_rev_id is None


def test_parse_revocation_components_load_errors(patched_issuer, monkeypatch):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)
    comps = {
        "cred_def": types.SimpleNamespace(raw_value=b"{}"),
        "rev_reg_def": types.SimpleNamespace(raw_value=b"{}"),
        "rev_reg_def_private": types.SimpleNamespace(raw_value=b"{}"),
        "rev_reg": types.SimpleNamespace(raw_value=b"{}"),
        "rev_reg_info": types.SimpleNamespace(value_json={}),
    }

    def _raise_load(raw):
        raise m.CredxError(1, "x")

    monkeypatch.setattr(
        m, "RevocationRegistryDefinition", types.SimpleNamespace(load=_raise_load)
    )
    with pytest.raises(m.IndyIssuerError):
        issuer._parse_revocation_components(comps)


@pytest.mark.asyncio
async def test_update_revocation_registry_error(patched_issuer, monkeypatch):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)

    class _Rev:
        def update(self, *a, **k):
            raise m.CredxError(1, "x")

    comps = {
        "rev_reg": _Rev(),
        "cred_def": object(),
        "rev_reg_def": object(),
        "rev_reg_def_private": object(),
    }
    with pytest.raises(m.IndyIssuerError):
        await issuer._update_revocation_registry(comps, [1])


@pytest.mark.asyncio
async def test_save_revocation_updates_success_path(patched_issuer):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)
    async with prof.transaction() as t:
        await t.handle.insert(
            m.CATEGORY_REV_REG, "rr", types.SimpleNamespace(to_json_buffer=lambda: b"{}")
        )
        await t.handle.insert(
            m.CATEGORY_REV_REG_INFO, "rr", {"curr_id": 1, "used_ids": []}
        )

    await issuer._save_revocation_updates(
        "rr",
        types.SimpleNamespace(to_json_buffer=lambda: b"{}"),
        {"curr_id": 1, "used_ids": []},
        {2},
    )


@pytest.mark.asyncio
async def test_fetch_revocation_records_missing_components(patched_issuer):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)

    class _Sess(_Txn):
        async def fetch(self, cat, name, for_update=False):
            return None

    class _P(_Profile):
        def transaction(self):
            return _Sess(self.h)

    with pytest.raises(m.IndyIssuerError):
        async with _P().transaction() as t:
            await issuer._fetch_revocation_records(t, "rr")


@pytest.mark.asyncio
async def test_create_credential_revocation_success_path(patched_issuer, monkeypatch):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)

    class _RRD:
        max_cred_num = 10

    monkeypatch.setattr(
        m, "RevocationRegistryDefinition", types.SimpleNamespace(load=lambda raw: _RRD())
    )
    monkeypatch.setattr(
        issuer,
        "_update_revocation_registry",
        lambda comps, ids: types.SimpleNamespace(to_json=lambda: "{}"),
    )
    monkeypatch.setattr(issuer, "_save_revocation_updates", lambda *a, **k: None)
    monkeypatch.setattr(m, "CredentialRevocationConfig", lambda *a, **k: object())

    class _Cred:
        @staticmethod
        def create(*a, **k):
            return types.SimpleNamespace(to_json=lambda: "{}"), None, None

    monkeypatch.setattr(m, "Credential", _Cred)

    class _Recv:
        raw_value = b"{}"

    rev_reg = types.SimpleNamespace(to_json_buffer=lambda: b"{}", raw_value=b"{}")
    rev_info = types.SimpleNamespace(value_json={"curr_id": 0, "used_ids": []})
    rev_def_rec = _Recv()
    rev_key = types.SimpleNamespace(raw_value=b"{}")

    async def _fake_fetch(txn, rr):
        return rev_reg, rev_info, rev_def_rec, rev_key

    monkeypatch.setattr(issuer, "_fetch_revocation_records", _fake_fetch)
    async with prof.session() as s:
        await s.handle.insert(m.CATEGORY_CRED_DEF, "cd", b"{}")
        await s.handle.insert(m.CATEGORY_CRED_DEF_PRIVATE, "cd", b"{}")
    cred_json, cred_rev_id = await issuer.create_credential(
        {"attrNames": ["name"]},
        {"cred_def_id": "cd"},
        {"prover_did": "did:sov:abc"},
        {"name": "Alice"},
        revoc_reg_id="rr",
    )
    assert isinstance(cred_json, str)
    assert cred_rev_id == "1"


@pytest.mark.asyncio
async def test_create_credential_entropy_fallback(patched_issuer, monkeypatch):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)
    async with prof.session() as s:
        await s.handle.insert(m.CATEGORY_CRED_DEF, "cd", b"{}")
        await s.handle.insert(m.CATEGORY_CRED_DEF_PRIVATE, "cd", b"{}")

    class _Cred:
        @staticmethod
        def create(*a, **k):
            return types.SimpleNamespace(to_json=lambda: "{}"), None, None

    monkeypatch.setattr(m, "Credential", _Cred)
    cred_json, cred_rev_id = await issuer.create_credential(
        {"attrNames": ["name"]},
        {"cred_def_id": "cd"},
        {"entropy": "did:sov:abc"},
        {"name": "Alice"},
    )
    assert isinstance(cred_json, str)


@pytest.mark.asyncio
async def test_save_revocation_updates_error_path(patched_issuer):
    m = patched_issuer
    prof = _Profile()

    class _TestIssuer(m.KanonIndyCredxIssuer):
        async def merge_revocation_registry_deltas(
            self, fro_delta: str, to_delta: str
        ) -> str:
            return "{}"

        async def create_and_store_revocation_registry(self, *a, **k):
            return ("rev", "{}", "{}")

    issuer = _TestIssuer(prof)

    class _HBad(_Handle):
        async def fetch(self, cat, name, for_update=False):
            if str(cat).endswith("info"):
                return types.SimpleNamespace(value_json={"curr_id": 1, "used_ids": []})
            return types.SimpleNamespace(raw_value=b"{}")

        async def replace(self, *a, **k):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.WRAPPER, "x")

    class _Sess(_Txn):
        def __init__(self, h):
            super().__init__(h)
            self.handle = _HBad()

    class _P(_Profile):
        def transaction(self):
            return _Sess(self.h)

    issuer._profile = _P()
    with pytest.raises(m.IndyIssuerError):
        await issuer._save_revocation_updates(
            "rr",
            types.SimpleNamespace(to_json_buffer=lambda: b"{}"),
            {"curr_id": 1, "used_ids": []},
            {2},
        )
