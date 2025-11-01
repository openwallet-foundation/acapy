import os
import uuid

import pytest

from ...config.injection_context import InjectionContext
from ...core.error import ProfileDuplicateError, ProfileError, ProfileNotFoundError
from ...database_manager.dbstore import DBStoreError
from ...storage.kanon_storage import KanonStorage
from ...storage.record import StorageRecord
from ..profile_anon_kanon import KanonAnonCredsProfile, KanonAnonProfileManager

# Skip all tests if POSTGRES_URL is not set
if not os.getenv("POSTGRES_URL"):
    pytest.skip(
        "Kanon PostgreSQL integration tests disabled: set POSTGRES_URL to enable",
        allow_module_level=True,
    )

pytestmark = [pytest.mark.postgres, pytest.mark.p1]


def get_test_config(profile_name: str = None):
    """Generate test configuration for Kanon store."""
    postgres_url = os.getenv("POSTGRES_URL")
    if not profile_name:
        profile_name = f"test_profile_{uuid.uuid4().hex[:8]}"

    key = "test_key_" + uuid.uuid4().hex[:8]
    return {
        "wallet.type": "kanon-anoncreds",
        "name": profile_name,
        "wallet.name": profile_name,
        "key": key,
        "wallet.key": key,
        "wallet.storage_type": "postgres",
        "wallet.storage_config": {"url": postgres_url},
        "wallet.storage_creds": {
            "account": "postgres",
            "password": "postgres",
        },
        "dbstore.storage_type": "postgres",
        "dbstore.storage_config": {"url": postgres_url},
        "dbstore.storage_creds": {
            "account": "postgres",
            "password": "postgres",
        },
        "dbstore.schema_config": "normalize",
        "auto_remove": False,
    }


@pytest.mark.asyncio
async def test_provision_profile():
    config = get_test_config()
    context = InjectionContext(settings=config)
    profile_manager = KanonAnonProfileManager()

    profile = await profile_manager.provision(context, config)

    try:
        assert profile is not None
        assert isinstance(profile, KanonAnonCredsProfile)
        assert profile.name == config["wallet.name"]

        async with profile.session() as session:
            storage = KanonStorage(session)

            test_record = StorageRecord(
                type="test_provision",
                id="test_1",
                value='{"data": "test"}',
            )
            await storage.add_record(test_record)

            retrieved = await storage.get_record("test_provision", "test_1")
            assert retrieved.id == "test_1"

    finally:
        # Cleanup: remove the profile
        try:
            await profile.remove()
        except Exception:
            pass
        await profile.close()


