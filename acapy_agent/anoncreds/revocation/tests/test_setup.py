from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ....core.event_bus import MockEventBus
from ....storage.type import (
    RECORD_TYPE_REV_LIST_CREATE_EVENT,
    RECORD_TYPE_REV_LIST_STORE_EVENT,
    RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
    RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
    RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
)
from ....tests import mock
from ....utils.testing import create_test_profile
from ...events import (
    INTERVENTION_REQUIRED_EVENT,
    ErrorInfoPayload,
    InterventionRequiredPayload,
    RevListCreateRequestedEvent,
    RevListCreateRequestedPayload,
    RevListCreateResponseEvent,
    RevListCreateResponsePayload,
    RevListFinishedEvent,
    RevListFinishedPayload,
    RevListStoreRequestedEvent,
    RevListStoreRequestedPayload,
    RevListStoreResponseEvent,
    RevListStoreResponsePayload,
    RevRegActivationRequestedEvent,
    RevRegActivationRequestedPayload,
    RevRegActivationResponseEvent,
    RevRegActivationResponsePayload,
    RevRegDefCreateFailurePayload,
    RevRegDefCreateRequestedEvent,
    RevRegDefCreateRequestedPayload,
    RevRegDefCreateResponseEvent,
    RevRegDefCreateResponsePayload,
    RevRegDefStoreRequestedEvent,
    RevRegDefStoreRequestedPayload,
    RevRegDefStoreResponseEvent,
    RevRegDefStoreResponsePayload,
    RevRegFullDetectedEvent,
    RevRegFullDetectedPayload,
    RevRegFullHandlingResponseEvent,
    RevRegFullHandlingResponsePayload,
)
from .. import revocation_setup as test_module
from ..auto_recovery.event_storage import EventStorageManager
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
        self.profile.inject = mock.Mock(return_value=MockEventBus())
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
            _, kwargs = mock_failure.call_args
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

    def test_clean_options_for_new_request(self):
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

    # Tests for on_registry_store_response
    async def test_on_registry_store_response_success(self):
        """Test on_registry_store_response handles success correctly."""
        rev_reg_def = MagicMock()
        rev_reg_def.cred_def_id = "test_cred_def_id"
        rev_reg_def.issuer_id = "test_issuer_id"
        rev_reg_def.type = "CL_ACCUM"
        rev_reg_def.value.max_cred_num = 100

        rev_reg_def_result = MagicMock()
        rev_reg_def_result.revocation_registry_definition_state.state = "finished"

        payload = RevRegDefStoreResponsePayload(
            rev_reg_def_id="test_rev_reg_def_id",
            rev_reg_def=rev_reg_def,
            rev_reg_def_result=rev_reg_def_result,
            tag="0",  # First registry tag
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=None,
        )
        event = RevRegDefStoreResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_success"
        ) as mock_success:
            with patch.object(
                AnonCredsRevocation, "emit_create_and_register_revocation_list_event"
            ) as mock_emit_rev_list:
                with patch.object(
                    AnonCredsRevocation,
                    "emit_create_revocation_registry_definition_event",
                ) as mock_emit_backup:
                    with patch.object(
                        AnonCredsRevocation, "_generate_backup_registry_tag"
                    ) as mock_gen_tag:
                        mock_gen_tag.return_value = "1"

                        await self.revocation_setup.on_registry_store_response(
                            self.profile, event
                        )

                        mock_success.assert_called_once()
                        mock_emit_rev_list.assert_called_once()
                        mock_emit_backup.assert_called_once()  # First registry triggers backup

    async def test_on_registry_store_response_failure(self):
        """Test on_registry_store_response handles failure correctly."""
        failure = MagicMock()
        failure.error_info = ErrorInfoPayload(
            error_msg="Storage failed", should_retry=True, retry_count=1
        )

        payload = RevRegDefStoreResponsePayload(
            rev_reg_def_id="test_rev_reg_def_id",
            rev_reg_def=MagicMock(),
            rev_reg_def_result=MagicMock(),
            tag="0",
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=failure,
        )
        event = RevRegDefStoreResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_failure"
        ) as mock_failure:
            mock_failure.return_value = True  # Retry was attempted

            await self.revocation_setup.on_registry_store_response(self.profile, event)

            mock_failure.assert_called_once()
            _, kwargs = mock_failure.call_args
            assert kwargs["failure_type"] == "registry_store"

    # Tests for rev list methods
    @patch.object(AnonCredsRevocation, "create_and_register_revocation_list")
    async def test_on_rev_list_create_requested(self, mock_create_list):
        """Test on_rev_list_create_requested uses correlation helper."""
        payload = RevListCreateRequestedPayload(
            rev_reg_def_id="test_rev_reg_def_id",
            options={"request_id": "test_request_id"},
        )
        event = RevListCreateRequestedEvent(payload)

        with patch.object(
            self.revocation_setup, "_setup_request_correlation"
        ) as mock_setup:
            mock_setup.return_value = (
                "test_correlation_id",
                {"correlation_id": "test_correlation_id"},
            )

            await self.revocation_setup.on_rev_list_create_requested(self.profile, event)

            mock_setup.assert_called_once_with(
                self.profile, payload, RECORD_TYPE_REV_LIST_CREATE_EVENT
            )
            mock_create_list.assert_called_once()

    async def test_on_rev_list_create_response_success(self):
        """Test on_rev_list_create_response handles success correctly."""
        payload = RevListCreateResponsePayload(
            rev_reg_def_id="test_rev_reg_def_id",
            rev_list_result=MagicMock(),
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=None,
        )
        event = RevListCreateResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_success"
        ) as mock_success:
            with patch.object(
                AnonCredsRevocation, "emit_store_revocation_list_event"
            ) as mock_emit:
                await self.revocation_setup.on_rev_list_create_response(
                    self.profile, event
                )

                mock_success.assert_called_once()
                mock_emit.assert_called_once()

    async def test_on_rev_list_create_response_failure(self):
        """Test on_rev_list_create_response handles failure correctly."""
        failure = MagicMock()
        failure.error_info = ErrorInfoPayload(
            error_msg="List creation failed", should_retry=True, retry_count=1
        )

        payload = RevListCreateResponsePayload(
            rev_reg_def_id="test_rev_reg_def_id",
            rev_list_result=None,
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=failure,
        )
        event = RevListCreateResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_failure"
        ) as mock_failure:
            mock_failure.return_value = True  # Retry was attempted

            await self.revocation_setup.on_rev_list_create_response(self.profile, event)

            mock_failure.assert_called_once()
            _, kwargs = mock_failure.call_args
            assert kwargs["failure_type"] == "rev_list_create"

    async def test_on_rev_list_finished(self):
        """Test on_rev_list_finished notifies revocation published event."""
        payload = RevListFinishedPayload(
            rev_reg_id="test_rev_reg_id",
            revoked=[1, 2, 3],
            options={"request_id": "test_request_id"},
        )
        event = RevListFinishedEvent(payload)

        with patch(
            "acapy_agent.anoncreds.revocation.revocation_setup.notify_revocation_published_event"
        ) as mock_notify:
            await self.revocation_setup.on_rev_list_finished(self.profile, event)

            mock_notify.assert_called_once_with(
                self.profile, "test_rev_reg_id", [1, 2, 3]
            )

    @patch.object(AnonCredsRevocation, "handle_store_revocation_list_request")
    async def test_on_rev_list_store_requested(self, mock_store_list):
        """Test on_rev_list_store_requested uses correlation helper."""
        payload = RevListStoreRequestedPayload(
            rev_reg_def_id="test_rev_reg_def_id",
            result=MagicMock(),
            options={"request_id": "test_request_id"},
        )
        event = RevListStoreRequestedEvent(payload)

        with patch.object(
            self.revocation_setup, "_setup_request_correlation"
        ) as mock_setup:
            mock_setup.return_value = (
                "test_correlation_id",
                {"correlation_id": "test_correlation_id"},
            )

            await self.revocation_setup.on_rev_list_store_requested(self.profile, event)

            mock_setup.assert_called_once_with(
                self.profile, payload, RECORD_TYPE_REV_LIST_STORE_EVENT
            )
            mock_store_list.assert_called_once()

    async def test_on_rev_list_store_response_success(self):
        """Test on_rev_list_store_response handles success correctly."""
        payload = RevListStoreResponsePayload(
            rev_reg_def_id="test_rev_reg_def_id",
            result=MagicMock(),
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
                "first_registry": True,  # Should trigger activation
            },
            failure=None,
        )
        event = RevListStoreResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_success"
        ) as mock_success:
            with patch.object(
                AnonCredsRevocation, "emit_set_active_registry_event"
            ) as mock_emit_activation:
                await self.revocation_setup.on_rev_list_store_response(
                    self.profile, event
                )

                mock_success.assert_called_once()
                mock_emit_activation.assert_called_once()

    async def test_on_rev_list_store_response_failure(self):
        """Test on_rev_list_store_response handles failure using helper method."""
        failure = MagicMock()
        failure.error_info = ErrorInfoPayload(
            error_msg="Store failed", should_retry=True, retry_count=1
        )
        failure.result = MagicMock()

        payload = RevListStoreResponsePayload(
            rev_reg_def_id="test_rev_reg_def_id",
            result=MagicMock(),
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=failure,
        )
        event = RevListStoreResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_failure"
        ) as mock_failure:
            mock_failure.return_value = True  # Retry was attempted

            await self.revocation_setup.on_rev_list_store_response(self.profile, event)

            mock_failure.assert_called_once()
            _, kwargs = mock_failure.call_args
            assert kwargs["failure_type"] == "rev_list_store"

    # Tests for registry activation request
    @patch.object(AnonCredsRevocation, "handle_activate_registry_request")
    async def test_on_registry_activation_requested(self, mock_handle_activate):
        """Test on_registry_activation_requested uses correlation helper."""
        payload = RevRegActivationRequestedPayload(
            rev_reg_def_id="test_rev_reg_def_id",
            options={"request_id": "test_request_id", "cred_def_id": "test_cred_def_id"},
        )
        event = RevRegActivationRequestedEvent(payload)

        with patch.object(
            self.revocation_setup, "_setup_request_correlation"
        ) as mock_setup:
            mock_setup.return_value = (
                "test_correlation_id",
                {
                    "correlation_id": "test_correlation_id",
                    "request_id": "test_request_id",
                },
            )

            await self.revocation_setup.on_registry_activation_requested(
                self.profile, event
            )

            mock_setup.assert_called_once_with(
                self.profile, payload, RECORD_TYPE_REV_REG_ACTIVATION_EVENT
            )
            mock_handle_activate.assert_called_once_with(
                rev_reg_def_id="test_rev_reg_def_id",
                options={
                    "correlation_id": "test_correlation_id",
                    "request_id": "test_request_id",
                },
            )

    # Tests for registry activation response
    async def test_on_registry_activation_response_success(self):
        """Test on_registry_activation_response handles success correctly."""
        payload = RevRegActivationResponsePayload(
            rev_reg_def_id="test_rev_reg_def_id",
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
                "cred_def_id": "test_cred_def_id",
                "old_rev_reg_def_id": "old_rev_reg_def_id",  # Triggers backup creation
            },
            failure=None,
        )
        event = RevRegActivationResponseEvent(payload)

        with patch.object(EventStorageManager, "update_event_response") as mock_update:
            with patch.object(
                AnonCredsRevocation, "get_created_revocation_registry_definition"
            ) as mock_get_def:
                mock_rev_reg_def = MagicMock()
                mock_rev_reg_def.issuer_id = "test_issuer_id"
                mock_rev_reg_def.type = "CL_ACCUM"
                mock_rev_reg_def.value.max_cred_num = 100
                mock_get_def.return_value = mock_rev_reg_def

                with patch.object(
                    AnonCredsRevocation,
                    "emit_create_revocation_registry_definition_event",
                ) as mock_emit_backup:
                    with patch.object(
                        AnonCredsRevocation, "_generate_backup_registry_tag"
                    ) as mock_gen_tag:
                        mock_gen_tag.return_value = "backup_tag"

                        await self.revocation_setup.on_registry_activation_response(
                            self.profile, event
                        )

                        mock_update.assert_called_once()
                        mock_get_def.assert_called_once()
                        mock_emit_backup.assert_called_once()

    async def test_on_registry_activation_response_failure(self):
        """Test on_registry_activation_response handles failure correctly."""
        failure = MagicMock()
        failure.error_info = ErrorInfoPayload(
            error_msg="Activation failed", should_retry=True, retry_count=1
        )

        payload = RevRegActivationResponsePayload(
            rev_reg_def_id="test_rev_reg_def_id",
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=failure,
        )
        event = RevRegActivationResponseEvent(payload)

        with patch("asyncio.sleep") as mock_sleep:
            with patch.object(
                EventStorageManager, "update_event_for_retry"
            ) as mock_update:
                with patch.object(
                    AnonCredsRevocation, "emit_set_active_registry_event"
                ) as mock_retry:
                    await self.revocation_setup.on_registry_activation_response(
                        self.profile, event
                    )

                    mock_sleep.assert_called_once()
                    mock_update.assert_called_once()
                    mock_retry.assert_called_once()

    async def test_on_registry_activation_response_success_no_rev_reg_def(self):
        """Test on_registry_activation_response when rev_reg_def retrieval fails."""
        payload = RevRegActivationResponsePayload(
            rev_reg_def_id="test_rev_reg_def_id",
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
                "cred_def_id": "test_cred_def_id",
                "old_rev_reg_def_id": "old_rev_reg_def_id",  # Triggers backup creation
            },
            failure=None,
        )
        event = RevRegActivationResponseEvent(payload)

        with patch.object(EventStorageManager, "update_event_response") as mock_update:
            with patch.object(
                AnonCredsRevocation, "get_created_revocation_registry_definition"
            ) as mock_get_def:
                # Mock get_created_revocation_registry_definition to return None
                mock_get_def.return_value = None

                with patch.object(
                    self.revocation_setup,
                    "_notify_issuer_about_failure",
                    new_callable=AsyncMock,
                ) as mock_notify_failure:
                    await self.revocation_setup.on_registry_activation_response(
                        self.profile, event
                    )

                    # Verify event was updated as successful
                    mock_update.assert_called_once()

                    # Verify get_created_revocation_registry_definition was called
                    mock_get_def.assert_called_once_with("test_rev_reg_def_id")

                    # Verify _notify_issuer_about_failure was called with expected args
                    mock_notify_failure.assert_called_once_with(
                        profile=self.profile,
                        failure_type="registry_activation",
                        identifier="test_rev_reg_def_id",
                        error_msg="Could not retrieve registry definition for creating backup",
                        options=payload.options,
                    )

    # Tests for full registry handling response
    async def test_on_registry_full_handling_response_success(self):
        """Test on_registry_full_handling_response handles success correctly."""
        payload = RevRegFullHandlingResponsePayload(
            old_rev_reg_def_id="old_rev_reg_def_id",
            new_active_rev_reg_def_id="new_active_rev_reg_def_id",
            cred_def_id="test_cred_def_id",
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=None,
        )
        event = RevRegFullHandlingResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_success"
        ) as mock_success:
            await self.revocation_setup.on_registry_full_handling_response(
                self.profile, event
            )

            mock_success.assert_called_once()
            _, kwargs = mock_success.call_args
            assert kwargs["event_type"] == RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT
            assert kwargs["correlation_id"] == "test_correlation_id"

    async def test_on_registry_full_handling_response_failure(self):
        """Test on_registry_full_handling_response handles failure using helper method."""
        failure = MagicMock()
        failure.error_info = ErrorInfoPayload(
            error_msg="Full handling failed", should_retry=True, retry_count=1
        )

        payload = RevRegFullHandlingResponsePayload(
            old_rev_reg_def_id="old_rev_reg_def_id",
            new_active_rev_reg_def_id=None,
            cred_def_id="test_cred_def_id",
            options={
                "correlation_id": "test_correlation_id",
                "request_id": "test_request_id",
            },
            failure=failure,
        )
        event = RevRegFullHandlingResponseEvent(payload)

        with patch.object(
            self.revocation_setup, "_handle_response_failure"
        ) as mock_failure:
            mock_failure.return_value = True  # Retry was attempted

            await self.revocation_setup.on_registry_full_handling_response(
                self.profile, event
            )

            mock_failure.assert_called_once()
            _, kwargs = mock_failure.call_args
            assert kwargs["failure_type"] == "full_registry_handling"

    # Tests for _notify_issuer_about_failure
    async def test_notify_issuer_about_failure_with_event_bus(self):
        """Test _notify_issuer_about_failure with event bus available."""
        from ....core.event_bus import Event

        mock_event_bus = MagicMock()
        mock_event_bus.notify = AsyncMock()
        self.profile.inject_or = MagicMock(return_value=mock_event_bus)

        await self.revocation_setup._notify_issuer_about_failure(
            profile=self.profile,
            failure_type="registry_creation",
            identifier="test_identifier",
            error_msg="Test error message",
            options={"request_id": "test_request_id"},
        )

        mock_event_bus.notify.assert_called_once()
        call_args = mock_event_bus.notify.call_args
        assert call_args[1]["profile"] == self.profile

        event = call_args[1]["event"]
        assert isinstance(event, Event)
        assert event.topic == INTERVENTION_REQUIRED_EVENT

        payload = event.payload
        assert isinstance(payload, InterventionRequiredPayload)
        assert payload.point_of_failure == "registry_creation"
        assert payload.error_msg == "Test error message"
        assert payload.identifier == "test_identifier"
        assert payload.options == {"request_id": "test_request_id"}

    async def test_notify_issuer_about_failure_without_event_bus(self):
        """Test _notify_issuer_about_failure without event bus available."""
        self.profile.inject_or = MagicMock(return_value=None)

        # Should not raise exception, just log error
        await self.revocation_setup._notify_issuer_about_failure(
            profile=self.profile,
            failure_type="registry_creation",
            identifier="test_identifier",
            error_msg="Test error message",
            options={"request_id": "test_request_id"},
        )
