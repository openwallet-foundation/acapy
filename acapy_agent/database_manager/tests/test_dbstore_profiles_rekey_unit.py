import pytest

from acapy_agent.database_manager.dbstore import DBStore
from acapy_agent.database_manager.error import DBStoreError, DBStoreErrorCode
from acapy_agent.database_manager.interfaces import AbstractDatabaseStore


class _ProfileDB(AbstractDatabaseStore):
    release_number = "release_0"

    def __init__(self, fail=False):
        self.fail = fail
        self.name = "p"

    async def create_profile(self, name: str = None) -> str:
        if self.fail:
            raise RuntimeError("create_fail")
        self.name = name or "p"
        return self.name

    async def get_profile_name(self) -> str:
        if self.fail:
            raise RuntimeError("get_fail")
        return self.name

    async def remove_profile(self, name: str) -> bool:
        if self.fail:
            raise RuntimeError("remove_fail")
        return True

    async def rekey(self, key_method: str = None, pass_key: str = None):
        if self.fail:
            raise RuntimeError("rekey_fail")
        return None

    def scan(self, *args, **kwargs):
        return iter(())

    def scan_keyset(self, *args, **kwargs):
        return iter(())

    def session(self, *args, **kwargs):
        return self

    def transaction(self, *args, **kwargs):
        return self

    async def close(self, remove: bool = False) -> bool:
        return True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def translate_error(self, e):
        return DBStoreError(code=DBStoreErrorCode.UNEXPECTED, message=str(e))


@pytest.mark.asyncio
async def test_dbstore_profile_ops_success():
    store = DBStore(_ProfileDB(fail=False), uri="sqlite://:memory:")
    assert await store.create_profile("q") == "q"
    assert await store.get_profile_name() == "q"
    assert await store.remove_profile("q") is True
    await store.rekey(pass_key="pk")


@pytest.mark.asyncio
async def test_dbstore_profile_ops_error_mapping():
    store = DBStore(_ProfileDB(fail=True), uri="sqlite://:memory:")
    for coro in (
        store.create_profile(),
        store.get_profile_name(),
        store.remove_profile("p"),
        store.rekey(pass_key="pk"),
    ):
        with pytest.raises(DBStoreError):
            await coro
