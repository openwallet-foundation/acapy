"""Tests for credential definition creation with wait_for_revocation_setup options."""

import json
from unittest import IsolatedAsyncioTestCase

import pytest

from ....tests import mock
from ....utils.testing import create_test_profile
from ...issuer import AnonCredsIssuer
from ...models.credential_definition import CredDef
from ..revocation import AnonCredsRevocation
from ..revocation_setup import DefaultRevocationSetup


@pytest.mark.anoncreds
class TestAnonCredsIssuerWaitForRevocation(IsolatedAsyncioTestCase):
    """Tests for wait_for_revocation_setup functionality."""

    async def asyncSetUp(self) -> None:
        """Set up test environment."""
        self.profile = await create_test_profile(
            settings={"wallet.type": "askar-anoncreds"},
        )
        self.issuer = AnonCredsIssuer(self.profile)

    @mock.patch.object(AnonCredsIssuer, "notify")
    async def test_finish_cred_def_passes_options(self, mock_notify):
        """Test finish_cred_def method passes options correctly to the event."""
        # Mock transaction and entry data
        mock_entry = mock.MagicMock()
        mock_entry.value = json.dumps(
            {"issuer_id": "issuer-id", "schema_id": "schema-id"}
        )
        mock_entry.tags = {"support_revocation": "True", "max_cred_num": "1000"}

        self.profile.transaction = mock.Mock(
            return_value=mock.MagicMock(
                commit=mock.CoroutineMock(),
            )
        )

        with mock.patch.object(
            self.issuer, "_finish_registration", return_value=mock_entry
        ):
            with mock.patch.object(CredDef, "from_json") as mock_from_json:
                mock_cred_def = mock.MagicMock()
                mock_cred_def.schema_id = "schema-id"
                mock_cred_def.issuer_id = "issuer-id"
                mock_from_json.return_value = mock_cred_def

                await self.issuer.finish_cred_def(
                    job_id="job-id",
                    cred_def_id="cred-def-id",
                    options={"wait_for_revocation_setup": True},
                )

                # Should notify with correct parameters including options
                mock_notify.assert_called_once()
                call_args = mock_notify.call_args[0][0]  # Get the event passed to notify
                assert call_args.payload.cred_def_id == "cred-def-id"
                assert call_args.payload.support_revocation is True
                assert call_args.payload.options["wait_for_revocation_setup"] is True

    async def test_event_handler_respects_wait_option(self):
        """Test that the event handler respects the wait_for_revocation_setup option.

        This is a basic integration test to verify the event handler behavior.
        More comprehensive tests should be added to the revocation setup module.
        """
        # Create event handler
        setup_manager = DefaultRevocationSetup()

        # Create mock event with wait_for_revocation_setup=False
        mock_payload = mock.MagicMock()
        mock_payload.support_revocation = True
        mock_payload.cred_def_id = "test-cred-def-id"
        mock_payload.issuer_id = "test-issuer-id"
        mock_payload.max_cred_num = 1000
        mock_payload.options = {"wait_for_revocation_setup": False}

        event = mock.MagicMock()
        event.payload = mock_payload

        # Mock the AnonCredsRevocation class
        with mock.patch(
            "acapy_agent.anoncreds.revocation.revocation_setup.AnonCredsRevocation"
        ) as mock_revocation_class:
            mock_revocation = mock_revocation_class.return_value
            mock_revocation.emit_create_revocation_registry_definition_event = (
                mock.CoroutineMock()
            )
            mock_revocation.wait_for_active_revocation_registry = mock.CoroutineMock()

            # Call the event handler
            await setup_manager.on_cred_def(self.profile, event)

            # Should create registries but not wait
            mock_revocation.emit_create_revocation_registry_definition_event.assert_called_once()

            mock_revocation.wait_for_active_revocation_registry.assert_not_called()

    async def test_event_handler_waits_when_configured(self):
        """Test that the event handler waits when wait_for_revocation_setup=True."""
        # Create event handler
        setup_manager = DefaultRevocationSetup()

        # Create mock event with wait_for_revocation_setup=True
        mock_payload = mock.MagicMock()
        mock_payload.support_revocation = True
        mock_payload.cred_def_id = "test-cred-def-id"
        mock_payload.issuer_id = "test-issuer-id"
        mock_payload.max_cred_num = 1000
        mock_payload.options = {"wait_for_revocation_setup": True}

        event = mock.MagicMock()
        event.payload = mock_payload

        # Mock the AnonCredsRevocation class
        with mock.patch(
            "acapy_agent.anoncreds.revocation.revocation_setup.AnonCredsRevocation"
        ) as mock_revocation_class:
            mock_revocation = mock_revocation_class.return_value
            mock_revocation.emit_create_revocation_registry_definition_event = (
                mock.CoroutineMock()
            )
            mock_revocation.wait_for_active_revocation_registry = mock.CoroutineMock()

            # Call the event handler
            await setup_manager.on_cred_def(self.profile, event)

            # Should create registries AND wait
            mock_revocation.emit_create_revocation_registry_definition_event.assert_called_once()
            mock_revocation.wait_for_active_revocation_registry.assert_called_once_with(
                "test-cred-def-id"
            )


