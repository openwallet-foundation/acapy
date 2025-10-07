import types

import pytest


class _Handle:
    def __init__(self):
        self.rows = {}

    def fetch(self, cat, name, for_update=False):
        return self.rows.get((cat, name))

    async def insert(self, cat, name, value, tags=None):
        key = (cat, name)
        if key in self.rows:
            # Simulate duplicate
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.DUPLICATE, "dup")
        self.rows[key] = types.SimpleNamespace(
            raw_value=value,
            value_json=value if isinstance(value, dict) else None,
            tags=tags or {},
        )
        return None

    def remove(self, cat, name):
        self.rows.pop((cat, name), None)

    def replace(self, cat, name, value=None, value_json=None):
        rec = self.rows.get((cat, name))
        if not rec:
            return
        if value is not None:
            rec.raw_value = value
        if value_json is not None:
            rec.value_json = value_json


class _Sess:
    def __init__(self, handle):
        self.handle = handle

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Txn(_Sess):
    def commit(self):
        return None


class _Profile:
    def __init__(self):
        self._handle = _Handle()
        self.settings = {}
        self.store = types.SimpleNamespace(scan=self._scan)
        self.name = "p"

    def session(self):
        return _Sess(self._handle)

    def transaction(self):
        return _Txn(self._handle)

    def _scan(self, category, tag_filter, offset, limit, profile=None):
        async def _gen():
            for (cat, name), rec in self._handle.rows.items():
                if cat == category:
                    yield types.SimpleNamespace(name=name, raw_value=rec.raw_value)

        return _gen()


@pytest.fixture
def patched_holder(monkeypatch):
    from acapy_agent.indy.credx import holder_kanon as module

    class _LinkSecret:
        @staticmethod
        def load(x):
            return "LS"

        @staticmethod
        def create():
            return types.SimpleNamespace(
                to_json_buffer=lambda: b"{}", to_json=lambda: "{}"
            )

    class _CredentialRequest:
        @staticmethod
        def create(did, cred_def, secret, ms_id, offer):
            return types.SimpleNamespace(to_json=lambda: "{}"), types.SimpleNamespace(
                to_json=lambda: "{}"
            )

    class _Credential:
        def __init__(self, sj):
            self._obj = sj

        @staticmethod
        def load(data):
            return _Credential(data)

        def process(self, meta, secret, cred_def, rev_def):
            class _Recv:
                schema_id = "V4SG:2:sch:1.0"
                cred_def_id = "V4SG:3:CL:1:tag"
                rev_reg_id = None

                def to_json_buffer(self):
                    return b"{}"

            return _Recv()

        def to_dict(self):
            return {
                "schema_id": "s",
                "cred_def_id": "d",
                "rev_reg_id": None,
                "values": {"name": {"raw": "Alice"}},
                "signature": {"r_credential": None},
            }

    monkeypatch.setattr(module, "LinkSecret", _LinkSecret)
    monkeypatch.setattr(module, "CredentialRequest", _CredentialRequest)
    monkeypatch.setattr(module, "Credential", _Credential)

    return module


@pytest.mark.asyncio
async def test_get_link_secret_create_and_retry_duplicate(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)
    sec = await holder.get_link_secret()
    assert sec
    sec2 = await holder.get_link_secret()
    assert sec2


@pytest.mark.asyncio
async def test_create_credential_request_and_store_credential(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)
    req, meta = await holder.create_credential_request({}, {}, "did:sov:abc")
    assert isinstance(req, str) and isinstance(meta, str)
    cred_id = await holder.store_credential(
        {"id": "sch"},
        {
            "values": {"name": {"raw": "Alice"}},
            "schema_id": "V4SG:2:sch:1.0",
        },
        {},
        None,
    )
    assert cred_id


@pytest.mark.asyncio
async def test_get_credentials_and_get_credential(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)
    # preload a credential
    async with prof.session() as s:
        await s.handle.insert(m.CATEGORY_CREDENTIAL, "c1", b"{}")
    recs = await holder.get_credentials(offset=0, limit=10, wql={})
    assert isinstance(recs, list)
    data = await holder.get_credential("c1")
    assert isinstance(data, str)