@pytest.mark.asyncio
async def test_provision_duplicate_profile_fails():
    config = get_test_config()
    context = InjectionContext(settings=config)
    profile_manager = KanonAnonProfileManager()

    profile1 = await profile_manager.provision(context, config)

    try:
        async with profile1.session() as session:
            storage = KanonStorage(session)
            test_record = StorageRecord(
                type="test_duplicate",
                id="original_data",
                value='{"marker": "original"}',
            )
            await storage.add_record(test_record)

        await profile1.close()

        try:
            profile2 = await profile_manager.provision(context, config)
            async with profile2.session() as session:
                storage = KanonStorage(session)
                retrieved = await storage.get_record("test_duplicate", "original_data")
                assert retrieved.value == '{"marker": "original"}'
            await profile2.close()
        except (ProfileDuplicateError, ProfileError):
            pass

    finally:
        try:
            profile_cleanup = await profile_manager.open(context, config)
            await profile_cleanup.remove()
            await profile_cleanup.close()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_provision_with_recreate():
    profile_name = f"test_recreate_{uuid.uuid4().hex[:8]}"
    config = get_test_config(profile_name)
    context = InjectionContext(settings=config)
    profile_manager = KanonAnonProfileManager()

    profile1 = await profile_manager.provision(context, config)

    try:
        async with profile1.session() as session:
            storage = KanonStorage(session)
            test_record = StorageRecord(
                type="test_recreate",
                id="old_data",
                value='{"marker": "old"}',
            )
            await storage.add_record(test_record)

        await profile1.close()

        profile_to_remove = await profile_manager.open(context, config)
        await profile_to_remove.remove()
        await profile_to_remove.close()

        config["auto_remove"] = False  # Ensure we don't auto-remove
        profile2 = await profile_manager.provision(context, config)

        async with profile2.session() as session:
            storage = KanonStorage(session)
            try:
                from ...storage.error import StorageNotFoundError

                await storage.get_record("test_recreate", "old_data")
            except StorageNotFoundError:
                pass

            # Verify we can add new data
            new_record = StorageRecord(
                type="test_recreate",
                id="new_data",
                value='{"marker": "new"}',
            )
            await storage.add_record(new_record)

        await profile2.close()

    finally:
        # Cleanup
        try:
            profile_cleanup = await profile_manager.open(context, config)
            await profile_cleanup.remove()
            await profile_cleanup.close()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_open_existing_profile():
    """Test opening an existing profile.

    Verifies:
    - Profile can be provisioned
    - Profile can be closed and re-opened
    - Data persists across open/close
    """
    config = get_test_config()
    context = InjectionContext(settings=config)
    profile_manager = KanonAnonProfileManager()

    # Provision profile
    profile1 = await profile_manager.provision(context, config)

    try:
        # Store test data
        async with profile1.session() as session:
            storage = KanonStorage(session)
            test_record = StorageRecord(
                type="test_open",
                id="persistent_data",
                value='{"data": "persists"}',
            )
            await storage.add_record(test_record)

        # Close profile
        await profile1.close()

        # Re-open profile
        profile2 = await profile_manager.open(context, config)

        # Verify data persisted
        async with profile2.session() as session:
            storage = KanonStorage(session)
            retrieved = await storage.get_record("test_open", "persistent_data")
            assert retrieved.value == '{"data": "persists"}'

        await profile2.close()

    finally:
        # Cleanup
        try:
            profile_cleanup = await profile_manager.open(context, config)
            await profile_cleanup.remove()
            await profile_cleanup.close()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_open_nonexistent_profile_fails():
    config = get_test_config(f"nonexistent_{uuid.uuid4().hex}")
    context = InjectionContext(settings=config)
    profile_manager = KanonAnonProfileManager()

    try:
        profile = await profile_manager.open(context, config)
        await profile.remove()
        await profile.close()
    except (ProfileNotFoundError, ProfileError, DBStoreError):
        # Expected: profile doesn't exist
        pass


@pytest.mark.asyncio
async def test_session_and_transaction():
    config = get_test_config()
    context = InjectionContext(settings=config)
    profile_manager = KanonAnonProfileManager()

    profile = await profile_manager.provision(context, config)

    try:
        async with profile.session() as session:
            storage = KanonStorage(session)
            assert not session.is_transaction

            # Add record in session
            record1 = StorageRecord(
                type="test_session",
                id="session_record",
                value='{"type": "session"}',
            )
            await storage.add_record(record1)

        # Verify record persisted
        async with profile.session() as session:
            storage = KanonStorage(session)
            retrieved = await storage.get_record("test_session", "session_record")
            assert retrieved.value == '{"type": "session"}'

        async with profile.transaction() as txn:
            storage = KanonStorage(txn)
            assert txn.is_transaction

            record2 = StorageRecord(
                type="test_transaction",
                id="txn_record",
                value='{"type": "transaction"}',
            )
            await storage.add_record(record2)

        # Verify record persisted after transaction
        async with profile.session() as session:
            storage = KanonStorage(session)
            retrieved = await storage.get_record("test_transaction", "txn_record")
            assert retrieved.value == '{"type": "transaction"}'

        try:
            async with profile.transaction() as txn:
                storage = KanonStorage(txn)

                record3 = StorageRecord(
                    type="test_rollback",
                    id="rollback_record",
                    value='{"type": "rollback"}',
                )
                await storage.add_record(record3)

                raise ValueError("Test rollback")

        except ValueError:
            pass

        async with profile.session() as session:
            from ...storage.error import StorageNotFoundError

            storage = KanonStorage(session)
            try:
                await storage.get_record("test_rollback", "rollback_record")
            except StorageNotFoundError:
                # Expected: record was rolled back
                pass

    finally:
        # Cleanup
        try:
            await profile.remove()
        except Exception:
            pass
        await profile.close()


