import importlib

import pytest


@pytest.mark.asyncio
async def test_register_backends_success(monkeypatch):
    calls = []

    def _register_backend(db_type, backend):
        calls.append((db_type, type(backend).__name__))

    import acapy_agent.database_manager.databases.backends.backend_registration as br

    importlib.reload(br)
    monkeypatch.setattr(br, "register_backend", _register_backend)
    br.register_backends()

    db_types = [c[0] for c in calls]
    assert "sqlite" in db_types
    assert "postgres" in db_types
    assert "postgresql" in db_types


@pytest.mark.asyncio
async def test_register_backends_importerror_paths(monkeypatch):
    import acapy_agent.database_manager.databases.postgresql_normalized.backend as pg_backend
    import acapy_agent.database_manager.databases.sqlite_normalized.backend as sqlite_backend

    had_sqlite = hasattr(sqlite_backend, "SqliteBackend")
    had_pg = hasattr(pg_backend, "PostgresqlBackend")
    try:
        if had_sqlite:
            monkeypatch.delattr(sqlite_backend, "SqliteBackend", raising=False)
        if had_pg:
            monkeypatch.delattr(pg_backend, "PostgresqlBackend", raising=False)

        calls = []

        def _register_backend(db_type, backend):
            calls.append((db_type, backend))

        import acapy_agent.database_manager.databases.backends.backend_registration as br

        monkeypatch.setattr(br, "register_backend", _register_backend)

        importlib.reload(br)
        br.register_backends()
        assert calls == []
    finally:
        importlib.reload(sqlite_backend)
        importlib.reload(pg_backend)
