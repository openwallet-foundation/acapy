import types

import pytest


class _Settings:
    def __init__(self, data=None):
        self._data = data or {}

    def get(self, k, d=None):
        return self._data.get(k, d)

    def extend(self, m):
        return _Settings({**self._data, **m})


class _Context:
    def __init__(self):
        from acapy_agent.config.injection_context import InjectionContext

        self._ctx = InjectionContext(settings={"wallet.key": "", "wallet.rekey": None})

    @property
    def settings(self):
        return self._ctx.settings

    @settings.setter
    def settings(self, s):
        self._ctx.settings = s

    def copy(self):
        return self._ctx.copy()


class _Opened:
    def __init__(self):
        self.name = "p"
        self.created = True

        # Provide minimal stores to support profile.remove()
        class _S:
            async def remove_profile(self, pid):
                return None

        self.db_store = _S()
        self.askar_store = _S()


class _KanonProfile:
    def __init__(self):
        self.opened = _Opened()
        self.context = _Context()

        async def _create_profile(pid):
            return None

        self.store = types.SimpleNamespace(create_profile=_create_profile)


class _WalletRecord:
    def __init__(self, wid, settings=None):
        self.wallet_id = wid
        self.settings = settings or {}
        self.wallet_dispatch_type = None
        self.wallet_webhook_urls = []


@pytest.mark.asyncio
async def test_single_wallet_manager_flow(monkeypatch):
    from acapy_agent.multitenant import single_wallet_kanon_manager as module
    from acapy_agent.multitenant.single_wallet_kanon_manager import (
        SingleWalletKanonMultitenantManager,
    )

    async def _wallet_config(ctx, provision=False):
        return _KanonProfile(), {}

    monkeypatch.setattr(module, "wallet_config", _wallet_config)

    mgr = SingleWalletKanonMultitenantManager(profile=types.SimpleNamespace())
    base_ctx = _Context()
    wr = _WalletRecord("sub1", {"k": 1})
    prof = await mgr.get_wallet_profile(base_ctx, wr, provision=True)
    assert prof.profile_id == "sub1"
    # Remove
    await mgr.remove_wallet_profile(prof)
