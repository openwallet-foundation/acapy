"""Test RevNotificationRecord."""

import pytest
import pytest_asyncio

from ......storage.error import StorageDuplicateError, StorageNotFoundError
from ......utils.testing import create_test_profile
from ...messages.revoke import Revoke
from ..rev_notification_record import RevNotificationRecord


@pytest_asyncio.fixture
async def profile():
    profile = await create_test_profile()
    yield profile


@pytest.fixture
def rec():
    yield RevNotificationRecord(
        rev_reg_id="mock_rev_reg_id",
        cred_rev_id="mock_cred_rev_id",
        connection_id="mock_connection_id",
        thread_id="mock_thread_id",
        comment="mock_comment",
        version="v2_0",
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
                version="v2_0",
            )
            await another.save(session)
            await RevNotificationRecord.query_by_ids(
                session, cred_rev_id="mock_cred_rev_id", rev_reg_id="mock_rev_reg_id"
            )


def test_to_message(rec):
    message = rec.to_message()
    assert isinstance(message, Revoke)
    assert message.credential_id == f"{rec.rev_reg_id}::{rec.cred_rev_id}"
    assert message.comment == rec.comment

    with pytest.raises(ValueError):
        rec.thread_id = None
        rec.to_message()
