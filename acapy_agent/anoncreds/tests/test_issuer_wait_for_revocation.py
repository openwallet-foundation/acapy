"""Tests for credential definition creation with wait_for_revocation_setup options."""

import json
from unittest import IsolatedAsyncioTestCase

import pytest

from ...anoncreds.models.credential_definition import (
    CredDef,
    CredDefResult,
    CredDefState,
    CredDefValue,
    CredDefValuePrimary,
)
from ...anoncreds.models.schema import (
    AnonCredsSchema,
    GetSchemaResult,
)
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import issuer as test_module
from ..revocation.revocation_setup import DefaultRevocationSetup


@pytest.mark.anoncreds
class TestAnonCredsIssuerWaitForRevocation(IsolatedAsyncioTestCase):
    """Tests for wait_for_revocation_setup functionality."""

    async def asyncSetUp(self) -> None:
        """Set up test environment."""
        self.profile = await create_test_profile(
            settings={"wallet.type": "askar-anoncreds"},
        )
        self.issuer = test_module.AnonCredsIssuer(self.profile)

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_store_credential_definition_with_wait_false(self, mock_notify):
        """Test that store_credential_definition works with wait_for_revocation_setup=False."""
        # Setup mocks
        schema_result = GetSchemaResult(
            schema_id="schema-id",
            schema=AnonCredsSchema(
                issuer_id="issuer-id",
                name="schema-name",
                version="1.0",
                attr_names=["attr1", "attr2"],
            ),
            schema_metadata={},
            resolution_metadata={},
        )

        cred_def_result = CredDefResult(
            job_id="job-id",
            credential_definition_state=CredDefState(
                state="finished",
                credential_definition=CredDef(
                    issuer_id="issuer-id",
                    schema_id="schema-id",
                    tag="tag",
                    type="CL",
                    value=CredDefValue(
                        primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")
                    ),
                ),
                credential_definition_id="cred-def-id",
            ),
            credential_definition_metadata={},
            registration_metadata={},
        )

        # Mock transaction
        self.profile.transaction = mock.Mock(
            return_value=mock.MagicMock(
                insert=mock.CoroutineMock(),
                commit=mock.CoroutineMock(),
            )
        )

        # Call with wait_for_revocation_setup=False - should work normally
        await self.issuer.store_credential_definition(
            schema_result=schema_result,
            cred_def_result=cred_def_result,
            cred_def_private=mock.MagicMock(),
            key_proof=mock.MagicMock(),
            support_revocation=True,
            max_cred_num=1000,
            options={"wait_for_revocation_setup": False},
        )

        # Should notify with correct parameters including options
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args[0][0]  # Get the event passed to notify
        assert call_args.payload.cred_def_id == "job-id"
        assert call_args.payload.support_revocation is True
        assert not call_args.payload.options["wait_for_revocation_setup"]

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_store_credential_definition_with_wait_true(self, mock_notify):
        """Test that store_credential_definition works with wait_for_revocation_setup=True."""
        schema_result = GetSchemaResult(
            schema_id="schema-id",
            schema=AnonCredsSchema(
                issuer_id="issuer-id",
                name="schema-name",
                version="1.0",
                attr_names=["attr1", "attr2"],
            ),
            schema_metadata={},
            resolution_metadata={},
        )

        cred_def_result = CredDefResult(
            job_id="job-id",
            credential_definition_state=CredDefState(
                state="finished",
                credential_definition=CredDef(
                    issuer_id="issuer-id",
                    schema_id="schema-id",
                    tag="tag",
                    type="CL",
                    value=CredDefValue(
                        primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")
                    ),
                ),
                credential_definition_id="cred-def-id",
            ),
            credential_definition_metadata={},
            registration_metadata={},
        )

        self.profile.transaction = mock.Mock(
            return_value=mock.MagicMock(
                insert=mock.CoroutineMock(),
                commit=mock.CoroutineMock(),
            )
        )

        # Call with wait_for_revocation_setup=True - should still work normally
        # (waiting is now handled in the event handler, not in store_credential_definition)
        await self.issuer.store_credential_definition(
            schema_result=schema_result,
            cred_def_result=cred_def_result,
            cred_def_private=mock.MagicMock(),
            key_proof=mock.MagicMock(),
            support_revocation=True,
            max_cred_num=1000,
            options={"wait_for_revocation_setup": True},
        )

        # Should notify with correct parameters including options
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args[0][0]  # Get the event passed to notify
        assert call_args.payload.cred_def_id == "job-id"
        assert call_args.payload.support_revocation is True
        assert call_args.payload.options["wait_for_revocation_setup"] is True

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_store_credential_definition_no_support_revocation(self, mock_notify):
        """Test that store_credential_definition works with support_revocation=False."""
        schema_result = GetSchemaResult(
            schema_id="schema-id",
            schema=AnonCredsSchema(
                issuer_id="issuer-id",
                name="schema-name",
                version="1.0",
                attr_names=["attr1", "attr2"],
            ),
            schema_metadata={},
            resolution_metadata={},
        )

        cred_def_result = CredDefResult(
            job_id="job-id",
            credential_definition_state=CredDefState(
                state="finished",
                credential_definition=CredDef(
                    issuer_id="issuer-id",
                    schema_id="schema-id",
                    tag="tag",
                    type="CL",
                    value=CredDefValue(
                        primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")
                    ),
                ),
                credential_definition_id="cred-def-id",
            ),
            credential_definition_metadata={},
            registration_metadata={},
        )

        self.profile.transaction = mock.Mock(
            return_value=mock.MagicMock(
                insert=mock.CoroutineMock(),
                commit=mock.CoroutineMock(),
            )
        )

        # Call with support_revocation=False - should work normally
        await self.issuer.store_credential_definition(
            schema_result=schema_result,
            cred_def_result=cred_def_result,
            cred_def_private=mock.MagicMock(),
            key_proof=mock.MagicMock(),
            support_revocation=False,
            max_cred_num=1000,
            options={
                "wait_for_revocation_setup": True
            },  # This shouldn't matter when revocation is disabled
        )

        # Should notify with correct parameters
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args[0][0]  # Get the event passed to notify
        assert call_args.payload.cred_def_id == "job-id"
        assert not call_args.payload.support_revocation

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
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
            with mock.patch.object(test_module.CredDef, "from_json") as mock_from_json:
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
            mock_revocation.create_and_register_revocation_registry_definition = (
                mock.CoroutineMock()
            )
            mock_revocation.wait_for_active_revocation_registry = mock.CoroutineMock()

            # Call the event handler
            await setup_manager.on_cred_def(self.profile, event)

            # Should create registries but not wait
            assert (
                mock_revocation.create_and_register_revocation_registry_definition.call_count
                == 2
            )
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
            mock_revocation.create_and_register_revocation_registry_definition = (
                mock.CoroutineMock()
            )
            mock_revocation.wait_for_active_revocation_registry = mock.CoroutineMock()

            # Call the event handler
            await setup_manager.on_cred_def(self.profile, event)

            # Should create registries AND wait
            assert (
                mock_revocation.create_and_register_revocation_registry_definition.call_count
                == 2
            )
            mock_revocation.wait_for_active_revocation_registry.assert_called_once_with(
                "test-cred-def-id"
            )
