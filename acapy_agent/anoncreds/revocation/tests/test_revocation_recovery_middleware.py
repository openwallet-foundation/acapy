"""Test the revocation recovery middleware module."""

import asyncio
from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web

from ....admin.request_context import AdminRequestContext
from ....core.event_bus import EventBus
from ....storage.type import RECORD_TYPE_REV_REG_DEF_CREATE_EVENT
from ....utils.testing import create_test_profile
from ..auto_recovery.revocation_recovery_middleware import (
    RevocationRecoveryTracker,
    get_revocation_event_counts,
    recover_profile_events,
    recovery_tracker,
    revocation_recovery_middleware,
)


@pytest.mark.anoncreds
class TestRevocationRecoveryTracker(IsolatedAsyncioTestCase):
    """Test RevocationRecoveryTracker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = RevocationRecoveryTracker()
        self.profile_name = "test_profile"

    def test_initial_state(self):
        """Test tracker initial state."""
        assert not self.tracker.is_recovered(self.profile_name)
        assert not self.tracker.is_recovery_in_progress(self.profile_name)

    def test_mark_recovery_started(self):
        """Test marking recovery as started."""
        self.tracker.mark_recovery_started(self.profile_name)

        assert not self.tracker.is_recovered(self.profile_name)
        assert self.tracker.is_recovery_in_progress(self.profile_name)

    def test_mark_recovery_completed(self):
        """Test marking recovery as completed."""
        # Start recovery first
        self.tracker.mark_recovery_started(self.profile_name)
        assert self.tracker.is_recovery_in_progress(self.profile_name)

        # Complete recovery
        self.tracker.mark_recovery_completed(self.profile_name)

        assert self.tracker.is_recovered(self.profile_name)
        assert not self.tracker.is_recovery_in_progress(self.profile_name)

    def test_mark_recovery_failed(self):
        """Test marking recovery as failed."""
        # Start recovery first
        self.tracker.mark_recovery_started(self.profile_name)
        assert self.tracker.is_recovery_in_progress(self.profile_name)

        # Fail recovery
        self.tracker.mark_recovery_failed(self.profile_name)

        assert not self.tracker.is_recovered(self.profile_name)
        assert not self.tracker.is_recovery_in_progress(self.profile_name)

    def test_multiple_profiles(self):
        """Test tracker with multiple profiles."""
        profile1 = "profile1"
        profile2 = "profile2"

        self.tracker.mark_recovery_started(profile1)
        self.tracker.mark_recovery_completed(profile2)

        assert self.tracker.is_recovery_in_progress(profile1)
        assert not self.tracker.is_recovered(profile1)

        assert not self.tracker.is_recovery_in_progress(profile2)
        assert self.tracker.is_recovered(profile2)


@pytest.mark.anoncreds
class TestGetRevocationEventCounts(IsolatedAsyncioTestCase):
    """Test get_revocation_event_counts function."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.profile = await create_test_profile()

    async def asyncTearDown(self):
        """Clean up test fixtures."""
        await self.profile.close()

    def create_test_event(
        self, correlation_id: str, expiry_timestamp: float = None
    ) -> dict:
        """Create a test event dictionary."""
        return {
            "event_type": RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
            "correlation_id": correlation_id,
            "expiry_timestamp": expiry_timestamp,
        }

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.is_event_expired"
    )
    async def test_no_events(self, mock_is_expired):
        """Test when no events are found."""
        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            # Mock EventStorageManager
            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.EventStorageManager"
            ) as mock_storage_class:
                mock_storage = AsyncMock()
                mock_storage.get_in_progress_events.return_value = []
                mock_storage_class.return_value = mock_storage

                pending_count, recoverable_count = await get_revocation_event_counts(
                    self.profile
                )

                assert pending_count == 0
                assert recoverable_count == 0

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.is_event_expired"
    )
    async def test_events_with_expiry(self, mock_is_expired):
        """Test events with expiry timestamps."""
        # Mock expired and non-expired events
        current_time = datetime.now(timezone.utc).timestamp()
        expired_time = current_time - 3600  # 1 hour ago
        future_time = current_time + 3600  # 1 hour from now

        events = [
            self.create_test_event("expired_1", expired_time),
            self.create_test_event("expired_2", expired_time),
            self.create_test_event("future_1", future_time),
        ]

        # Configure mock to return expired for first two, not expired for third
        mock_is_expired.side_effect = lambda ts: ts == expired_time

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.EventStorageManager"
            ) as mock_storage_class:
                mock_storage = AsyncMock()
                mock_storage.get_in_progress_events.return_value = events
                mock_storage_class.return_value = mock_storage

                pending_count, recoverable_count = await get_revocation_event_counts(
                    self.profile, check_expiry=True
                )

                assert pending_count == 3
                assert recoverable_count == 2

    async def test_events_without_expiry(self):
        """Test events without expiry timestamps."""
        events = [
            self.create_test_event("no_expiry_1"),
            self.create_test_event("no_expiry_2"),
        ]

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.EventStorageManager"
            ) as mock_storage_class:
                mock_storage = AsyncMock()
                mock_storage.get_in_progress_events.return_value = events
                mock_storage_class.return_value = mock_storage

                pending_count, recoverable_count = await get_revocation_event_counts(
                    self.profile, check_expiry=True
                )

                assert pending_count == 2
                assert (
                    recoverable_count == 2
                )  # Events without expiry are considered recoverable

    async def test_check_expiry_false(self):
        """Test when check_expiry is False."""
        events = [
            self.create_test_event("event_1", 123456789),
            self.create_test_event("event_2", 987654321),
        ]

        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.EventStorageManager"
            ) as mock_storage_class:
                mock_storage = AsyncMock()
                mock_storage.get_in_progress_events.return_value = events
                mock_storage_class.return_value = mock_storage

                pending_count, recoverable_count = await get_revocation_event_counts(
                    self.profile, check_expiry=False
                )

                assert pending_count == 2
                assert recoverable_count == 2  # All pending events are recoverable

    async def test_error_handling(self):
        """Test error handling in get_revocation_event_counts."""
        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session_cm.side_effect = Exception("Database error")

            pending_count, recoverable_count = await get_revocation_event_counts(
                self.profile
            )

            assert pending_count == 0
            assert recoverable_count == 0