@pytest.mark.asyncio
async def test_create_credential_request_error(patched_holder, monkeypatch):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)

    def _raise(*a, **k):
        raise m.CredxError(1, "x")

    monkeypatch.setattr(m, "CredentialRequest", types.SimpleNamespace(create=_raise))
    with pytest.raises(m.IndyHolderError):
        await holder.create_credential_request({}, {}, "did:sov:abc")


@pytest.mark.asyncio
async def test_store_credential_parse_errors_and_commit_error(
    patched_holder, monkeypatch
):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)

    # schema parse error
    class _BadSchemaCred:
        @staticmethod
        def load(data):
            class _C:
                def process(self, *a, **k):
                    class _Recv:
                        schema_id = "bad"
                        cred_def_id = "V4SG:3:CL:1:tag"
                        rev_reg_id = None

                        def to_json_buffer(self):
                            return b"{}"

                    return _Recv()

            return _C()

    monkeypatch.setattr(m, "Credential", _BadSchemaCred)
    with pytest.raises(m.IndyHolderError):
        await holder.store_credential(
            {"id": "sch"}, {"values": {"name": {"raw": "Alice"}}}, {}, None
        )

    class _BadCredDef:
        @staticmethod
        def load(data):
            class _C:
                def process(self, *a, **k):
                    class _Recv:
                        schema_id = "V4SG:2:sch:1.0"
                        cred_def_id = "bad"
                        rev_reg_id = None

                        def to_json_buffer(self):
                            return b"{}"

                    return _Recv()

            return _C()

    monkeypatch.setattr(m, "Credential", _BadCredDef)
    with pytest.raises(m.IndyHolderError):
        await holder.store_credential(
            {"id": "sch"}, {"values": {"name": {"raw": "Alice"}}}, {}, None
        )

    # commit error mapping
    class _TxnFail(_Txn):
        async def commit(self):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.WRAPPER, "x")

    class _ProfFail(_Profile):
        def transaction(self):
            return _TxnFail(self._handle)

    holderf = m.IndyCredxHolder(_ProfFail())
    monkeypatch.setattr(m, "Credential", patched_holder.Credential)
    with pytest.raises(m.IndyHolderError):
        await holderf.store_credential(
            {"id": "sch"}, {"values": {"name": {"raw": "Alice"}}}, {}, None
        )


@pytest.mark.asyncio
async def test_get_credentials_loading_and_retrieval_errors(patched_holder, monkeypatch):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)
    prof._handle.rows[(m.CATEGORY_CREDENTIAL, "c1")] = types.SimpleNamespace(
        raw_value=b"{}"
    )

    def _raise_load(data):
        raise m.CredxError(1, "x")

    monkeypatch.setattr(m, "Credential", types.SimpleNamespace(load=_raise_load))
    with pytest.raises(m.IndyHolderError):
        await holder.get_credentials(offset=0, limit=10, wql={})

    def _raise_scan(*a, **k):
        from acapy_agent.database_manager.dbstore import DBStoreError, DBStoreErrorCode

        raise DBStoreError(DBStoreErrorCode.WRAPPER, "x")

    prof.store = types.SimpleNamespace(scan=_raise_scan)
    with pytest.raises(m.IndyHolderError):
        await holder.get_credentials(offset=0, limit=10, wql={})


@pytest.mark.asyncio
async def test_get_credentials_for_presentation_unknown_referent(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)
    presentation_request = {"requested_attributes": {}, "requested_predicates": {}}
    with pytest.raises(m.IndyHolderError):
        await holder.get_credentials_for_presentation_request_by_referent(
            presentation_request, ["unknown"], offset=0, limit=10
        )


@pytest.mark.asyncio
async def test_credential_revoked_true_and_false(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)

    class _C:
        def __init__(self, rr_id, idx):
            self.rev_reg_id = rr_id
            self.rev_reg_index = idx

    def _get(cred_id):
        return _C("rr", 3 if cred_id == "c1" else 4)

    holder._get_credential = _get

    class _Ledger:
        def get_revoc_reg_delta(self, rev_reg_id, f, t):
            return ({"value": {"revoked": [3]}}, None)

    ledger = _Ledger()
    assert await holder.credential_revoked(ledger, "c1") is True
    assert await holder.credential_revoked(ledger, "c2") is False


