"""Tests for wait_for_revocation_setup functionality in AnonCredsIssuer."""

import asyncio
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
    async def test_wait_for_revocation_setup_false_fire_and_forget(self, mock_notify):
        """Test wait_for_revocation_setup=False (fire and forget mode)."""
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

        # Call with wait_for_revocation_setup=False
        await self.issuer.store_credential_definition(
            schema_result=schema_result,
            cred_def_result=cred_def_result,
            cred_def_private=mock.MagicMock(),
            key_proof=mock.MagicMock(),
            support_revocation=True,
            max_cred_num=1000,
            options={"wait_for_revocation_setup": False},
        )

        # Should notify but not wait
        mock_notify.assert_called_once()

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_wait_for_revocation_setup_no_support_revocation(self, mock_notify):
        """Test wait_for_revocation_setup=True but support_revocation=False."""
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

        # Call with support_revocation=False (should not wait regardless of wait flag)
        await self.issuer.store_credential_definition(
            schema_result=schema_result,
            cred_def_result=cred_def_result,
            cred_def_private=mock.MagicMock(),
            key_proof=mock.MagicMock(),
            support_revocation=False,
            max_cred_num=1000,
            options={"wait_for_revocation_setup": True},
        )

        mock_notify.assert_called_once()

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_wait_for_revocation_setup_successful_completion(self, mock_notify):
        """Test wait_for_revocation_setup=True with successful completion."""
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

        # Mock revocation service to return 2 finished registries immediately
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the database query to return finished registries
            with mock.patch.object(
                self.issuer.profile, "session"
            ) as mock_session_context:
                mock_session = mock.MagicMock()
                mock_session.handle.fetch_all = mock.CoroutineMock(
                    return_value=[mock.MagicMock(), mock.MagicMock()]  # 2 registries
                )
                mock_session_context.return_value.__aenter__ = mock.CoroutineMock(
                    return_value=mock_session
                )
                mock_session_context.return_value.__aexit__ = mock.CoroutineMock(
                    return_value=None
                )

                await self.issuer.store_credential_definition(
                    schema_result=schema_result,
                    cred_def_result=cred_def_result,
                    cred_def_private=mock.MagicMock(),
                    key_proof=mock.MagicMock(),
                    support_revocation=True,
                    max_cred_num=1000,
                    options={"wait_for_revocation_setup": True},
                )

                mock_notify.assert_called_once()
                # Should not need to sleep since registries are immediately available
                mock_sleep.assert_not_called()

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_wait_for_revocation_setup_timeout(self, mock_notify):
        """Test wait_for_revocation_setup=True with timeout."""
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

        # Mock revocation service to return only 1 registry (incomplete)
        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the database query to return only 1 registry (incomplete)
            with mock.patch.object(
                self.issuer.profile, "session"
            ) as mock_session_context:
                mock_session = mock.MagicMock()
                mock_session.handle.fetch_all = mock.CoroutineMock(
                    return_value=[mock.MagicMock()]  # Only 1 registry, need 2
                )
                mock_session_context.return_value.__aenter__ = mock.CoroutineMock(
                    return_value=mock_session
                )
                mock_session_context.return_value.__aexit__ = mock.CoroutineMock(
                    return_value=None
                )

                with self.assertRaises(test_module.AnonCredsIssuerError) as exc_context:
                    await self.issuer.store_credential_definition(
                        schema_result=schema_result,
                        cred_def_result=cred_def_result,
                        cred_def_private=mock.MagicMock(),
                        key_proof=mock.MagicMock(),
                        support_revocation=True,
                        max_cred_num=1000,
                        options={"wait_for_revocation_setup": True},
                    )

                # Check error message includes helpful information
                error_message = str(exc_context.exception)
                assert "Timeout waiting for revocation setup completion" in error_message
                assert "job-id" in error_message
                assert (
                    "Expected 2 revocation registries, but only 1 were completed"
                    in error_message
                )
                assert "still be in progress in the background" in error_message

                mock_notify.assert_called_once()

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_wait_for_revocation_setup_partial_completion_timeout(
        self, mock_notify
    ):
        """Test timeout with partial completion (1/2 registries)."""
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

        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the database query to simulate progression: 0 -> 1 -> still 1 (partial completion)
            with mock.patch.object(
                self.issuer.profile, "session"
            ) as mock_session_context:
                mock_session = mock.MagicMock()
                mock_session.handle.fetch_all = mock.CoroutineMock(
                    side_effect=[[], [mock.MagicMock()]]  # Stays at 1 registry
                )
                mock_session_context.return_value.__aenter__ = mock.CoroutineMock(
                    return_value=mock_session
                )
                mock_session_context.return_value.__aexit__ = mock.CoroutineMock(
                    return_value=None
                )

                with self.assertRaises(test_module.AnonCredsIssuerError) as exc_context:
                    await self.issuer.store_credential_definition(
                        schema_result=schema_result,
                        cred_def_result=cred_def_result,
                        cred_def_private=mock.MagicMock(),
                        key_proof=mock.MagicMock(),
                        support_revocation=True,
                        max_cred_num=1000,
                        options={"wait_for_revocation_setup": True},
                    )

                # Check that it shows partial progress in error message
                error_message = str(exc_context.exception)
                assert (
                    "Expected 2 revocation registries, but only 1 were completed"
                    in error_message
                )
        mock_notify.assert_called_once()

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_wait_for_revocation_setup_polling_errors_continue(self, mock_notify):
        """Test that polling continues despite transient errors."""
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

        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the database query to simulate: error -> error -> success
            with mock.patch.object(
                self.issuer.profile, "session"
            ) as mock_session_context:
                mock_session = mock.MagicMock()
                mock_session.handle.fetch_all = mock.CoroutineMock(
                    side_effect=[
                        Exception("Transient error 1"),
                        Exception("Transient error 2"),
                        [
                            mock.MagicMock(),
                            mock.MagicMock(),
                        ],  # Success on 3rd try - 2 registries
                    ]
                )
                mock_session_context.return_value.__aenter__ = mock.CoroutineMock(
                    return_value=mock_session
                )
                mock_session_context.return_value.__aexit__ = mock.CoroutineMock(
                    return_value=None
                )

                # Should complete successfully despite initial errors
                await self.issuer.store_credential_definition(
                    schema_result=schema_result,
                    cred_def_result=cred_def_result,
                    cred_def_private=mock.MagicMock(),
                    key_proof=mock.MagicMock(),
                    support_revocation=True,
                    max_cred_num=1000,
                    options={"wait_for_revocation_setup": True},
                )

                mock_notify.assert_called_once()
                # Should have tried 3 times
                assert mock_session.handle.fetch_all.call_count == 3

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_wait_for_revocation_setup_immediate_completion(self, mock_notify):
        """Test immediate completion (registries already exist)."""
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

        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            # Mock the database query to return 3 registries immediately (more than needed)
            with mock.patch.object(
                self.issuer.profile, "session"
            ) as mock_session_context:
                mock_session = mock.MagicMock()
                mock_session.handle.fetch_all = mock.CoroutineMock(
                    return_value=[
                        mock.MagicMock(),
                        mock.MagicMock(),
                        mock.MagicMock(),
                    ]  # 3 registries > 2
                )
                mock_session_context.return_value.__aenter__ = mock.CoroutineMock(
                    return_value=mock_session
                )
                mock_session_context.return_value.__aexit__ = mock.CoroutineMock(
                    return_value=None
                )

                start_time = asyncio.get_event_loop().time()
                await self.issuer.store_credential_definition(
                    schema_result=schema_result,
                    cred_def_result=cred_def_result,
                    cred_def_private=mock.MagicMock(),
                    key_proof=mock.MagicMock(),
                    support_revocation=True,
                    max_cred_num=1000,
                    options={"wait_for_revocation_setup": True},
                )
                end_time = asyncio.get_event_loop().time()

                # Should complete very quickly (no polling needed)
                assert end_time - start_time < 0.1  # Less than 100ms
                mock_notify.assert_called_once()
                # Should only check once
                mock_session.handle.fetch_all.assert_called_once()
                # Should not need to sleep since registries are immediately available
                mock_sleep.assert_not_called()

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_finish_cred_def_with_wait_for_revocation_setup(self, mock_notify):
        """Test finish_cred_def method also respects wait_for_revocation_setup."""
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

        with mock.patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None  # Make sleep instant

            with mock.patch.object(
                self.issuer, "_finish_registration", return_value=mock_entry
            ):
                with mock.patch.object(
                    test_module.CredDef, "from_json"
                ) as mock_from_json:
                    mock_cred_def = mock.MagicMock()
                    mock_cred_def.schema_id = "schema-id"
                    mock_cred_def.issuer_id = "issuer-id"
                    mock_from_json.return_value = mock_cred_def

                    # Mock the database query to return 2 finished registries
                    with mock.patch.object(
                        self.issuer.profile, "session"
                    ) as mock_session_context:
                        mock_session = mock.MagicMock()
                        mock_session.handle.fetch_all = mock.CoroutineMock(
                            return_value=[
                                mock.MagicMock(),
                                mock.MagicMock(),
                            ]  # 2 registries
                        )
                        mock_session_context.return_value.__aenter__ = mock.CoroutineMock(
                            return_value=mock_session
                        )
                        mock_session_context.return_value.__aexit__ = mock.CoroutineMock(
                            return_value=None
                        )

                        await self.issuer.finish_cred_def(
                            job_id="job-id",
                            cred_def_id="cred-def-id",
                            options={"wait_for_revocation_setup": True},
                        )

                        mock_notify.assert_called_once()
                        mock_session.handle.fetch_all.assert_called_once()
                        # Should not need to sleep since registries are immediately available
                        mock_sleep.assert_not_called()
