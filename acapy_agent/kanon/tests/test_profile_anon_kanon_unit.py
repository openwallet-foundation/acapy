import pytest


class _FakeDBHandle:
    def __init__(self, is_txn: bool):
        self.is_transaction = is_txn
        self.closed = False
        self.committed = False

    async def commit(self):
        self.committed = True

    async def close(self):
        self.closed = True

    async def count(self, *_a, **_k):
        return 0


class _FakeKMSHandle:
    def __init__(self, is_txn: bool):
        self.is_transaction = is_txn
        self.closed = False
        self.committed = False

    async def commit(self):
        self.committed = True

    async def close(self):
        self.closed = True

    async def count(self, *_a, **_k):
        return 0


class _FakeDBStore:
    def __init__(self):
        self.removed = []

    def session(self, *_a, **_k):
        async def _open():
            return _FakeDBHandle(False)

        return _open()

    def transaction(self, *_a, **_k):
        async def _open():
            return _FakeDBHandle(True)

        return _open()

    async def remove_profile(self, name):
        self.removed.append(name)


class _FakeAskarStore:
    def __init__(self):
        self.removed = []

    def session(self, *_a, **_k):
        async def _open():
            return _FakeKMSHandle(False)

        return _open()

    def transaction(self, *_a, **_k):
        async def _open():
            return _FakeKMSHandle(True)

        return _open()

    async def remove_profile(self, name):
        self.removed.append(name)


class _FakeOpened:
    def __init__(self, name="prof"):
        self.db_store = _FakeDBStore()
        self.askar_store = _FakeAskarStore()
        self.name = name
        self.created = False

    async def close(self):
        if hasattr(self.db_store, "close"):
            await self.db_store.close()
        if hasattr(self.askar_store, "close"):
            await self.askar_store.close()


@pytest.mark.asyncio
async def test_profile_remove_success_and_error(monkeypatch):
    from acapy_agent.core.error import ProfileError
    from acapy_agent.kanon.profile_anon_kanon import KanonAnonCredsProfile

    opened = _FakeOpened("p1")
    prof = KanonAnonCredsProfile(opened)

    await prof.remove()

    async def fail_db(name):
        raise Exception("dbfail")

    async def fail_kms(name):
        raise Exception("kmsfail")

    opened.db_store.remove_profile = fail_db
    opened.askar_store.remove_profile = fail_kms

    prof.profile_id = "p1"
    with pytest.raises(ProfileError):
        await prof.remove()


@pytest.mark.asyncio
async def test_session_setup_teardown_and_is_transaction(monkeypatch):
    from acapy_agent.kanon.profile_anon_kanon import (
        KanonAnonCredsProfile,
        KanonAnonCredsProfileSession,
    )

    opened = _FakeOpened("p1")
    prof = KanonAnonCredsProfile(opened, profile_id="p1")

    sess = KanonAnonCredsProfileSession(prof, False)
    await sess._setup()
    assert sess.is_transaction is False
    await sess._teardown(commit=None)

    sess2 = KanonAnonCredsProfileSession(prof, True)
    await sess2._setup()
    assert sess2.is_transaction is True
    await sess2._teardown(commit=True)


@pytest.mark.asyncio
async def test_session_teardown_commit_errors(monkeypatch):
    from acapy_agent.core.error import ProfileError
    from acapy_agent.kanon.profile_anon_kanon import (
        KanonAnonCredsProfile,
        KanonAnonCredsProfileSession,
    )

    class _BadDB(_FakeDBStore):
        def transaction(self, *_a, **_k):
            async def _open():
                h = _FakeDBHandle(True)
                from acapy_agent.database_manager.dbstore import (
                    DBStoreError,
                    DBStoreErrorCode,
                )

                async def bad_commit():
                    raise DBStoreError(
                        code=DBStoreErrorCode.WRAPPER, message="bad commit"
                    )

                h.commit = bad_commit
                return h

            return _open()

    opened = _FakeOpened("p1")
    opened.db_store = _BadDB()
    prof = KanonAnonCredsProfile(opened, profile_id="p1")

    sess = KanonAnonCredsProfileSession(prof, True)
    await sess._setup()
    with pytest.raises(ProfileError):
        await sess._teardown(commit=True)


@pytest.mark.asyncio
async def test_profile_close_closes_both(monkeypatch):
    from acapy_agent.kanon.profile_anon_kanon import KanonAnonCredsProfile

    class _CDB(_FakeDBStore):
        def __init__(self):
            super().__init__()
            self.closed = False

        async def close(self, remove=False):
            self.closed = True

    class _CKMS(_FakeAskarStore):
        def __init__(self):
            super().__init__()
            self.closed = False

        async def close(self, remove=False):
            self.closed = True

    opened = _FakeOpened("p1")
    opened.db_store = _CDB()
    opened.askar_store = _CKMS()
    prof = KanonAnonCredsProfile(opened)
    await prof.close()
    assert opened.db_store.closed is True
    assert opened.askar_store.closed is True
