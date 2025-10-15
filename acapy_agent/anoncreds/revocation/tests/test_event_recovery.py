"""Test the event recovery module."""

from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ....core.event_bus import EventBus
from ....storage.type import (
    RECORD_TYPE_REV_LIST_CREATE_EVENT,
    RECORD_TYPE_REV_LIST_STORE_EVENT,
    RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
    RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
    RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
)
from ....utils.testing import create_test_profile
from ..auto_recovery.event_recovery import EventRecoveryManager, recover_revocation_events


@pytest.mark.anoncreds
class TestEventRecoveryManager(IsolatedAsyncioTestCase):
    """Test EventRecoveryManager class."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.profile = await create_test_profile()
        self.event_bus = MagicMock(spec=EventBus)
        self.manager = EventRecoveryManager(self.profile, self.event_bus)

    async def asyncTearDown(self):
        """Clean up test fixtures."""
        await self.profile.close()

    def test_init(self):
        """Test EventRecoveryManager initialization."""
        assert self.manager.profile == self.profile
        assert self.manager.event_bus == self.event_bus

    def create_test_event_record(
        self,
        event_type: str,
        correlation_id: str = "test_corr_id",
        event_data: dict = None,
        options: dict = None,
    ) -> dict:
        """Create a test event record."""
        if event_data is None:
            event_data = {"test": "data"}
        if options is None:
            options = {}

        return {
            "event_type": event_type,
            "correlation_id": correlation_id,
            "event_data": event_data,
            "options": options,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.EventStorageManager"
    )
    async def test_recover_in_progress_events_no_events(self, mock_storage_class):
        """Test recover_in_progress_events when no events exist."""
        mock_storage = AsyncMock()
        mock_storage.get_in_progress_events.return_value = []
        mock_storage_class.return_value = mock_storage

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            result = await self.manager.recover_in_progress_events()

            assert result == 0
            mock_storage.get_in_progress_events.assert_called_once_with(only_expired=True)

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.EventStorageManager"
    )
    async def test_recover_in_progress_events_with_events(self, mock_storage_class):
        """Test recover_in_progress_events with events to recover."""
        # Create test events
        test_events = [
            self.create_test_event_record(RECORD_TYPE_REV_REG_DEF_CREATE_EVENT, "corr_1"),
            self.create_test_event_record(RECORD_TYPE_REV_LIST_CREATE_EVENT, "corr_2"),
        ]

        mock_storage = AsyncMock()
        mock_storage.get_in_progress_events.return_value = test_events
        mock_storage_class.return_value = mock_storage

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            with patch.object(
                self.manager, "_recover_single_event"
            ) as mock_recover_single:
                mock_recover_single.return_value = None

                result = await self.manager.recover_in_progress_events()

                assert result == 2
                assert mock_recover_single.call_count == 2
                mock_recover_single.assert_any_call(test_events[0])
                mock_recover_single.assert_any_call(test_events[1])

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.EventStorageManager"
    )
    async def test_recover_in_progress_events_with_errors(self, mock_storage_class):
        """Test recover_in_progress_events with some recovery errors."""
        test_events = [
            self.create_test_event_record(RECORD_TYPE_REV_REG_DEF_CREATE_EVENT, "corr_1"),
            self.create_test_event_record(RECORD_TYPE_REV_LIST_CREATE_EVENT, "corr_2"),
            self.create_test_event_record(RECORD_TYPE_REV_REG_ACTIVATION_EVENT, "corr_3"),
        ]

        mock_storage = AsyncMock()
        mock_storage.get_in_progress_events.return_value = test_events
        mock_storage_class.return_value = mock_storage

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            with patch.object(
                self.manager, "_recover_single_event"
            ) as mock_recover_single:
                # First event succeeds, second fails, third succeeds
                mock_recover_single.side_effect = [
                    None,
                    Exception("Recovery failed"),
                    None,
                ]

                result = await self.manager.recover_in_progress_events()

                # Should return 2 (successful recoveries)
                assert result == 2
                assert mock_recover_single.call_count == 3

    async def test_recover_single_event_rev_reg_def_create(self):
        """Test _recover_single_event for REV_REG_DEF_CREATE_EVENT."""
        event_data = {
            "issuer_id": "test_issuer",
            "cred_def_id": "test_cred_def",
            "registry_type": "CL_ACCUM",
            "tag": "test_tag",
            "max_cred_num": 100,
            "options": {"test": "option"},
        }

        event_record = self.create_test_event_record(
            RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            "test_corr_id",
            event_data,
            {"recovery_option": "test"},
        )

        with patch.object(
            self.manager, "_recover_rev_reg_def_create_event"
        ) as mock_recover:
            await self.manager._recover_single_event(event_record)
            mock_recover.assert_called_once()

    async def test_recover_single_event_rev_reg_def_store(self):
        """Test _recover_single_event for REV_REG_DEF_STORE_EVENT."""
        event_data = {"test": "data"}
        event_record = self.create_test_event_record(
            RECORD_TYPE_REV_REG_DEF_STORE_EVENT, "test_corr_id", event_data
        )

        with patch.object(
            self.manager, "_recover_rev_reg_def_store_event"
        ) as mock_recover:
            await self.manager._recover_single_event(event_record)
            mock_recover.assert_called_once()

    async def test_recover_single_event_rev_list_create(self):
        """Test _recover_single_event for REV_LIST_CREATE_EVENT."""
        event_data = {"test": "data"}
        event_record = self.create_test_event_record(
            RECORD_TYPE_REV_LIST_CREATE_EVENT, "test_corr_id", event_data
        )

        with patch.object(self.manager, "_recover_rev_list_create_event") as mock_recover:
            await self.manager._recover_single_event(event_record)
            mock_recover.assert_called_once()

    async def test_recover_single_event_rev_list_store(self):
        """Test _recover_single_event for REV_LIST_STORE_EVENT."""
        event_data = {"test": "data"}
        event_record = self.create_test_event_record(
            RECORD_TYPE_REV_LIST_STORE_EVENT, "test_corr_id", event_data
        )

        with patch.object(self.manager, "_recover_rev_list_store_event") as mock_recover:
            await self.manager._recover_single_event(event_record)
            mock_recover.assert_called_once()

    async def test_recover_single_event_rev_reg_activation(self):
        """Test _recover_single_event for REV_REG_ACTIVATION_EVENT."""
        event_data = {"test": "data"}
        event_record = self.create_test_event_record(
            RECORD_TYPE_REV_REG_ACTIVATION_EVENT, "test_corr_id", event_data
        )

        with patch.object(
            self.manager, "_recover_rev_reg_activation_event"
        ) as mock_recover:
            await self.manager._recover_single_event(event_record)
            mock_recover.assert_called_once()

    async def test_recover_single_event_rev_reg_full_handling(self):
        """Test _recover_single_event for REV_REG_FULL_HANDLING_EVENT."""
        event_data = {"test": "data"}
        event_record = self.create_test_event_record(
            RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT, "test_corr_id", event_data
        )

        with patch.object(
            self.manager, "_recover_rev_reg_full_handling_event"
        ) as mock_recover:
            await self.manager._recover_single_event(event_record)
            mock_recover.assert_called_once()

    async def test_recover_single_event_unknown_type(self):
        """Test _recover_single_event with unknown event type."""
        event_data = {"test": "data"}
        event_record = self.create_test_event_record(
            "unknown_event_type", "test_corr_id", event_data
        )

        # Should not raise exception, just log warning
        await self.manager._recover_single_event(event_record)

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.deserialize_event_payload"
    )
    async def test_recover_rev_reg_def_create_event(self, mock_deserialize):
        """Test _recover_rev_reg_def_create_event."""
        # Mock the deserialized payload
        mock_payload = MagicMock()
        mock_payload.issuer_id = "test_issuer"
        mock_payload.cred_def_id = "test_cred_def"
        mock_payload.registry_type = "CL_ACCUM"
        mock_payload.tag = "test_tag"
        mock_payload.max_cred_num = 100
        mock_payload.options = {"original": "option"}
        mock_deserialize.return_value = mock_payload

        event_data = {"test": "data"}
        options = {"recovery": True, "correlation_id": "test_corr_id"}

        with patch(
            "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevRegDefCreateRequestedPayload"
        ) as mock_payload_class:
            mock_new_payload = MagicMock()
            mock_payload_class.return_value = mock_new_payload

            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevRegDefCreateRequestedEvent"
            ) as mock_event_class:
                mock_event = MagicMock()
                mock_event_class.return_value = mock_event

                self.event_bus.notify = AsyncMock()

                await self.manager._recover_rev_reg_def_create_event(event_data, options)

                # Verify payload creation with merged options
                expected_options = {
                    "original": "option",
                    "recovery": True,
                    "correlation_id": "test_corr_id",
                }
                mock_payload_class.assert_called_once_with(
                    issuer_id="test_issuer",
                    cred_def_id="test_cred_def",
                    registry_type="CL_ACCUM",
                    tag="test_tag",
                    max_cred_num=100,
                    options=expected_options,
                )

                # Verify event creation and notification
                mock_event_class.assert_called_once_with(mock_new_payload)
                self.event_bus.notify.assert_called_once_with(self.profile, mock_event)

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.deserialize_event_payload"
    )
    async def test_recover_rev_reg_def_store_event(self, mock_deserialize):
        """Test _recover_rev_reg_def_store_event."""
        mock_payload = MagicMock()
        mock_payload.rev_reg_def = "test_rev_reg_def"
        mock_payload.rev_reg_def_result = "test_result"
        mock_payload.options = {"original": "option"}
        mock_deserialize.return_value = mock_payload

        event_data = {"test": "data"}
        options = {"recovery": True}

        with patch(
            "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevRegDefStoreRequestedPayload"
        ) as mock_payload_class:
            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevRegDefStoreRequestedEvent"
            ):
                self.event_bus.notify = AsyncMock()

                await self.manager._recover_rev_reg_def_store_event(event_data, options)

                expected_options = {"original": "option", "recovery": True}
                mock_payload_class.assert_called_once_with(
                    rev_reg_def="test_rev_reg_def",
                    rev_reg_def_result="test_result",
                    options=expected_options,
                )

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.deserialize_event_payload"
    )
    async def test_recover_rev_list_create_event(self, mock_deserialize):
        """Test _recover_rev_list_create_event."""
        mock_payload = MagicMock()
        mock_payload.rev_reg_def_id = "test_rev_reg_def_id"
        mock_payload.options = {"original": "option"}
        mock_deserialize.return_value = mock_payload

        event_data = {"test": "data"}
        options = {"recovery": True}

        with patch(
            "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevListCreateRequestedPayload"
        ) as mock_payload_class:
            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevListCreateRequestedEvent"
            ):
                self.event_bus.notify = AsyncMock()

                await self.manager._recover_rev_list_create_event(event_data, options)

                expected_options = {"original": "option", "recovery": True}
                mock_payload_class.assert_called_once_with(
                    rev_reg_def_id="test_rev_reg_def_id",
                    options=expected_options,
                )

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.deserialize_event_payload"
    )
    async def test_recover_rev_list_store_event(self, mock_deserialize):
        """Test _recover_rev_list_store_event."""
        mock_payload = MagicMock()
        mock_payload.rev_reg_def_id = "test_rev_reg_def_id"
        mock_payload.result = "test_result"
        mock_payload.options = {"original": "option"}
        mock_deserialize.return_value = mock_payload

        event_data = {"test": "data"}
        options = {"recovery": True}

        with patch(
            "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevListStoreRequestedPayload"
        ) as mock_payload_class:
            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevListStoreRequestedEvent"
            ):
                self.event_bus.notify = AsyncMock()

                await self.manager._recover_rev_list_store_event(event_data, options)

                expected_options = {"original": "option", "recovery": True}
                mock_payload_class.assert_called_once_with(
                    rev_reg_def_id="test_rev_reg_def_id",
                    result="test_result",
                    options=expected_options,
                )

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.deserialize_event_payload"
    )
    async def test_recover_rev_reg_activation_event(self, mock_deserialize):
        """Test _recover_rev_reg_activation_event."""
        mock_payload = MagicMock()
        mock_payload.rev_reg_def_id = "test_rev_reg_def_id"
        mock_payload.options = {"original": "option"}
        mock_deserialize.return_value = mock_payload

        event_data = {"test": "data"}
        options = {"recovery": True}

        with patch(
            "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevRegActivationRequestedPayload"
        ) as mock_payload_class:
            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevRegActivationRequestedEvent"
            ):
                self.event_bus.notify = AsyncMock()

                await self.manager._recover_rev_reg_activation_event(event_data, options)

                expected_options = {"original": "option", "recovery": True}
                mock_payload_class.assert_called_once_with(
                    rev_reg_def_id="test_rev_reg_def_id",
                    options=expected_options,
                )

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.deserialize_event_payload"
    )
    async def test_recover_rev_reg_full_handling_event(self, mock_deserialize):
        """Test _recover_rev_reg_full_handling_event."""
        mock_payload = MagicMock()
        mock_payload.rev_reg_def_id = "test_rev_reg_def_id"
        mock_payload.cred_def_id = "test_cred_def_id"
        mock_payload.options = {"original": "option"}
        mock_deserialize.return_value = mock_payload

        event_data = {"test": "data"}
        options = {"recovery": True}

        with patch(
            "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevRegFullDetectedPayload"
        ) as mock_payload_class:
            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevRegFullDetectedEvent"
            ):
                self.event_bus.notify = AsyncMock()

                await self.manager._recover_rev_reg_full_handling_event(
                    event_data, options
                )

                expected_options = {"original": "option", "recovery": True}
                mock_payload_class.assert_called_once_with(
                    rev_reg_def_id="test_rev_reg_def_id",
                    cred_def_id="test_cred_def_id",
                    options=expected_options,
                )

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.EventStorageManager"
    )
    async def test_cleanup_old_events(self, mock_storage_class):
        """Test cleanup_old_events method."""
        mock_storage = AsyncMock()
        mock_storage.cleanup_completed_events.return_value = 5
        mock_storage_class.return_value = mock_storage

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            result = await self.manager.cleanup_old_events(max_age_hours=48)

            assert result == 5
            mock_storage.cleanup_completed_events.assert_called_once_with(
                max_age_hours=48
            )

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.EventStorageManager"
    )
    async def test_cleanup_old_events_default_age(self, mock_storage_class):
        """Test cleanup_old_events with default max_age_hours."""
        mock_storage = AsyncMock()
        mock_storage.cleanup_completed_events.return_value = 3
        mock_storage_class.return_value = mock_storage

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            result = await self.manager.cleanup_old_events()

            assert result == 3
            mock_storage.cleanup_completed_events.assert_called_once_with(
                max_age_hours=24
            )

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.EventStorageManager"
    )
    async def test_get_recovery_status(self, mock_storage_class):
        """Test get_recovery_status method."""
        # Mock in-progress events
        in_progress_events = [
            {"event_type": RECORD_TYPE_REV_REG_DEF_CREATE_EVENT},
            {"event_type": RECORD_TYPE_REV_REG_DEF_CREATE_EVENT},
            {"event_type": RECORD_TYPE_REV_LIST_CREATE_EVENT},
        ]

        # Mock failed events
        failed_events = [
            {"event_type": RECORD_TYPE_REV_REG_DEF_STORE_EVENT},
            {"event_type": RECORD_TYPE_REV_LIST_CREATE_EVENT},
        ]

        mock_storage = AsyncMock()
        mock_storage.get_in_progress_events.return_value = in_progress_events
        mock_storage.get_failed_events.return_value = failed_events
        mock_storage_class.return_value = mock_storage

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            result = await self.manager.get_recovery_status()

            expected = {
                "in_progress_events": 3,
                "failed_events": 2,
                "events_by_type": {
                    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT: 2,
                    RECORD_TYPE_REV_LIST_CREATE_EVENT: 1,
                },
                "failed_events_by_type": {
                    RECORD_TYPE_REV_REG_DEF_STORE_EVENT: 1,
                    RECORD_TYPE_REV_LIST_CREATE_EVENT: 1,
                },
            }

            assert result == expected

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.EventStorageManager"
    )
    async def test_get_recovery_status_no_events(self, mock_storage_class):
        """Test get_recovery_status when no events exist."""
        mock_storage = AsyncMock()
        mock_storage.get_in_progress_events.return_value = []
        mock_storage.get_failed_events.return_value = []
        mock_storage_class.return_value = mock_storage

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            result = await self.manager.get_recovery_status()

            expected = {
                "in_progress_events": 0,
                "failed_events": 0,
                "events_by_type": {},
                "failed_events_by_type": {},
            }

            assert result == expected


@pytest.mark.anoncreds
class TestRecoverRevocationEventsFunction(IsolatedAsyncioTestCase):
    """Test recover_revocation_events convenience function."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.profile = await create_test_profile()
        self.event_bus = MagicMock(spec=EventBus)

    async def asyncTearDown(self):
        """Clean up test fixtures."""
        await self.profile.close()

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.EventRecoveryManager"
    )
    async def test_recover_revocation_events(self, mock_manager_class):
        """Test recover_revocation_events convenience function."""
        mock_manager = AsyncMock()
        mock_manager.recover_in_progress_events.return_value = 7
        mock_manager_class.return_value = mock_manager

        result = await recover_revocation_events(self.profile, self.event_bus)

        assert result == 7
        mock_manager_class.assert_called_once_with(self.profile, self.event_bus)
        mock_manager.recover_in_progress_events.assert_called_once()


