"""Tests for event storage manager."""

import json
from datetime import datetime, timedelta, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ....storage.base import BaseStorage
from ....storage.record import StorageRecord
from ....storage.type import (
    EVENT_STATE_REQUESTED,
    EVENT_STATE_RESPONSE_FAILURE,
    EVENT_STATE_RESPONSE_SUCCESS,
    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
)
from ....utils.testing import create_test_profile
from ..auto_recovery import event_storage as event_storage_module
from ..auto_recovery.event_storage import EventStorageManager


@pytest.mark.anoncreds
class TestEventStorageManager(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.profile = await create_test_profile()
        self.session = await self.profile.session()
        self.storage_manager = EventStorageManager(self.session)

    async def asyncTearDown(self):
        await self.profile.close()

    def create_test_record(
        self,
        record_id: str,
        state: str,
        created_at: datetime,
        expiry_timestamp: float = None,
    ) -> StorageRecord:
        """Create a test storage record with specified timestamps."""
        record_data = {
            "event_type": RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            "event_data": {"test": "data"},
            "correlation_id": record_id,
            "request_id": f"req_{record_id}",
            "state": state,
            "options": {},
            "created_at": created_at.isoformat(),
            "expiry_timestamp": expiry_timestamp,
        }

        return StorageRecord(
            RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            json.dumps(record_data),
            tags={"correlation_id": record_id, "state": state},
            id=record_id,
        )

    async def test_cleanup_completed_events_with_timestamps_old_records(self):
        """Test cleanup removes records older than max_age_hours."""
        current_time = datetime.now(timezone.utc)
        old_time = current_time - timedelta(hours=25)  # 25 hours ago

        # Create old completed records
        old_success_record = self.create_test_record(
            "old_success", EVENT_STATE_RESPONSE_SUCCESS, old_time
        )
        old_failure_record = self.create_test_record(
            "old_failure", EVENT_STATE_RESPONSE_FAILURE, old_time
        )

        mock_storage = AsyncMock(spec=BaseStorage)
        mock_storage.find_paginated_records.side_effect = [
            [old_success_record],  # Success records
            [old_failure_record],  # Failure records
        ]

        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        # Run cleanup with 24 hour max age
        cleaned_up = await storage_manager.cleanup_completed_events(
            event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            max_age_hours=24,
        )

        # Should clean up both old records
        assert cleaned_up == 2
        assert mock_storage.delete_record.call_count == 2
        mock_storage.delete_record.assert_any_call(old_success_record)
        mock_storage.delete_record.assert_any_call(old_failure_record)

    async def test_cleanup_completed_events_with_timestamps_recent_records(self):
        """Test cleanup preserves records newer than max_age_hours."""
        current_time = datetime.now(timezone.utc)
        recent_time = current_time - timedelta(hours=12)  # 12 hours ago

        # Create recent completed records
        recent_success_record = self.create_test_record(
            "recent_success", EVENT_STATE_RESPONSE_SUCCESS, recent_time
        )
        recent_failure_record = self.create_test_record(
            "recent_failure", EVENT_STATE_RESPONSE_FAILURE, recent_time
        )

        mock_storage = AsyncMock(spec=BaseStorage)
        mock_storage.find_paginated_records.side_effect = [
            [recent_success_record],  # Success records
            [recent_failure_record],  # Failure records
        ]

        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        # Run cleanup with 24 hour max age
        cleaned_up = await storage_manager.cleanup_completed_events(
            event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            max_age_hours=24,
        )

        # Should not clean up recent records
        assert cleaned_up == 0
        mock_storage.delete_record.assert_not_called()

    async def test_cleanup_completed_events_respects_expiry_timestamp(self):
        """Test cleanup respects expiry_timestamp as minimum cleanup time."""
        current_time = datetime.now(timezone.utc)
        old_time = current_time - timedelta(hours=25)  # 25 hours ago

        # Create record that's old but has future expiry
        future_expiry = (current_time + timedelta(hours=1)).timestamp()
        record_with_future_expiry = self.create_test_record(
            "future_expiry",
            EVENT_STATE_RESPONSE_SUCCESS,
            old_time,
            expiry_timestamp=future_expiry,
        )

        mock_storage = AsyncMock(spec=BaseStorage)
        mock_storage.find_paginated_records.side_effect = [
            [record_with_future_expiry],  # Success records
            [],  # Failure records
        ]

        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        # Run cleanup with 24 hour max age
        cleaned_up = await storage_manager.cleanup_completed_events(
            event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            max_age_hours=24,
        )

        # Should not clean up record with future expiry
        assert cleaned_up == 0
        mock_storage.delete_record.assert_not_called()

    async def test_cleanup_completed_events_expiry_timestamp_in_past(self):
        """Test cleanup works when expiry_timestamp is in the past."""
        current_time = datetime.now(timezone.utc)
        old_time = current_time - timedelta(hours=25)  # 25 hours ago

        # Create record with past expiry (should be cleaned up)
        past_expiry = (current_time - timedelta(hours=1)).timestamp()
        record_with_past_expiry = self.create_test_record(
            "past_expiry",
            EVENT_STATE_RESPONSE_SUCCESS,
            old_time,
            expiry_timestamp=past_expiry,
        )

        mock_storage = AsyncMock(spec=BaseStorage)
        mock_storage.find_paginated_records.side_effect = [
            [record_with_past_expiry],  # Success records
            [],  # Failure records
        ]

        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        # Run cleanup with 24 hour max age
        cleaned_up = await storage_manager.cleanup_completed_events(
            event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            max_age_hours=24,
        )

        # Should clean up record since both age and expiry allow it
        assert cleaned_up == 1
        mock_storage.delete_record.assert_called_once_with(record_with_past_expiry)

    async def test_cleanup_completed_events_missing_created_at(self):
        """Test cleanup skips records missing created_at timestamp."""
        # Create record without created_at
        record_data = {
            "event_type": RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            "event_data": {"test": "data"},
            "correlation_id": "no_created_at",
            "state": EVENT_STATE_RESPONSE_SUCCESS,
            "options": {},
            # Missing created_at field
        }

        record_without_created_at = StorageRecord(
            RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            json.dumps(record_data),
            tags={
                "correlation_id": "no_created_at",
                "state": EVENT_STATE_RESPONSE_SUCCESS,
            },
            id="no_created_at",
        )

        mock_storage = AsyncMock(spec=BaseStorage)
        mock_storage.find_paginated_records.side_effect = [
            [record_without_created_at],  # Success records
            [],  # Failure records
        ]

        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        # Run cleanup
        cleaned_up = await storage_manager.cleanup_completed_events(
            event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            max_age_hours=24,
        )

        # Should skip record without created_at
        assert cleaned_up == 0
        mock_storage.delete_record.assert_not_called()

    async def test_cleanup_completed_events_invalid_json(self):
        """Test cleanup handles records with invalid JSON gracefully."""
        # Create record with invalid JSON
        invalid_record = StorageRecord(
            RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            "invalid json {",  # Malformed JSON
            tags={
                "correlation_id": "invalid_json",
                "state": EVENT_STATE_RESPONSE_SUCCESS,
            },
            id="invalid_json",
        )

        mock_storage = AsyncMock(spec=BaseStorage)
        mock_storage.find_paginated_records.side_effect = [
            [invalid_record],  # Success records
            [],  # Failure records
        ]

        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        # Run cleanup
        cleaned_up = await storage_manager.cleanup_completed_events(
            event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            max_age_hours=24,
        )

        # Should skip record with invalid JSON
        assert cleaned_up == 0
        mock_storage.delete_record.assert_not_called()

    async def test_cleanup_completed_events_mixed_scenarios(self):
        """Test cleanup with mixed scenarios: old, recent, with/without expiry."""
        current_time = datetime.now(timezone.utc)
        old_time = current_time - timedelta(hours=25)  # 25 hours ago
        recent_time = current_time - timedelta(hours=12)  # 12 hours ago

        # Create various test records
        old_cleanable = self.create_test_record(
            "old_cleanable", EVENT_STATE_RESPONSE_SUCCESS, old_time
        )
        old_with_future_expiry = self.create_test_record(
            "old_future_expiry",
            EVENT_STATE_RESPONSE_SUCCESS,
            old_time,
            expiry_timestamp=(current_time + timedelta(hours=1)).timestamp(),
        )
        recent_not_cleanable = self.create_test_record(
            "recent", EVENT_STATE_RESPONSE_FAILURE, recent_time
        )
        old_with_past_expiry = self.create_test_record(
            "old_past_expiry",
            EVENT_STATE_RESPONSE_FAILURE,
            old_time,
            expiry_timestamp=(current_time - timedelta(hours=1)).timestamp(),
        )

        mock_storage = AsyncMock(spec=BaseStorage)
        mock_storage.find_paginated_records.side_effect = [
            [
                old_cleanable,
                old_with_future_expiry,
                recent_not_cleanable,
            ],  # Success records
            [old_with_past_expiry],  # Failure records
        ]

        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        # Run cleanup with 24 hour max age
        cleaned_up = await storage_manager.cleanup_completed_events(
            event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            max_age_hours=24,
        )

        # Should clean up: old_cleanable and old_with_past_expiry (2 records)
        # Should NOT clean up: old_with_future_expiry and recent_not_cleanable
        assert cleaned_up == 2
        assert mock_storage.delete_record.call_count == 2
        mock_storage.delete_record.assert_any_call(old_cleanable)
        mock_storage.delete_record.assert_any_call(old_with_past_expiry)

    async def test_cleanup_completed_events_all_event_types(self):
        """Test cleanup works when no specific event_type is provided."""
        current_time = datetime.now(timezone.utc)
        old_time = current_time - timedelta(hours=25)  # 25 hours ago

        old_record = self.create_test_record(
            "old_record", EVENT_STATE_RESPONSE_SUCCESS, old_time
        )

        mock_storage = AsyncMock(spec=BaseStorage)
        # Mock will be called for each event type in all_event_types
        mock_storage.find_paginated_records.return_value = [old_record]

        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        # Run cleanup for all event types (event_type=None)
        cleaned_up = await storage_manager.cleanup_completed_events(
            event_type=None,
            max_age_hours=24,
        )

        # Should clean up records (exact count depends on number of event types)
        assert cleaned_up > 0
        mock_storage.delete_record.assert_called()

    async def test_cleanup_completed_events_storage_error(self):
        """Test cleanup handles storage errors gracefully."""
        mock_storage = AsyncMock(spec=BaseStorage)
        mock_storage.find_paginated_records.side_effect = Exception("Storage error")

        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        # Run cleanup - should not raise exception
        cleaned_up = await storage_manager.cleanup_completed_events(
            event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            max_age_hours=24,
        )

        # Should return 0 due to error
        assert cleaned_up == 0

    async def test_get_failed_events_pages_through_storage(self):
        """Failed-event retrieval pages through storage instead of loading all."""
        current_time = datetime.now(timezone.utc)
        records = [
            self.create_test_record(
                f"failed_{i}", EVENT_STATE_RESPONSE_FAILURE, current_time
            )
            for i in range(3)
        ]

        mock_storage = AsyncMock(spec=BaseStorage)
        # With a batch size of 2: a full first page then a partial page ends paging.
        mock_storage.find_paginated_records.side_effect = [records[:2], records[2:]]
        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        with patch.object(event_storage_module, "EVENT_SCAN_BATCH_SIZE", 2):
            failed = await storage_manager.get_failed_events(
                event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT
            )

        mock_storage.find_all_records.assert_not_called()
        assert len(failed) == 3
        assert mock_storage.find_paginated_records.await_count == 2
        calls = mock_storage.find_paginated_records.await_args_list
        assert calls[0].kwargs["offset"] == 0
        assert calls[0].kwargs["tag_query"] == {"state": EVENT_STATE_RESPONSE_FAILURE}
        assert calls[1].kwargs["offset"] == 2

    async def test_get_in_progress_events_pages_through_storage(self):
        """In-progress retrieval pages through storage and filters by state."""
        current_time = datetime.now(timezone.utc)
        records = [
            self.create_test_record(f"req_{i}", EVENT_STATE_REQUESTED, current_time)
            for i in range(3)
        ]

        mock_storage = AsyncMock(spec=BaseStorage)
        mock_storage.find_paginated_records.side_effect = [records[:2], records[2:]]
        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        with patch.object(event_storage_module, "EVENT_SCAN_BATCH_SIZE", 2):
            in_progress = await storage_manager.get_in_progress_events(
                event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT
            )

        mock_storage.find_all_records.assert_not_called()
        assert len(in_progress) == 3
        calls = mock_storage.find_paginated_records.await_args_list
        assert calls[0].kwargs["tag_query"] == {"state": EVENT_STATE_REQUESTED}

    async def test_cleanup_pages_and_accounts_for_deletions(self):
        """Cleanup pages through storage and advances offset past kept records."""
        current_time = datetime.now(timezone.utc)
        old_time = current_time - timedelta(hours=25)
        recent_time = current_time - timedelta(hours=1)

        # A full first page (batch size 2): one kept (recent) + one deleted (old).
        kept = self.create_test_record("kept", EVENT_STATE_RESPONSE_SUCCESS, recent_time)
        deleted = self.create_test_record(
            "deleted", EVENT_STATE_RESPONSE_SUCCESS, old_time
        )

        mock_storage = AsyncMock(spec=BaseStorage)
        # SUCCESS: full page [kept, deleted] then empty; FAILURE: empty.
        mock_storage.find_paginated_records.side_effect = [
            [kept, deleted],
            [],
            [],
        ]
        self.session.inject = MagicMock(return_value=mock_storage)
        storage_manager = EventStorageManager(self.session)

        with patch.object(event_storage_module, "EVENT_SCAN_BATCH_SIZE", 2):
            cleaned_up = await storage_manager.cleanup_completed_events(
                event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                max_age_hours=24,
            )

        assert cleaned_up == 1
        mock_storage.delete_record.assert_called_once_with(deleted)
        success_calls = [
            c
            for c in mock_storage.find_paginated_records.await_args_list
            if c.kwargs["tag_query"] == {"state": EVENT_STATE_RESPONSE_SUCCESS}
        ]
        # One record was deleted from the full first page, so the next SUCCESS page
        # is fetched at offset 1 (2 scanned - 1 removed).
        assert success_calls[0].kwargs["offset"] == 0
        assert success_calls[1].kwargs["offset"] == 1
