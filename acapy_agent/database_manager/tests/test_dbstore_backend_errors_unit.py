import pytest

from acapy_agent.database_manager.dbstore import DBStore, register_backend
from acapy_agent.database_manager.error import DBStoreError, DBStoreErrorCode
from acapy_agent.database_manager.interfaces import DatabaseBackend


class _FailBackend(DatabaseBackend):
    def provision(self, *args, **kwargs):
        raise RuntimeError("prov fail")

    def open(self, *args, **kwargs):
        raise RuntimeError("open fail")

    def remove(self, *args, **kwargs):
        raise RuntimeError("remove fail")

    def translate_error(self, exception):
        return DBStoreError(code=DBStoreErrorCode.UNEXPECTED, message=str(exception))


@pytest.mark.asyncio
async def test_dbstore_provision_open_remove_error_mapping(monkeypatch):
    # Register a failing backend under a fake scheme
    register_backend("failscheme", _FailBackend())

    uri = "failscheme://path"
    with pytest.raises(DBStoreError):
        await DBStore.provision(uri=uri, profile="p", recreate=True)
    with pytest.raises(DBStoreError):
        await DBStore.open(uri=uri, profile="p")
    with pytest.raises(DBStoreError):
        await DBStore.remove(uri=uri)

    # Unsupported scheme should raise BACKEND error
    with pytest.raises(DBStoreError) as e:
        await DBStore.provision(uri="unknown://path")
    assert e.value.code == DBStoreErrorCode.BACKEND
