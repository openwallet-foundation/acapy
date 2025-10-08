import pytest

from acapy_agent.database_manager.dbstore import DBStore, register_backend
from acapy_agent.database_manager.interfaces import AbstractDatabaseStore, DatabaseBackend


class _OkDB(AbstractDatabaseStore):
    release_number = "release_0"

    async def create_profile(self, name: str = None) -> str:
        return name or "p"

    async def get_profile_name(self) -> str:
        return "p"

    async def remove_profile(self, name: str) -> bool:
        return True

    async def rekey(self, key_method: str = None, pass_key: str = None):
        return None

    def scan(self, *args, **kwargs):
        return iter(())

    def scan_keyset(self, *args, **kwargs):
        return iter(())

    def session(self, profile: str = None, release_number: str = "release_0"):
        return self

    def transaction(self, profile: str = None, release_number: str = "release_0"):
        return self

    async def close(self, remove: bool = False) -> bool:
        return True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _OkBackend(DatabaseBackend):
    def __init__(self):
        self._db = _OkDB()

    def provision(
        self,
        uri,
        key_method,
        pass_key,
        profile,
        recreate,
        release_number: str = "release_0",
        schema_config: str = None,
        config: dict | None = None,
    ):
        return self._db

    def open(
        self,
        uri,
        key_method,
        pass_key,
        profile,
        schema_migration: bool | None = None,
        target_schema_release_number: str | None = None,
        config: dict | None = None,
    ):
        return self._db

    def remove(self, uri, release_number: str = "release_0", config: dict | None = None):
        return True

    def translate_error(self, exception):
        raise exception


@pytest.mark.asyncio
async def test_dbstore_provision_open_remove_success(monkeypatch):
    register_backend("ok", _OkBackend())
    uri = "ok://path"
    store = await DBStore.provision(uri=uri, profile="p", recreate=True)
    assert store.uri == uri
    release_number = store.release_number
    await store.close()

    store2 = await DBStore.open(uri=uri, profile="p")
    assert store2.release_number == release_number
    assert await DBStore.remove(uri=uri) is True
