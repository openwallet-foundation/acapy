import types
import pytest


@pytest.mark.asyncio
async def test_init_ledger_pool_disabled_and_read_only_logs(monkeypatch, caplog):
    from acapy_agent.kanon.profile_anon_kanon import KanonAnonCredsProfile
    from acapy_agent.config.injection_context import InjectionContext

    class _Opened:
        def __init__(self):
            self.db_store = types.SimpleNamespace()
            self.askar_store = types.SimpleNamespace()
            self.name = "p"
            self.created = True
        async def close(self):
            pass

    ctx = InjectionContext(settings={
        "ledger.disabled": True,
    })
    prof = KanonAnonCredsProfile(_Opened(), ctx)
    assert prof.ledger_pool is None


    ctx2 = InjectionContext(settings={
        "ledger.genesis_transactions": "{}",
        "ledger.read_only": True,
        "ledger.pool_name": "pool",
        "ledger.keepalive": 3,
    })
    caplog.set_level("WARNING")
    prof2 = KanonAnonCredsProfile(_Opened(), ctx2)

    assert prof2.ledger_pool is not None
    assert any("read-only" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_bind_providers_with_write_ledger_and_endorser(monkeypatch):
    from acapy_agent.kanon.profile_anon_kanon import KanonAnonCredsProfile
    from acapy_agent.config.injection_context import InjectionContext

    class _Opened:
        def __init__(self):
            self.db_store = types.SimpleNamespace()
            self.askar_store = types.SimpleNamespace()
            self.name = "p"
            self.created = True
        async def close(self):
            pass

    ctx = InjectionContext(settings={
        "ledger.ledger_config_list": [
            {
                "id": "l1",
                "genesis_transactions": "{}",
                "is_write": True,
                "read_only": False,
                "keepalive": 2,
                "endorser_alias": "alias",
                "endorser_did": "WgWxqztrNooG92RXvxSTWv",
            }
        ]
    })
    prof = KanonAnonCredsProfile(_Opened(), ctx)
    assert ctx.settings.get_value("ledger.ledger_config_list")
    assert ctx.settings.get_value("ledger.ledger_config_list")[0]["endorser_alias"] == "alias"

