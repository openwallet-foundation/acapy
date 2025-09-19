import pytest

from acapy_agent.database_manager.category_registry import (
    get_release,
    load_release,
    load_schema,
)


def test_load_schema_missing_module_returns_empty(caplog):
    data = load_schema("no_such_category", "0_1")
    assert data["schemas"] == {}
    assert data["columns"] == []
    assert data["drop_schemas"] == {}


def test_load_release_missing_raises():
    with pytest.raises(ValueError) as e:
        load_release("release_9_9")
    assert "not found" in str(e.value)


def test_get_release_release_0_default_handlers_sqlite():
    handlers, schemas, drops = get_release("release_0", "sqlite")
    assert "default" in handlers
    assert schemas["default"] is None
    assert drops["default"] is None


def test_get_release_invalid_release_raises():
    with pytest.raises(ValueError):
        get_release("release_9_9", "sqlite")


def test_get_release_unsupported_db_type_raises():
    with pytest.raises(ValueError):
        get_release("release_0_1", "no_such_db")