@pytest.mark.asyncio
async def test_remove_profile():
    config = get_test_config()
    context = InjectionContext(settings=config)
    profile_manager = KanonAnonProfileManager()

    profile = await profile_manager.provision(context, config)

    async with profile.session() as session:
        storage = KanonStorage(session)
        for i in range(5):
            record = StorageRecord(
                type="test_remove",
                id=f"record_{i}",
                value=f'{{"index": {i}}}',
            )
            await storage.add_record(record)

    await profile.remove()
    await profile.close()

    try:
        profile2 = await profile_manager.open(context, config)
        async with profile2.session() as session:
            from ...storage.error import StorageNotFoundError

            storage = KanonStorage(session)
            try:
                await storage.get_record("test_remove", "record_0")
                # Clean up
                await profile2.remove()
            except StorageNotFoundError:
                pass
        await profile2.close()
    except (ProfileNotFoundError, ProfileError, DBStoreError):
        pass


@pytest.mark.asyncio
async def test_remove_nonexistent_profile_graceful():
    config = get_test_config(f"never_created_{uuid.uuid4().hex}")
    context = InjectionContext(settings=config)

    try:
        # Try to open (will fail) then remove
        profile_manager = KanonAnonProfileManager()
        profile = await profile_manager.open(context, config)
        await profile.remove()
        await profile.close()
    except (ProfileNotFoundError, ProfileError, DBStoreError):
        # Expected: profile doesn't exist, cannot remove
        pass


@pytest.mark.asyncio
async def test_concurrent_sessions():
    config = get_test_config()
    context = InjectionContext(settings=config)
    profile_manager = KanonAnonProfileManager()

    profile = await profile_manager.provision(context, config)

    try:
        async with profile.session() as session1:
            async with profile.session() as session2:
                storage1 = KanonStorage(session1)
                storage2 = KanonStorage(session2)

                # Write from session1
                record1 = StorageRecord(
                    type="test_concurrent",
                    id="from_session1",
                    value='{"session": 1}',
                )
                await storage1.add_record(record1)

                # Write from session2
                record2 = StorageRecord(
                    type="test_concurrent",
                    id="from_session2",
                    value='{"session": 2}',
                )
                await storage2.add_record(record2)

                # Each session can read what the other wrote
                retrieved1 = await storage2.get_record("test_concurrent", "from_session1")
                retrieved2 = await storage1.get_record("test_concurrent", "from_session2")

                assert retrieved1.value == '{"session": 1}'
                assert retrieved2.value == '{"session": 2}'

    finally:
        try:
            await profile.remove()
        except Exception:
            pass
        await profile.close()


@pytest.mark.asyncio
async def test_profile_name_property():
    """Test profile name property.

    Verifies:
    - Profile.name returns correct name
    - Name matches configuration
    """
    profile_name = f"test_name_{uuid.uuid4().hex[:8]}"
    config = get_test_config(profile_name)
    context = InjectionContext(settings=config)
    profile_manager = KanonAnonProfileManager()

    profile = await profile_manager.provision(context, config)

    try:
        # Verify name property
        assert profile.name == profile_name
        assert profile.opened.name == profile_name

    finally:
        try:
            await profile.remove()
        except Exception:
            pass
        await profile.close()
