"""Tests for wait_for_active_revocation_registry utility method."""

from unittest import IsolatedAsyncioTestCase

from ...revocation.models.issuer_rev_reg_record import IssuerRevRegRecord
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import wait_for_active_registry as test_module


class TestWaitForActiveRevocationRegistry(IsolatedAsyncioTestCase):
    """Test wait_for_active_revocation_registry utility."""

    async def asyncSetUp(self):
        """Set up test environment."""
        self.profile = await create_test_profile()
        self.cred_def_id = "test-cred-def-id"

    async def test_immediate_success_registry_already_active(self):
        """Test immediate success when registry is already active."""
        # Mock an active registry record
        mock_registry = mock.MagicMock()
        mock_registry.state = IssuerRevRegRecord.STATE_ACTIVE

        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            with mock.patch.object(
                IssuerRevRegRecord, "query_by_cred_def_id"
            ) as mock_query:
                mock_query.return_value = [mock_registry, mock_registry]  # 2 active

                # Should complete immediately without timeout
                await test_module.wait_for_active_revocation_registry(
                    self.profile, self.cred_def_id
                )

                # Should only query once
                mock_query.assert_called_once_with(
                    mock.ANY,  # session
                    self.cred_def_id,
                    IssuerRevRegRecord.STATE_ACTIVE,
                )
                # Should not need to sleep
                mock_sleep.assert_not_called()

    async def test_success_after_polling(self):
        """Test successful completion after some polling iterations."""
        mock_registry = mock.MagicMock()
        mock_registry.state = IssuerRevRegRecord.STATE_ACTIVE

        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            with mock.patch.object(
                IssuerRevRegRecord, "query_by_cred_def_id"
            ) as mock_query:
                # First call return empty, second call returns 1 active registry, 3rd call returns 2 active registries
                mock_query.side_effect = [
                    [],
                    [mock_registry],
                    [mock_registry, mock_registry],
                ]

                await test_module.wait_for_active_revocation_registry(
                    self.profile, self.cred_def_id
                )

                # Should have queried 3 times
                assert mock_query.call_count == 3
                # Should have slept twice (after 1st and 2nd empty results)
                assert mock_sleep.call_count == 2
                mock_sleep.assert_called_with(0.5)

    async def test_timeout_no_active_registries(self):
        """Test timeout when no registries become active."""
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            with mock.patch.object(
                IssuerRevRegRecord, "query_by_cred_def_id"
            ) as mock_query:
                mock_query.return_value = []  # No active registries

                with self.assertRaises(TimeoutError) as exc_context:
                    await test_module.wait_for_active_revocation_registry(
                        self.profile, self.cred_def_id
                    )

                # Check error message content
                error_message = str(exc_context.exception)
                assert "Timeout waiting for revocation setup completion" in error_message
                assert self.cred_def_id in error_message
                assert "Expected 2 active revocation registries" in error_message
                assert "still be in progress in the background" in error_message

    async def test_polling_with_transient_errors_then_success(self):
        """Test that polling continues despite transient database errors."""
        mock_registry = mock.MagicMock()
        mock_registry.state = IssuerRevRegRecord.STATE_ACTIVE

        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            with mock.patch.object(
                IssuerRevRegRecord, "query_by_cred_def_id"
            ) as mock_query:
                # Simulate: error, error, success
                mock_query.side_effect = [
                    Exception("Database connection error"),
                    Exception("Temporary network issue"),
                    [mock_registry, mock_registry],  # Success on 3rd attempt
                ]

                await test_module.wait_for_active_revocation_registry(
                    self.profile, self.cred_def_id
                )

                # Should have retried despite errors
                assert mock_query.call_count == 3
                # Should have slept after each error
                assert mock_sleep.call_count == 2

    async def test_multiple_active_registries(self):
        """Test success when multiple registries are active (more than expected)."""
        mock_registry1 = mock.MagicMock()
        mock_registry2 = mock.MagicMock()
        mock_registry3 = mock.MagicMock()

        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            with mock.patch.object(
                IssuerRevRegRecord, "query_by_cred_def_id"
            ) as mock_query:
                mock_query.return_value = [
                    mock_registry1,
                    mock_registry2,
                    mock_registry3,
                ]  # 3 active registries

                await test_module.wait_for_active_revocation_registry(
                    self.profile, self.cred_def_id
                )

                # Should complete immediately since we have >= 2
                mock_query.assert_called_once()
                mock_sleep.assert_not_called()

    async def test_custom_timeout_value(self):
        """Test behavior with custom timeout configuration."""
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            with mock.patch.object(
                IssuerRevRegRecord, "query_by_cred_def_id"
            ) as mock_query:
                mock_query.return_value = []  # No active registries

                # Set a custom timeout
                custom_timeout = 5.0
                with mock.patch.object(
                    test_module, "REVOCATION_REGISTRY_CREATION_TIMEOUT", custom_timeout
                ):
                    with self.assertRaises(TimeoutError):
                        await test_module.wait_for_active_revocation_registry(
                            self.profile, self.cred_def_id
                        )

                    # Should have polled based on custom timeout (5.0s / 0.5s = 10 iterations)
                    expected_iterations = int(custom_timeout / 0.5)
                    assert mock_query.call_count == expected_iterations
