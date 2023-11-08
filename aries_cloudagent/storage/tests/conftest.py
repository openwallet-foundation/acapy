import pytest
from ...storage.record import StorageRecord


@pytest.fixture
def record_factory():
    def _test_record(tags={}):
        return StorageRecord(type="TYPE", value="TEST", tags=tags)

    yield _test_record


@pytest.fixture
def missing():
    yield StorageRecord(type="__MISSING__", value="000000000")