class TestAnonCredsRevocationWaitMethod(IsolatedAsyncioTestCase):
    """Test AnonCredsRevocation.wait_for_active_revocation_registry method."""

    async def asyncSetUp(self):
        """Set up test environment."""
        self.profile = await create_test_profile(
            settings={"wallet.type": "askar-anoncreds"}
        )
        self.revocation = AnonCredsRevocation(self.profile)
        self.cred_def_id = "test-cred-def-id"

    async def test_immediate_success_registry_already_active(self):
        """Test immediate success when registry is already active."""
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the session and database query
            mock_session_context = mock.MagicMock()
            mock_session = mock.MagicMock()
            mock_session.handle.fetch_all = mock.CoroutineMock(
                return_value=[{"id": "reg1"}]  # 1 active registry
            )
            mock_session_context.__aenter__ = mock.CoroutineMock(
                return_value=mock_session
            )
            mock_session_context.__aexit__ = mock.CoroutineMock(return_value=None)

            with mock.patch.object(
                self.profile, "session", return_value=mock_session_context
            ):
                # Should complete immediately without timeout
                await self.revocation.wait_for_active_revocation_registry(
                    self.cred_def_id
                )

                # Should only query once
                mock_session.handle.fetch_all.assert_called_once_with(
                    "revocation_reg_def",
                    {"cred_def_id": self.cred_def_id, "active": "true"},
                )
                # Should not need to sleep
                mock_sleep.assert_not_called()

    async def test_success_after_polling(self):
        """Test successful completion after some polling iterations."""
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the session and database query
            mock_session_context = mock.MagicMock()
            mock_session = mock.MagicMock()
            # First 2 calls return empty, 3rd call returns 1 active registry
            mock_session.handle.fetch_all = mock.CoroutineMock(
                side_effect=[[], [], [{"id": "reg1"}]]
            )
            mock_session_context.__aenter__ = mock.CoroutineMock(
                return_value=mock_session
            )
            mock_session_context.__aexit__ = mock.CoroutineMock(return_value=None)

            with mock.patch.object(
                self.profile, "session", return_value=mock_session_context
            ):
                await self.revocation.wait_for_active_revocation_registry(
                    self.cred_def_id
                )

                # Should have queried 3 times
                assert mock_session.handle.fetch_all.call_count == 3
                # Should have slept twice (after 1st and 2nd empty results)
                assert mock_sleep.call_count == 2
                mock_sleep.assert_called_with(0.5)

    async def test_timeout_no_active_registries(self):
        """Test timeout when no registries become active."""
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the session and database query
            mock_session_context = mock.MagicMock()
            mock_session = mock.MagicMock()
            mock_session.handle.fetch_all = mock.CoroutineMock(
                return_value=[]  # No active registries
            )
            mock_session_context.__aenter__ = mock.CoroutineMock(
                return_value=mock_session
            )
            mock_session_context.__aexit__ = mock.CoroutineMock(return_value=None)

            # Set a very short timeout for testing
            with mock.patch(
                "acapy_agent.anoncreds.revocation.revocation.REVOCATION_REGISTRY_CREATION_TIMEOUT",
                1.0,
            ):
                with mock.patch.object(
                    self.profile, "session", return_value=mock_session_context
                ):
                    with self.assertRaises(TimeoutError) as exc_context:
                        await self.revocation.wait_for_active_revocation_registry(
                            self.cred_def_id
                        )

                    # Check error message content
                    error_message = str(exc_context.exception)
                    assert (
                        "Timeout waiting for revocation setup completion" in error_message
                    )
                    assert self.cred_def_id in error_message
                    assert "Expected 1 revocation registries" in error_message
                    assert "still be in progress in the background" in error_message

                    # Should have polled multiple times (1.0s timeout / 0.5s interval = 2 iterations)
                    assert mock_session.handle.fetch_all.call_count == 2

    async def test_polling_with_transient_errors_then_success(self):
        """Test that polling continues despite transient database errors."""
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the session and database query
            mock_session_context = mock.MagicMock()
            mock_session = mock.MagicMock()
            # Simulate: error, error, success
            mock_session.handle.fetch_all = mock.CoroutineMock(
                side_effect=[
                    Exception("Database connection error"),
                    Exception("Temporary network issue"),
                    [{"id": "reg1"}],  # Success on 3rd attempt
                ]
            )
            mock_session_context.__aenter__ = mock.CoroutineMock(
                return_value=mock_session
            )
            mock_session_context.__aexit__ = mock.CoroutineMock(return_value=None)

            with mock.patch.object(
                self.profile, "session", return_value=mock_session_context
            ):
                await self.revocation.wait_for_active_revocation_registry(
                    self.cred_def_id
                )

                # Should have retried despite errors
                assert mock_session.handle.fetch_all.call_count == 3
                # Should have slept after each error
                assert mock_sleep.call_count == 2

    async def test_multiple_active_registries(self):
        """Test success when multiple registries are active (more than expected)."""
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the session and database query
            mock_session_context = mock.MagicMock()
            mock_session = mock.MagicMock()
            mock_session.handle.fetch_all = mock.CoroutineMock(
                return_value=[
                    {"id": "reg1"},
                    {"id": "reg2"},
                    {"id": "reg3"},
                ]  # 3 active registries
            )
            mock_session_context.__aenter__ = mock.CoroutineMock(
                return_value=mock_session
            )
            mock_session_context.__aexit__ = mock.CoroutineMock(return_value=None)

            with mock.patch.object(
                self.profile, "session", return_value=mock_session_context
            ):
                await self.revocation.wait_for_active_revocation_registry(
                    self.cred_def_id
                )

                # Should complete immediately since we have >= 1
                mock_session.handle.fetch_all.assert_called_once()
                mock_sleep.assert_not_called()

    async def test_custom_timeout_value(self):
        """Test behavior with custom timeout configuration."""
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the session and database query
            mock_session_context = mock.MagicMock()
            mock_session = mock.MagicMock()
            mock_session.handle.fetch_all = mock.CoroutineMock(
                return_value=[]  # No active registries
            )
            mock_session_context.__aenter__ = mock.CoroutineMock(
                return_value=mock_session
            )
            mock_session_context.__aexit__ = mock.CoroutineMock(return_value=None)

            # Set a custom timeout
            custom_timeout = 5.0
            with mock.patch(
                "acapy_agent.anoncreds.revocation.revocation.REVOCATION_REGISTRY_CREATION_TIMEOUT",
                custom_timeout,
            ):
                with mock.patch.object(
                    self.profile, "session", return_value=mock_session_context
                ):
                    with self.assertRaises(TimeoutError):
                        await self.revocation.wait_for_active_revocation_registry(
                            self.cred_def_id
                        )

                    # Should have polled based on custom timeout (5.0s / 0.5s = 10 iterations)
                    expected_iterations = int(custom_timeout / 0.5)
                    assert mock_session.handle.fetch_all.call_count == expected_iterations

    async def test_logging_behavior(self):
        """Test that appropriate log messages are generated."""
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None

            # Mock the session and database query
            mock_session_context = mock.MagicMock()
            mock_session = mock.MagicMock()
            # First call empty, second call has 1 registry
            mock_session.handle.fetch_all = mock.CoroutineMock(
                side_effect=[[], [{"id": "reg1"}]]
            )
            mock_session_context.__aenter__ = mock.CoroutineMock(
                return_value=mock_session
            )
            mock_session_context.__aexit__ = mock.CoroutineMock(return_value=None)

            with mock.patch(
                "acapy_agent.anoncreds.revocation.revocation.LOGGER"
            ) as mock_logger:
                with mock.patch.object(
                    self.profile, "session", return_value=mock_session_context
                ):
                    await self.revocation.wait_for_active_revocation_registry(
                        self.cred_def_id
                    )

                    # Should log debug message at start
                    mock_logger.debug.assert_any_call(
                        "Waiting for revocation setup completion for cred_def_id: %s",
                        self.cred_def_id,
                    )

                    # Should log progress updates
                    mock_logger.debug.assert_any_call(
                        "Revocation setup progress for %s: %d/%d registries active",
                        self.cred_def_id,
                        0,  # First iteration
                        1,  # Expected count
                    )

                    # Should log completion
                    mock_logger.info.assert_called_once_with(
                        "Revocation setup completed for cred_def_id: %s "
                        "(%d registries active)",
                        self.cred_def_id,
                        1,
                    )

    async def test_session_context_manager_usage(self):
        """Test that database session context manager is properly used."""
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None

            # Mock the session and database query
            mock_session_context = mock.MagicMock()
            mock_session = mock.MagicMock()
            mock_session.handle.fetch_all = mock.CoroutineMock(
                return_value=[{"id": "reg1"}]  # Success immediately
            )
            mock_session_context.__aenter__ = mock.CoroutineMock(
                return_value=mock_session
            )
            mock_session_context.__aexit__ = mock.CoroutineMock(return_value=None)

            with mock.patch.object(
                self.profile, "session", return_value=mock_session_context
            ):
                await self.revocation.wait_for_active_revocation_registry(
                    self.cred_def_id
                )

                # Should have used the session context manager
                self.profile.session.assert_called_once()
                mock_session_context.__aenter__.assert_called_once()
                mock_session_context.__aexit__.assert_called_once()

                # Query should have been called with correct parameters
                mock_session.handle.fetch_all.assert_called_once_with(
                    "revocation_reg_def",
                    {"cred_def_id": self.cred_def_id, "active": "true"},
                )
