import pytest


class _SessCtx:
    def __init__(self, ok=True):
        self._ok = ok

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def count(self, *_a, **_k):
        if not self._ok:
            raise Exception("x")
        return 0


class _Opened:
    def __init__(self, ok_db=True, ok_kms=True):
        class _DB:
            def session(self, *a, **k):
                return _SessCtx(ok_db)

        class _KMS:
            def session(self, *a, **k):
                return _SessCtx(ok_kms)

        self.db_store = _DB()
        self.askar_store = _KMS()
        self.name = "p"
        self.created = True

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_profile_manager_provision_and_open_success(monkeypatch):
    from acapy_agent.config.injection_context import InjectionContext
    from acapy_agent.kanon import profile_anon_kanon as module

    class _KCfg:
        def __init__(self, cfg):
            pass

        async def open_store(self, provision=False, in_memory=None):
            return _Opened(True, True)

    monkeypatch.setattr(module, "KanonStoreConfig", _KCfg)

    mgr = module.KanonAnonProfileManager()
    ctx = InjectionContext()
    prof = await mgr.provision(ctx, config={"test": True})
    assert isinstance(prof, module.KanonAnonCredsProfile)

    prof2 = await mgr.open(ctx, config={"test": True})
    assert isinstance(prof2, module.KanonAnonCredsProfile)


@pytest.mark.asyncio
async def test_profile_manager_db_kms_no_health_checks(monkeypatch):
    """Test that provision/open succeed without health checks.

    Health checks were removed because they were problematic on PostgreSQL
    where tables don't exist immediately after provisioning. Store failures
    during open_store will still raise appropriate exceptions.
    """
    from acapy_agent.config.injection_context import InjectionContext
    from acapy_agent.kanon import profile_anon_kanon as module

    class _KCfgDBFail:
        def __init__(self, cfg):
            pass

        async def open_store(self, provision=False, in_memory=None):
            return _Opened(False, True)

    class _KCfgKMSFail:
        def __init__(self, cfg):
            pass

        async def open_store(self, provision=False, in_memory=None):
            return _Opened(True, False)

    mgr = module.KanonAnonProfileManager()
    ctx = InjectionContext()

    # These should succeed now - health checks removed
    monkeypatch.setattr(module, "KanonStoreConfig", _KCfgDBFail)
    prof = await mgr.provision(ctx, config={"test": True})
    assert isinstance(prof, module.KanonAnonCredsProfile)

    monkeypatch.setattr(module, "KanonStoreConfig", _KCfgKMSFail)
    prof2 = await mgr.open(ctx, config={"test": True})
    assert isinstance(prof2, module.KanonAnonCredsProfile)


@pytest.mark.asyncio
async def test_generate_store_key(monkeypatch):
    from acapy_agent.kanon import profile_anon_kanon as module

    monkeypatch.setattr(module, "validate_seed", lambda s: b"seed")

    class _Store:
        @staticmethod
        def generate_raw_key(secret):
            return "RAWKEY"

    monkeypatch.setattr(module, "AskarStore", _Store)
    out = await module.KanonAnonProfileManager.generate_store_key(seed="x")
    assert out == "RAWKEY"
