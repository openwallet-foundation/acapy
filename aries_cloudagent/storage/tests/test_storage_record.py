from ...storage.record import StorageRecord


class TestStorageRecord:
    def test_create(self):
        record_type = "TYPE"
        record_value = "VALUE"
        record = StorageRecord(record_type, record_value)

        assert record.type == record_type
        assert record.value == record_value
        assert record.id and isinstance(record.id, str)
        assert record.tags == {}