@pytest.mark.anoncreds
class TestRecoverProfileEvents(IsolatedAsyncioTestCase):
    """Test recover_profile_events function."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.profile = await create_test_profile()
        self.event_bus = MagicMock(spec=EventBus)

    async def asyncTearDown(self):
        """Clean up test fixtures."""
        await self.profile.close()

    async def test_successful_recovery(self):
        """Test successful event recovery."""
        with patch(
            "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.EventRecoveryManager"
        ) as mock_recovery_class:
            mock_recovery = AsyncMock()
            mock_recovery.recover_in_progress_events.return_value = 3
            mock_recovery_class.return_value = mock_recovery

            await recover_profile_events(self.profile, self.event_bus)

            # Verify recovery manager was created with correct parameters
            mock_recovery_class.assert_called_once_with(self.profile, self.event_bus)
            mock_recovery.recover_in_progress_events.assert_called_once()

    async def test_no_events_to_recover(self):
        """Test when no events need recovery."""
        with patch(
            "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.EventRecoveryManager"
        ) as mock_recovery_class:
            mock_recovery = AsyncMock()
            mock_recovery.recover_in_progress_events.return_value = 0
            mock_recovery_class.return_value = mock_recovery

            await recover_profile_events(self.profile, self.event_bus)

            mock_recovery.recover_in_progress_events.assert_called_once()

    async def test_recovery_error(self):
        """Test error handling during recovery."""
        with patch(
            "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.EventRecoveryManager"
        ) as mock_recovery_class:
            mock_recovery = AsyncMock()
            mock_recovery.recover_in_progress_events.side_effect = Exception(
                "Recovery failed"
            )
            mock_recovery_class.return_value = mock_recovery

            with pytest.raises(Exception, match="Recovery failed"):
                await recover_profile_events(self.profile, self.event_bus)


@pytest.mark.anoncreds
class TestRevocationRecoveryMiddleware(IsolatedAsyncioTestCase):
    """Test revocation_recovery_middleware function."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.profile = await create_test_profile()
        self.request = MagicMock(spec=web.BaseRequest)
        self.handler = AsyncMock()
        self.handler.return_value = web.Response(text="OK")

        # Set up request context
        self.context = MagicMock(spec=AdminRequestContext)
        self.context.profile = self.profile
        self.request.__getitem__.return_value = self.context

        # Clear global recovery tracker state before each test
        recovery_tracker.recovered_profiles.clear()
        recovery_tracker.recovery_in_progress.clear()

    async def asyncTearDown(self):
        """Clean up test fixtures."""
        await self.profile.close()

    async def test_skip_paths(self):
        """Test that certain paths are skipped."""
        self.request.rel_url = "/status/ready"

        response = await revocation_recovery_middleware(self.request, self.handler)

        # Handler should be called directly without recovery checks
        self.handler.assert_called_once_with(self.request)
        assert response.text == "OK"

    async def test_no_profile_context(self):
        """Test when no profile context is available."""
        self.request.__getitem__.side_effect = KeyError("context")

        response = await revocation_recovery_middleware(self.request, self.handler)

        # Handler should be called directly
        self.handler.assert_called_once_with(self.request)
        assert response.text == "OK"

    async def test_auto_recovery_disabled(self):
        """Test when auto recovery is disabled."""
        self.request.rel_url = "/test/endpoint"

        # Mock profile settings to disable auto recovery
        with patch.object(self.profile.settings, "get_bool", return_value=False):
            response = await revocation_recovery_middleware(self.request, self.handler)

        # Handler should be called directly
        self.handler.assert_called_once_with(self.request)
        assert response.text == "OK"

    async def test_already_recovered(self):
        """Test when profile is already recovered."""
        self.request.rel_url = "/test/endpoint"
        profile_name = self.profile.name

        # Mark profile as already recovered
        recovery_tracker.mark_recovery_completed(profile_name)

        with patch.object(self.profile.settings, "get_bool", return_value=True):
            response = await revocation_recovery_middleware(self.request, self.handler)

        # Handler should be called directly
        self.handler.assert_called_once_with(self.request)
        assert response.text == "OK"

    async def test_recovery_in_progress(self):
        """Test when recovery is already in progress."""
        self.request.rel_url = "/test/endpoint"
        profile_name = self.profile.name

        # Mark recovery as in progress
        recovery_tracker.mark_recovery_started(profile_name)

        with patch.object(self.profile.settings, "get_bool", return_value=True):
            response = await revocation_recovery_middleware(self.request, self.handler)

        # Handler should be called directly
        self.handler.assert_called_once_with(self.request)
        assert response.text == "OK"

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.get_revocation_event_counts"
    )
    async def test_no_recoverable_events_no_pending(self, mock_get_counts):
        """Test when no recoverable events and no pending events exist."""
        self.request.rel_url = "/test/endpoint"
        profile_name = self.profile.name

        # Mock no events
        mock_get_counts.return_value = (0, 0)  # pending, recoverable

        with patch.object(self.profile.settings, "get_bool", return_value=True):
            await revocation_recovery_middleware(self.request, self.handler)

        # Profile should be marked as recovered
        assert recovery_tracker.is_recovered(profile_name)
        self.handler.assert_called_once_with(self.request)

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.get_revocation_event_counts"
    )
    async def test_no_recoverable_events_with_pending(self, mock_get_counts):
        """Test when no recoverable events but pending events exist."""
        self.request.rel_url = "/test/endpoint"
        profile_name = self.profile.name

        # Mock pending events within delay period
        mock_get_counts.return_value = (5, 0)  # pending, recoverable

        with patch.object(self.profile.settings, "get_bool", return_value=True):
            await revocation_recovery_middleware(self.request, self.handler)

        # Profile should NOT be marked as recovered yet
        assert not recovery_tracker.is_recovered(profile_name)
        self.handler.assert_called_once_with(self.request)

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.get_revocation_event_counts"
    )
    async def test_error_checking_events(self, mock_get_counts):
        """Test error handling when checking for events."""
        self.request.rel_url = "/test/endpoint"

        # Mock error during event count check
        mock_get_counts.side_effect = Exception("Database error")

        with patch.object(self.profile.settings, "get_bool", return_value=True):
            await revocation_recovery_middleware(self.request, self.handler)

        # Should continue with request despite error
        self.handler.assert_called_once_with(self.request)

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.recover_profile_events"
    )
    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.get_revocation_event_counts"
    )
    async def test_successful_recovery(self, mock_get_counts, mock_recover):
        """Test successful recovery process."""
        self.request.rel_url = "/test/endpoint"
        profile_name = self.profile.name

        # Mock recoverable events
        mock_get_counts.return_value = (5, 3)  # pending, recoverable
        mock_recover.return_value = None  # Successful recovery

        # Mock event bus injection
        mock_event_bus = MagicMock(spec=EventBus)
        with patch.object(self.profile, "inject", return_value=mock_event_bus):
            with patch.object(self.profile.settings, "get_bool", return_value=True):
                await revocation_recovery_middleware(self.request, self.handler)

        # Recovery should be performed
        mock_recover.assert_called_once_with(self.profile, mock_event_bus)

        # Profile should be marked as recovered
        assert recovery_tracker.is_recovered(profile_name)

        self.handler.assert_called_once_with(self.request)

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.recover_profile_events"
    )
    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.get_revocation_event_counts"
    )
    async def test_recovery_timeout(self, mock_get_counts, mock_recover):
        """Test recovery timeout handling."""
        self.request.rel_url = "/test/endpoint"
        profile_name = self.profile.name

        # Mock recoverable events and timeout
        mock_get_counts.return_value = (5, 3)  # pending, recoverable
        mock_recover.side_effect = asyncio.TimeoutError("Recovery timed out")

        # Mock event bus injection
        mock_event_bus = MagicMock(spec=EventBus)
        with patch.object(self.profile, "inject", return_value=mock_event_bus):
            with patch.object(self.profile.settings, "get_bool", return_value=True):
                await revocation_recovery_middleware(self.request, self.handler)

        # Profile should be marked as failed (not recovered)
        assert not recovery_tracker.is_recovered(profile_name)
        assert not recovery_tracker.is_recovery_in_progress(profile_name)

        self.handler.assert_called_once_with(self.request)

    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.recover_profile_events"
    )
    @patch(
        "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.get_revocation_event_counts"
    )
    async def test_recovery_general_error(self, mock_get_counts, mock_recover):
        """Test recovery general error handling."""
        self.request.rel_url = "/test/endpoint"
        profile_name = self.profile.name

        # Mock recoverable events and general error
        mock_get_counts.return_value = (5, 3)  # pending, recoverable
        mock_recover.side_effect = Exception("Recovery failed")

        # Mock event bus injection
        mock_event_bus = MagicMock(spec=EventBus)
        with patch.object(self.profile, "inject", return_value=mock_event_bus):
            with patch.object(self.profile.settings, "get_bool", return_value=True):
                await revocation_recovery_middleware(self.request, self.handler)

        # Profile should be marked as failed (not recovered)
        assert not recovery_tracker.is_recovered(profile_name)
        assert not recovery_tracker.is_recovery_in_progress(profile_name)

        self.handler.assert_called_once_with(self.request)