def test_load_link_secret_fallback_paths(patched_holder, monkeypatch):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)

    def _raise_load(raw):
        raise m.CredxError(1, "x")

    monkeypatch.setattr(m, "LinkSecret", types.SimpleNamespace(load=_raise_load))
    record = types.SimpleNamespace(value=b"abc")

    def _ok_load(obj):
        return "LS"

    monkeypatch.setattr(m, "LinkSecret", types.SimpleNamespace(load=_ok_load))
    out = holder._load_link_secret_fallback(record, Exception("orig"))
    assert out == "LS"

    def _raise_again(obj):
        raise m.CredxError(1, "x")

    monkeypatch.setattr(m, "LinkSecret", types.SimpleNamespace(load=_raise_again))
    with pytest.raises(m.IndyHolderError):
        holder._load_link_secret_fallback(record, Exception("orig"))


@pytest.mark.asyncio
async def test_create_and_save_link_secret_duplicate_and_error(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)

    class _H:
        def __init__(self):
            self.calls = 0

        def insert(self, *a, **k):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            self.calls += 1
            if self.calls == 1:
                raise DBStoreError(DBStoreErrorCode.DUPLICATE, "dup")
            return None

    sess = types.SimpleNamespace(handle=_H())
    out = await holder._create_and_save_link_secret(sess)
    assert out is None

    class _HBad:
        def insert(self, *a, **k):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.WRAPPER, "x")

    sess2 = types.SimpleNamespace(handle=_HBad())
    with pytest.raises(m.IndyHolderError):
        await holder._create_and_save_link_secret(sess2)


def test_is_duplicate_error_checks(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)
    from acapy_agent.database_manager.dbstore import DBStoreError, DBStoreErrorCode

    db_dup = DBStoreError(DBStoreErrorCode.DUPLICATE, "dup")
    assert holder._is_duplicate_error(db_dup) is True
    db_other = DBStoreError(DBStoreErrorCode.WRAPPER, "x")
    assert holder._is_duplicate_error(db_other) is False
    from aries_askar import AskarError, AskarErrorCode

    askar_dup = AskarError(AskarErrorCode.DUPLICATE, "dup")
    assert holder._is_duplicate_error(askar_dup) is True


@pytest.mark.asyncio
async def test_delete_credential_not_found_and_error(patched_holder):
    m = patched_holder

    class _HNotFound(_Handle):
        async def remove(self, cat, name):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.NOT_FOUND, "nf")

    class _P1(_Profile):
        def __init__(self):
            super().__init__()
            self._handle = _HNotFound()

    await m.IndyCredxHolder(_P1()).delete_credential("c1")

    class _HBad(_Handle):
        async def remove(self, cat, name):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.WRAPPER, "x")

    class _P2(_Profile):
        def __init__(self):
            super().__init__()
            self._handle = _HBad()

    with pytest.raises(m.IndyHolderError):
        await m.IndyCredxHolder(_P2()).delete_credential("c1")


@pytest.mark.asyncio
async def test_get_mime_type_variants_and_error(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)
    out = await holder.get_mime_type("c1")
    assert out is None
    rec = types.SimpleNamespace(value_json={"name": "text/plain"})
    prof._handle.rows[(m.IndyCredxHolder.RECORD_TYPE_MIME_TYPES, "c1")] = rec
    assert await holder.get_mime_type("c1", attr="name") == "text/plain"
    assert await holder.get_mime_type("c1") == {"name": "text/plain"}

    class _HBad(_Handle):
        async def fetch(self, *a, **k):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.WRAPPER, "x")

    class _PBad(_Profile):
        def __init__(self):
            super().__init__()
            self._handle = _HBad()

    with pytest.raises(m.IndyHolderError):
        await m.IndyCredxHolder(_PBad()).get_mime_type("c1")


def test_build_tag_filter_combination_and_effective_referents(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)
    tag = holder._build_tag_filter({"name"}, {"k": 1}, {"e": 1})
    assert tag["$and"][0] == {"$exist": ["attr::name::value"]}
    pr = {"requested_attributes": {"a": {}}, "requested_predicates": {"p": {}}}
    out = holder._get_effective_referents(pr, [])
    assert "a" in out and "p" in out


