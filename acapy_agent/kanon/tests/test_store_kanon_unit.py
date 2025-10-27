import json

import pytest


def _base_config(sqlite=True):
    return {
        "name": "test",
        "storage_type": "sqlite" if sqlite else "postgres_storage",
        "dbstore_storage_type": "sqlite" if sqlite else "postgres_storage",
        "test": True,
    }


@pytest.mark.asyncio
async def test_sqlite_uris_and_open_remove(monkeypatch, tmp_path):
    from acapy_agent.kanon.store_kanon import KanonOpenStore, KanonStoreConfig

    cfg = KanonStoreConfig(_base_config(sqlite=True))

    class _DB:
        def __init__(self):
            self.closed = False

        async def close(self, remove=False):
            self.closed = True

    class _KMS:
        def __init__(self):
            self.closed = False

        async def close(self, remove=False):
            self.closed = True

    async def _db_open(uri, *a, **k):
        return _DB()

    async def _kms_open(uri, *a, **k):
        return _KMS()

    monkeypatch.setattr("acapy_agent.kanon.store_kanon.DBStore.open", _db_open)
    monkeypatch.setattr("acapy_agent.kanon.store_kanon.Store.open", _kms_open)

    opened = await cfg.open_store(provision=False, in_memory=True)
    assert isinstance(opened, KanonOpenStore)
    assert opened.name == "test"
    await opened.close()


@pytest.mark.asyncio
async def test_postgres_missing_config_errors(monkeypatch):
    from acapy_agent.kanon.store_kanon import KanonStoreConfig, ProfileError

    cfg = {
        **_base_config(sqlite=False),
        "storage_config": json.dumps({"url": "localhost:5432/db"}),
        "storage_creds": json.dumps({"account": "a", "password": "p"}),
        "dbstore_storage_config": json.dumps({"url": "localhost:5432/db"}),
        "dbstore_storage_creds": json.dumps({"account": "a", "password": "p"}),
    }

    sc = KanonStoreConfig(cfg)
    dbstore_uri = sc.get_dbstore_uri(create=False)
    askar_uri = sc.get_askar_uri(create=False)

    assert "postgres" in dbstore_uri
    assert "postgres" in askar_uri

    # Verify password is included in URIs (not replaced with ***)
    assert "a:p@" in dbstore_uri, "DBStore URI should contain actual password"
    assert "a:p@" in askar_uri, "Askar URI should contain actual password"
    assert "***" not in dbstore_uri, "DBStore URI should not contain *** placeholder"
    assert "***" not in askar_uri, "Askar URI should not contain *** placeholder"

    bad_cfg = {**cfg}
    bad_cfg["dbstore_storage_config"] = json.dumps({})
    with pytest.raises(ProfileError):
        KanonStoreConfig(bad_cfg).get_dbstore_uri()

    bad_cfg2 = {**cfg}
    bad_cfg2["storage_config"] = json.dumps({})
    with pytest.raises(ProfileError):
        KanonStoreConfig(bad_cfg2).get_askar_uri()

    bad_tls = {**cfg}
    bad_tls["dbstore_storage_config"] = json.dumps(
        {"url": "host/db", "tls": {"sslmode": "bad"}}
    )
    with pytest.raises(ProfileError):
        KanonStoreConfig(bad_tls).get_dbstore_uri()

    bad_creds = {**cfg}
    bad_creds["dbstore_storage_creds"] = "{"  # invalid JSON
    with pytest.raises(ProfileError):
        KanonStoreConfig(bad_creds)


@pytest.mark.asyncio
async def test_open_error_translation_and_rekey(monkeypatch):
    from aries_askar import AskarError, AskarErrorCode

    from acapy_agent.database_manager.dbstore import DBStoreError, DBStoreErrorCode
    from acapy_agent.kanon.store_kanon import KanonStoreConfig, ProfileError

    cfg = KanonStoreConfig({"name": "t", "rekey": "rk", "dbstore_key": "dk"})

    class _DB:
        async def rekey(self, *a, **k):
            pass

    class _KMS:
        async def rekey(self, *a, **k):
            pass

    async def _db_open_fail(uri, *a, **k):
        raise DBStoreError(code=DBStoreErrorCode.NOT_FOUND, message="x")

    async def _kms_open_fail(uri, *a, **k):
        raise AskarError(AskarErrorCode.NOT_FOUND, "x")

    async def _kms_open_retry(uri, *a, **k):
        return _KMS()

    monkeypatch.setattr("acapy_agent.kanon.store_kanon.DBStore.open", _db_open_fail)
    with pytest.raises(ProfileError):
        await cfg.open_store(provision=False, in_memory=True)

    async def _db_open_dup(uri, *a, **k):
        raise DBStoreError(code=DBStoreErrorCode.DUPLICATE, message="dup")

    monkeypatch.setattr("acapy_agent.kanon.store_kanon.DBStore.open", _db_open_dup)
    with pytest.raises(ProfileError):
        await cfg.open_store(provision=False, in_memory=True)

    async def _db_open_ok(uri, *a, **k):
        return _DB()

    monkeypatch.setattr("acapy_agent.kanon.store_kanon.DBStore.open", _db_open_ok)
    monkeypatch.setattr("acapy_agent.kanon.store_kanon.Store.open", _kms_open_fail)
    monkeypatch.setattr("acapy_agent.kanon.store_kanon.Store.open", _kms_open_retry)
    opened = await cfg.open_store(provision=False, in_memory=True)
    assert opened is not None

    async def _kms_dup(uri, *a, **k):
        from aries_askar import AskarError

        raise AskarError(AskarErrorCode.DUPLICATE, "x")

    async def _kms_nf(uri, *a, **k):
        from aries_askar import AskarError

        raise AskarError(AskarErrorCode.NOT_FOUND, "x")

    cfg2 = KanonStoreConfig({"name": "t2"})
    monkeypatch.setattr("acapy_agent.kanon.store_kanon.DBStore.open", _db_open_ok)
    monkeypatch.setattr("acapy_agent.kanon.store_kanon.Store.open", _kms_dup)
    with pytest.raises(ProfileError):
        await cfg2.open_store(provision=False, in_memory=True)
    monkeypatch.setattr("acapy_agent.kanon.store_kanon.Store.open", _kms_nf)
    with pytest.raises(ProfileError):
        await cfg2.open_store(provision=False, in_memory=True)


@pytest.mark.asyncio
async def test_remove_store_mappings(monkeypatch):
    from aries_askar import AskarError, AskarErrorCode

    from acapy_agent.database_manager.dbstore import DBStoreError, DBStoreErrorCode
    from acapy_agent.kanon.store_kanon import KanonStoreConfig, ProfileNotFoundError

    cfg = KanonStoreConfig({"name": "t"})

    async def _kms_remove(uri):
        raise AskarError(AskarErrorCode.NOT_FOUND, "x")

    monkeypatch.setattr("acapy_agent.kanon.store_kanon.Store.remove", _kms_remove)
    cfg.store_class = "askar"
    with pytest.raises(ProfileNotFoundError):
        await cfg.remove_store()

    async def _db_remove(uri, *a, **k):
        raise DBStoreError(code=DBStoreErrorCode.NOT_FOUND, message="x")

    monkeypatch.setattr("acapy_agent.kanon.store_kanon.DBStore.remove", _db_remove)
    cfg.store_class = "dbstore"
    with pytest.raises(ProfileNotFoundError):
        await cfg.remove_store()