@pytest.mark.anoncreds
class TestMiddlewareIntegration(IsolatedAsyncioTestCase):
    """Integration tests for the middleware with real components."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.profile = await create_test_profile()

        # Clear global recovery tracker state
        recovery_tracker.recovered_profiles.clear()
        recovery_tracker.recovery_in_progress.clear()

    async def asyncTearDown(self):
        """Clean up test fixtures."""
        await self.profile.close()

    async def test_end_to_end_middleware_flow(self):
        """Test complete middleware flow with mocked storage."""
        request = MagicMock(spec=web.BaseRequest)
        request.rel_url = "/test/endpoint"

        # Set up request context
        context = MagicMock(spec=AdminRequestContext)
        context.profile = self.profile
        request.__getitem__.return_value = context

        # Mock handler
        handler = AsyncMock()
        handler.return_value = web.Response(text="OK")

        # Mock the storage layer to return no events
        with patch.object(self.profile, "session") as mock_session_cm:
            mock_session = AsyncMock()
            mock_session_cm.return_value.__aenter__.return_value = mock_session

            with patch(
                "acapy_agent.anoncreds.revocation.auto_recovery.revocation_recovery_middleware.EventStorageManager"
            ) as mock_storage_class:
                mock_storage = AsyncMock()
                mock_storage.get_in_progress_events.return_value = []
                mock_storage_class.return_value = mock_storage

                with patch.object(self.profile.settings, "get_bool", return_value=True):
                    response = await revocation_recovery_middleware(request, handler)

        # Should complete successfully and mark profile as recovered
        assert recovery_tracker.is_recovered(self.profile.name)
        handler.assert_called_once_with(request)
        assert response.text == "OK"