@pytest.mark.asyncio
async def test_create_presentation_success_and_error(patched_holder, monkeypatch):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)

    def _ls():
        return "LS"

    monkeypatch.setattr(holder, "get_link_secret", _ls)

    class _Present:
        @staticmethod
        def create(*a, **k):
            return types.SimpleNamespace(to_json=lambda: "{}")

    monkeypatch.setattr(m, "Presentation", _Present)
    req = {"requested_attributes": {}, "requested_predicates": {}}
    out = await holder.create_presentation(
        req, {"requested_attributes": {}, "requested_predicates": {}}, {}, {}
    )
    assert isinstance(out, str)

    class _BadPresent:
        @staticmethod
        def create(*a, **k):
            raise m.CredxError(1, "x")

    monkeypatch.setattr(m, "Presentation", _BadPresent)
    with pytest.raises(m.IndyHolderError):
        await holder.create_presentation(
            req, {"requested_attributes": {}, "requested_predicates": {}}, {}, {}
        )


@pytest.mark.asyncio
async def test_fetch_link_secret_record_error(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)

    class _BadHandle(_Handle):
        async def fetch(self, *a, **k):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.WRAPPER, "x")

    class _SessWrap:
        def __init__(self):
            self.handle = _BadHandle()

    with pytest.raises(m.IndyHolderError):
        await holder._fetch_link_secret_record(_SessWrap())


def test_create_new_link_secret_error(patched_holder, monkeypatch):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)

    def _raise_create():
        raise m.CredxError(1, "x")

    monkeypatch.setattr(m, "LinkSecret", types.SimpleNamespace(create=_raise_create))
    with pytest.raises(m.IndyHolderError):
        holder._create_new_link_secret()


def test_get_rev_state_validation_errors(patched_holder):
    m = patched_holder
    prof = _Profile()
    holder = m.IndyCredxHolder(prof)

    class _C:
        def __init__(self, rr):
            self.rev_reg_id = rr
            self.rev_reg_index = 1

    creds = {"c": _C("rr")}
    with pytest.raises(m.IndyHolderError):
        holder._get_rev_state("c", {"timestamp": 1}, creds, None)
    with pytest.raises(m.IndyHolderError):
        holder._get_rev_state("c", {"timestamp": 1}, creds, {"other": {}})
    with pytest.raises(m.IndyHolderError):
        holder._get_rev_state("c", {"timestamp": 2}, creds, {"rr": {1: {}}})


@pytest.mark.asyncio
async def test_get_credential_error_paths(patched_holder):
    m = patched_holder

    class _HBadFetch(_Handle):
        async def fetch(self, *a, **k):
            from acapy_agent.database_manager.dbstore import (
                DBStoreError,
                DBStoreErrorCode,
            )

            raise DBStoreError(DBStoreErrorCode.WRAPPER, "x")

    class _P1(_Profile):
        def __init__(self):
            super().__init__()
            self._handle = _HBadFetch()

    with pytest.raises(m.IndyHolderError):
        await m.IndyCredxHolder(_P1())._get_credential("c1")

    class _HNone(_Handle):
        async def fetch(self, *a, **k):
            return None

    class _P2(_Profile):
        def __init__(self):
            super().__init__()
            self._handle = _HNone()

    from acapy_agent.wallet.error import WalletNotFoundError

    with pytest.raises(WalletNotFoundError):
        await m.IndyCredxHolder(_P2())._get_credential("c1")

    class _HVal(_Handle):
        async def fetch(self, *a, **k):
            return types.SimpleNamespace(raw_value=b"{}")

    class _P3(_Profile):
        def __init__(self):
            super().__init__()
            self._handle = _HVal()

    def _raise_load(data):
        raise m.CredxError(1, "x")

    from acapy_agent.indy.credx import holder_kanon as module

    module.Credential = types.SimpleNamespace(load=_raise_load)
    with pytest.raises(m.IndyHolderError):
        await m.IndyCredxHolder(_P3())._get_credential("c1")
