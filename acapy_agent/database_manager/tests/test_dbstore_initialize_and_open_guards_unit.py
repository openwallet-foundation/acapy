import types

import pytest

from acapy_agent.database_manager.dbstore import DBStore, DBStoreError
from acapy_agent.database_manager.error import DBStoreErrorCode
from acapy_agent.database_manager.interfaces import AbstractDatabaseStore


class _InitFailDB(AbstractDatabaseStore):
    async def create_profile(self, name: str = None) -> str: ...
    async def get_profile_name(self) -> str: ...
    async def remove_profile(self, name: str) -> bool: ...
    async def rekey(self, key_method: str = None, pass_key: str = None): ...
    def scan(self, *args, **kwargs):
        return iter(())

    def scan_keyset(self, *args, **kwargs):
        return iter(())

    def session(self, profile: str = None, release_number: str = "release_0"):
        return types.SimpleNamespace(
            __aenter__=lambda s: s, __aexit__=lambda *a, **k: False
        )

    def transaction(self, profile: str = None, release_number: str = "release_0"):
        return self.session(profile, release_number)

    async def close(self, remove: bool = False) -> bool: ...
    async def initialize(self):
        raise RuntimeError("init fail")

    def translate_error(self, exception):
        return DBStoreError(code=DBStoreErrorCode.UNEXPECTED, message=str(exception))


@pytest.mark.asyncio
async def test_dbstore_initialize_error_translation():
    store = DBStore(_InitFailDB(), uri="sqlite://:memory:")
    with pytest.raises(DBStoreError):
        await store.initialize()


class _OpenTwiceDB(_InitFailDB):
    def __init__(self):
        self._sess = _DummySess()

    def session(self, profile: str = None, release_number: str = "release_0"):
        return self._sess


class _DummySess:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_dbopen_session_double_open_guard():
    store = DBStore(_OpenTwiceDB(), uri="sqlite://:memory:")
    opener = store.session()
    # First open ok
    s1 = await opener
    # Second open should raise wrapper error
    with pytest.raises(DBStoreError):
        await opener._open()