@pytest.mark.anoncreds
class TestEventRecoveryIntegration(IsolatedAsyncioTestCase):
    """Integration tests for event recovery functionality."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.profile = await create_test_profile()
        self.event_bus = MagicMock(spec=EventBus)
        self.manager = EventRecoveryManager(self.profile, self.event_bus)

    async def asyncTearDown(self):
        """Clean up test fixtures."""
        await self.profile.close()

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.EventStorageManager"
    )
    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.deserialize_event_payload"
    )
    async def test_end_to_end_recovery_flow(self, mock_deserialize, mock_storage_class):
        """Test complete recovery flow from storage to event emission."""
        # Setup test event
        event_data = {
            "issuer_id": "test_issuer",
            "cred_def_id": "test_cred_def",
            "registry_type": "CL_ACCUM",
            "tag": "test_tag",
            "max_cred_num": 100,
            "options": {"test": "option"},
        }

        test_event = {
            "event_type": RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            "correlation_id": "test_corr_id",
            "event_data": event_data,
            "options": {"recovery_test": True},
        }

        # Mock storage
        mock_storage = AsyncMock()
        mock_storage.get_in_progress_events.return_value = [test_event]
        mock_storage_class.return_value = mock_storage

        # Mock payload deserialization
        mock_payload = MagicMock()
        mock_payload.issuer_id = "test_issuer"
        mock_payload.cred_def_id = "test_cred_def"
        mock_payload.registry_type = "CL_ACCUM"
        mock_payload.tag = "test_tag"
        mock_payload.max_cred_num = 100
        mock_payload.options = {"test": "option"}
        mock_deserialize.return_value = mock_payload

        # Mock event bus
        self.event_bus.notify = AsyncMock()

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevRegDefCreateRequestedPayload"
            ) as mock_payload_class:
                with patch(
                    "acapy_agent.anoncreds.revocation.auto_recovery.event_recovery.RevRegDefCreateRequestedEvent"
                ) as mock_event_class:
                    mock_new_payload = MagicMock()
                    mock_payload_class.return_value = mock_new_payload
                    mock_event = MagicMock()
                    mock_event_class.return_value = mock_event

                    result = await self.manager.recover_in_progress_events()

                    # Verify recovery was successful
                    assert result == 1

                    # Verify event was re-emitted with recovery context
                    self.event_bus.notify.assert_called_once_with(
                        self.profile, mock_event
                    )

                    # Verify payload had recovery options merged
                    call_args = mock_payload_class.call_args
                    assert call_args[1]["options"]["test"] == "option"
                    assert call_args[1]["options"]["recovery"] is True
                    assert call_args[1]["options"]["correlation_id"] == "test_corr_id"
