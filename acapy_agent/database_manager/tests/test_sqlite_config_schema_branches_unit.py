import pytest

from acapy_agent.database_manager.databases.sqlite_normalized.config import SqliteConfig


@pytest.mark.asyncio
async def test_sqlite_config_provision_bad_schema_entries(monkeypatch, tmp_path):
    db_path = tmp_path / "schema.db"
    cfg = SqliteConfig(uri=f"sqlite://{db_path}", schema_config="normalize")

    from acapy_agent.database_manager.databases.sqlite_normalized import config as cfg_mod

    def _bad_get_release(release_number: str, db_type: str):
        return (
            {
                "default": object(),
                "cat1": object(),
            },
            {
                "default": {"sqlite": [""]},
                "cat1": None,
                "cat2": {"sqlite": ["CREATE TABLE IF NOT EXISTS bad("]},
            },
            {},
        )

    monkeypatch.setattr(cfg_mod, "get_release", _bad_get_release)

    with pytest.raises(Exception):
        cfg.provision(profile="p", recreate=True, release_number="release_0_1")
