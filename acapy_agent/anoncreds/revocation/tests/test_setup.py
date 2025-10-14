from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ....storage.type import (
    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
    RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
)
from ....tests import mock
from ....utils.testing import create_test_profile
from ...event_storage import EventStorageManager
from ...events import (
    ErrorInfoPayload,
    RevRegDefCreateFailurePayload,
    RevRegDefCreateRequestedEvent,
    RevRegDefCreateRequestedPayload,
    RevRegDefCreateResponseEvent,
    RevRegDefCreateResponsePayload,
    RevRegDefStoreRequestedEvent,
    RevRegDefStoreRequestedPayload,
    RevRegFullDetectedEvent,
    RevRegFullDetectedPayload,
)
from .. import revocation_setup as test_module
from ..revocation import AnonCredsRevocation


@pytest.mark.anoncreds
class TestAnonCredsRevocationSetup(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile(
            settings={
                "wallet-type": "askar-anoncreds",
                "tails_server_base_url": "http://tails-server.com",
            }
        )
        self.revocation_setup = test_module.DefaultRevocationSetup()

    # Tests for new helper methods
    async def test_setup_request_correlation_new_request(self):
        """Test _setup_request_correlation with new request (no correlation_id)."""
        payload = MagicMock()
        payload.options = {"request_id": "test_request_id", "retry_count": 0}

        with patch.object(EventStorageManager, "store_event_request") as mock_store:
            mock_store.return_value = None

            (
                correlation_id,
                options_with_correlation,
            ) = await self.revocation_setup._setup_request_correlation(
                self.profile, payload, RECORD_TYPE_REV_REG_DEF_CREATE_EVENT
            )

            # The correlation_id should be generated (not mocked, so it will be real)
            assert correlation_id.startswith("CORR_")
            assert options_with_correlation["correlation_id"] == correlation_id
            assert options_with_correlation["request_id"] == "test_request_id"
            mock_store.assert_called_once()

    async def test_setup_request_correlation_retry_request(self):
        """Test _setup_request_correlation with retry request (existing correlation_id)."""
        payload = MagicMock()
        payload.options = {
            "correlation_id": "existing_correlation_id",
            "request_id": "test_request_id",
        }

        with patch.object(EventStorageManager, "store_event_request") as mock_store:
            (
                correlation_id,
                options_with_correlation,
            ) = await self.revocation_setup._setup_request_correlation(
                self.profile, payload, RECORD_TYPE_REV_REG_DEF_CREATE_EVENT
            )

            assert correlation_id == "existing_correlation_id"
            assert options_with_correlation["correlation_id"] == "existing_correlation_id"
            # Should not store event for retry
            mock_store.assert_not_called()

    @patch("asyncio.sleep")
    async def test_handle_response_failure_with_retry(self, mock_sleep):
        """Test _handle_response_failure when error is retryable."""
        payload = MagicMock()
        payload.failure = MagicMock()
        payload.failure.error_info = ErrorInfoPayload(
            error_msg="Test error", should_retry=True, retry_count=1
        )
        payload.failure.cred_def_id = "test_cred_def_id"
        payload.options = {"request_id": "test_request_id"}

        retry_callback = AsyncMock()

        with patch.object(EventStorageManager, "update_event_for_retry") as mock_update:
            result = await self.revocation_setup._handle_response_failure(
                self.profile,
                payload,
                RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                "test_correlation_id",
                "registry_create",
                retry_callback,
            )

            assert result is True  # Retry was attempted
            mock_sleep.assert_called_once()
            mock_update.assert_called_once()
            retry_callback.assert_called_once()

    async def test_handle_response_failure_no_retry(self):
        """Test _handle_response_failure when error is not retryable."""
        payload = MagicMock()
        payload.failure = MagicMock()
        payload.failure.error_info = ErrorInfoPayload(
            error_msg="Test error", should_retry=False, retry_count=3
        )
        payload.failure.cred_def_id = "test_cred_def_id"
        payload.options = {"request_id": "test_request_id"}

        retry_callback = AsyncMock()

        with patch.object(EventStorageManager, "update_event_response") as mock_update:
            with patch.object(
                self.revocation_setup,
                "_notify_issuer_about_failure",
                new_callable=AsyncMock,
            ) as mock_notify:
                result = await self.revocation_setup._handle_response_failure(
                    self.profile,
                    payload,
                    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                    "test_correlation_id",
                    "registry_create",
                    retry_callback,
                )

                assert result is False  # Retry was not attempted
                mock_update.assert_called_once()
                mock_notify.assert_called_once()
                retry_callback.assert_not_called()

    async def test_handle_response_success(self):
        """Test _handle_response_success updates event storage correctly."""
        payload = MagicMock()

        with patch.object(EventStorageManager, "update_event_response") as mock_update:
            await self.revocation_setup._handle_response_success(
                self.profile,
                payload,
                RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                "test_correlation_id",
                "Test success message",
            )

            mock_update.assert_called_once_with(
                event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                correlation_id="test_correlation_id",
                success=True,
                response_data=mock.ANY,
            )

    # Tests for refactored event handler methods
    @patch.object(
        AnonCredsRevocation, "create_and_register_revocation_registry_definition"
    )
    async def test_on_registry_create_requested(self, mock_create_reg):
        """Test on_registry_create_requested uses correlation helper."""
        payload = RevRegDefCreateRequestedPayload(
            issuer_id="test_issuer_id",
            cred_def_id="test_cred_def_id",
            registry_type="CL_ACCUM",
            tag="0",
            max_cred_num=100,
            options={"request_id": "test_request_id"},
        )
        event = RevRegDefCreateRequestedEvent(payload)

        with patch.object(
            self.revocation_setup, "_setup_request_correlation"
        ) as mock_setup:
            mock_setup.return_value = (
                "test_correlation_id",
                {"correlation_id": "test_correlation_id"},
            )

            await self.revocation_setup.on_registry_create_requested(self.profile, event)

            mock_setup.assert_called_once_with(
                self.profile, payload, RECORD_TYPE_REV_REG_DEF_CREATE_EVENT
            )
            mock_create_reg.assert_called_once()

    async def test_on_registry_create_response_success(self):
        """Test on_registry_create_response handles success correctly."""
        rev_reg_def = MagicMock()
        rev_reg_def.id = "test_rev_reg_def_id"

        payload = RevRegDefCreateResponsePayload(
            rev_reg_def=rev_reg_def,
            rev_reg_def_result=MagicMock(),
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=None,
        )
        event = RevRegDefCreateResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_success"
        ) as mock_success:
            with patch.object(
                AnonCredsRevocation, "emit_store_revocation_registry_definition_event"
            ) as mock_emit:
                await self.revocation_setup.on_registry_create_response(
                    self.profile, event
                )

                mock_success.assert_called_once()
                mock_emit.assert_called_once()

    async def test_on_registry_create_response_failure_retryable(self):
        """Test on_registry_create_response handles retryable failure."""
        failure = RevRegDefCreateFailurePayload(
            error_info=ErrorInfoPayload(
                error_msg="Network error", should_retry=True, retry_count=1
            ),
            issuer_id="test_issuer_id",
            cred_def_id="test_cred_def_id",
            registry_type="CL_ACCUM",
            tag="0",
            max_cred_num=100,
        )

        payload = RevRegDefCreateResponsePayload(
            rev_reg_def=None,
            rev_reg_def_result=None,
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=failure,
        )
        event = RevRegDefCreateResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_failure"
        ) as mock_failure:
            mock_failure.return_value = True  # Retry was attempted

            await self.revocation_setup.on_registry_create_response(self.profile, event)

            mock_failure.assert_called_once()
            # Verify the retry callback would emit the retry event
            args, kwargs = mock_failure.call_args
            assert kwargs["failure_type"] == "registry_create"

    async def test_on_registry_create_response_failure_not_retryable(self):
        """Test on_registry_create_response handles non-retryable failure."""
        failure = RevRegDefCreateFailurePayload(
            error_info=ErrorInfoPayload(
                error_msg="Invalid issuer_id", should_retry=False, retry_count=3
            ),
            issuer_id="test_issuer_id",
            cred_def_id="test_cred_def_id",
            registry_type="CL_ACCUM",
            tag="0",
            max_cred_num=100,
        )

        payload = RevRegDefCreateResponsePayload(
            rev_reg_def=None,
            rev_reg_def_result=None,
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=failure,
        )
        event = RevRegDefCreateResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_failure"
        ) as mock_failure:
            mock_failure.return_value = False  # Retry was not attempted

            await self.revocation_setup.on_registry_create_response(self.profile, event)

            mock_failure.assert_called_once()

    @patch.object(
        AnonCredsRevocation, "handle_store_revocation_registry_definition_request"
    )
    async def test_on_registry_store_requested(self, mock_store):
        """Test on_registry_store_requested uses correlation helper."""
        payload = RevRegDefStoreRequestedPayload(
            rev_reg_def=MagicMock(),
            rev_reg_def_result=MagicMock(),
            options={"request_id": "test_request_id"},
        )
        event = RevRegDefStoreRequestedEvent(payload)

        with patch.object(
            self.revocation_setup, "_setup_request_correlation"
        ) as mock_setup:
            mock_setup.return_value = (
                "test_correlation_id",
                {"correlation_id": "test_correlation_id"},
            )

            await self.revocation_setup.on_registry_store_requested(self.profile, event)

            mock_setup.assert_called_once_with(
                self.profile, payload, RECORD_TYPE_REV_REG_DEF_STORE_EVENT
            )
            mock_store.assert_called_once()

    async def test_on_registry_full_detected_new_request_id(self):
        """Test on_registry_full_detected generates new request_id when needed."""
        payload = RevRegFullDetectedPayload(
            rev_reg_def_id="test_rev_reg_def_id",
            cred_def_id="test_cred_def_id",
            options={},  # No correlation / request_id
        )
        event = RevRegFullDetectedEvent(payload)

        with patch.object(test_module, "generate_correlation_id") as mock_gen_cor:
            mock_gen_cor.return_value = "test_correlation_id"

            with patch.object(
                AnonCredsRevocation, "handle_full_registry_event"
            ) as mock_handle:
                with patch.object(test_module, "generate_request_id") as mock_gen_req:
                    mock_gen_req.return_value = "new_request_id"

                    await self.revocation_setup.on_registry_full_detected(
                        self.profile, event
                    )

                    # Check that request_id was added to payload options
                    assert payload.options["request_id"] == "new_request_id"
                    mock_gen_cor.assert_called_once()
                    mock_handle.assert_called_once()

    async def test_clean_options_for_new_request(self):
        """Test _clean_options_for_new_request removes correlation_id."""
        options = {
            "correlation_id": "old_correlation_id",
            "request_id": "test_request_id",
            "other_option": "value",
        }

        cleaned_options = self.revocation_setup._clean_options_for_new_request(options)

        assert "correlation_id" not in cleaned_options
        assert cleaned_options["request_id"] == "test_request_id"
        assert cleaned_options["other_option"] == "value"
