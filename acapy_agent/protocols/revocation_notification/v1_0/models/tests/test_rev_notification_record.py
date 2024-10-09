"""Test RevNotificationRecord."""

import pytest

from ......core.in_memory import InMemoryProfile
from ......storage.error import StorageDuplicateError, StorageNotFoundError
from ...messages.revoke import Revoke
from ..rev_notification_record import RevNotificationRecord


@pytest.fixture
def profile():
    yield InMemoryProfile.test_profile()


@pytest.fixture
def rec():
    yield RevNotificationRecord(
        rev_reg_id="mock_rev_reg_id",
        cred_rev_id="mock_cred_rev_id",
        connection_id="mock_connection_id",
        thread_id="mock_thread_id",
        comment="mock_comment",
        version="v1_0",
    )


@pytest.mark.asyncio
async def test_storage(profile, rec):
    async with profile.session() as session:
        await rec.save(session)
        recalled = await RevNotificationRecord.retrieve_by_id(
            session, rec.revocation_notification_id
        )
        assert recalled == rec
        recalled = await RevNotificationRecord.query_by_ids(
            session, cred_rev_id="mock_cred_rev_id", rev_reg_id="mock_rev_reg_id"
        )
        assert recalled == rec
        [recalled] = await RevNotificationRecord.query_by_rev_reg_id(
            session, rev_reg_id="mock_rev_reg_id"
        )
        assert recalled == rec

        with pytest.raises(StorageNotFoundError):
            await RevNotificationRecord.query_by_ids(
                session, cred_rev_id="unknown", rev_reg_id="unknown"
            )

        with pytest.raises(StorageDuplicateError):
            another = RevNotificationRecord(
                rev_reg_id="mock_rev_reg_id",
                cred_rev_id="mock_cred_rev_id",
                version="v1_0",
            )
            await another.save(session)
            await RevNotificationRecord.query_by_ids(
                session, cred_rev_id="mock_cred_rev_id", rev_reg_id="mock_rev_reg_id"
            )


def test_to_message(rec):
    message = rec.to_message()
    assert isinstance(message, Revoke)
    assert message.thread_id == rec.thread_id
    assert message.comment == rec.comment

    with pytest.raises(ValueError):
        rec.thread_id = None
        rec.to_message()
