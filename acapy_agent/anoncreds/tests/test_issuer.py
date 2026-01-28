import json
from typing import Optional
from unittest import IsolatedAsyncioTestCase

import pytest
from anoncreds import (
    AnoncredsError,
    Credential,
    CredentialDefinition,
    CredentialOffer,
    W3cCredential,
)
from aries_askar import AskarError, AskarErrorCode

from ...anoncreds.base import AnonCredsObjectAlreadyExists, AnonCredsSchemaAlreadyExists
from ...anoncreds.models.credential_definition import (
    CredDef,
    CredDefResult,
    CredDefState,
    CredDefValue,
    CredDefValuePrimary,
    CredDefValueRevocation,
    GetCredDefResult,
)
from ...anoncreds.models.schema import (
    AnonCredsSchema,
    GetSchemaResult,
    SchemaResult,
    SchemaState,
)
from ...askar.profile_anon import AskarAnonCredsProfile, AskarAnonCredsProfileSession
from ...core.event_bus import Event, MockEventBus
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import issuer as test_module
from ..events import SchemaFinishedEvent


class MockSchemaEntry:
    def __init__(self, name: Optional[str] = "name"):
        self.name = name
        self.version = "1.0"
        self.value_json = "value_json"
        self.issuer_id = "issuer-id"

    def serialize(self):
        return self.value_json


class MockSchemaValue:
    attr_names = ["attr1", "attr2"]


class MockSchemaResult:
    def __init__(self) -> None:
        self.schema = MockSchemaEntry()
        self.schema_value = MockSchemaValue()


class MockCredDefState:
    credential_definition_id = "cred-def-id"
    state = "finished"


class MockCredDefEntry:
    def __init__(self, name: Optional[str] = "name", epoch: Optional[str] = None):
        self.name = name
        self.tags = {
            "schema_id": "schema-id",
            "epoch": epoch,
        }

    credential_definition_state = MockCredDefState()
    raw_value = "raw-value"
    value_json = {}

    def to_json(self):
        return json.dumps({"cred_def": "cred_def"})


class MockCredDefPrivate:
    def to_json_buffer(self):
        return "cred-def-private"


class MockKeyProof:
    def to_json_buffer(self):
        return "key-proof"

    raw_value = "raw-value"


class MockCredOffer:
    def to_json(self):
        return json.dumps({"cred_offer": "cred_offer"})


class MockCredential:
    def to_json(self):
        return json.dumps({"credential": "credential"})


def get_mock_schema_result(
    job_id: Optional[str] = "job-id", schema_id: Optional[str] = "schema-id"
):
    return SchemaResult(
        job_id=job_id,
        schema_state=SchemaState(
            state="finished",
            schema_id=schema_id,
            schema=AnonCredsSchema(
                issuer_id="issuer-id",
                name="name",
                version="1.0",
                attr_names=["attr1", "attr2"],
            ),
        ),
    )


@pytest.mark.anoncreds
class TestAnonCredsIssuer(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile(
            settings={"wallet.type": "askar-anoncreds"},
        )
        self.issuer = test_module.AnonCredsIssuer(self.profile)

    async def test_init(self):
        assert isinstance(self.issuer, test_module.AnonCredsIssuer)
        assert isinstance(self.issuer.profile, AskarAnonCredsProfile)

    async def test_init_wrong_profile_type(self):
        self.issuer._profile = await create_test_profile(
            settings={"wallet.type": "askar"},
        )
        with self.assertRaises(ValueError):
            self.issuer.profile

    async def test_notify(self):
        self.profile.inject = mock.Mock(return_value=MockEventBus())
        await self.issuer.notify(Event(topic="test-topic"))

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    @mock.patch.object(AnonCredsSchema, "deserialize", return_value="test")
    async def test_create_and_register_schema_finds_schema_raises_x(
        self, _, mock_session_handle
    ):
        mock_schema = AnonCredsSchema(
            issuer_id="issuer-id",
            name="schema-name",
            version="1.0",
            attr_names=["attr1", "attr2"],
        )
        mock_schema.value_json = "value_json"
        mock_session_handle.fetch_all = mock.CoroutineMock(return_value=[mock_schema])
        with self.assertRaises(AnonCredsObjectAlreadyExists):
            await self.issuer.create_and_register_schema(
                issuer_id="issuer-id",
                name="name",
                version="1.0",
                attr_names=["attr1", "attr2"],
            )

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    async def test_create_and_register_schema(self, mock_session_handle):
        mock_session_handle.fetch_all = mock.CoroutineMock(return_value=[])
        mock_session_handle.insert = mock.CoroutineMock(return_value=None)
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                register_schema=mock.CoroutineMock(return_value=get_mock_schema_result())
            )
        )
        result = await self.issuer.create_and_register_schema(
            issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
            name="example name",
            version="1.0",
            attr_names=["attr1", "attr2"],
        )

        assert result is not None
        mock_session_handle.fetch_all.assert_called_once()
        mock_session_handle.insert.assert_called_once()

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    async def test_create_and_register_schema_missing_schema_id_or_job_id(
        self, mock_session_handle
    ):
        mock_session_handle.fetch_all = mock.CoroutineMock(return_value=[])
        mock_session_handle.insert = mock.CoroutineMock(return_value=None)
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                register_schema=mock.CoroutineMock(
                    side_effect=[
                        SchemaResult(
                            job_id=None,
                            schema_state=SchemaState(
                                state="finished",
                                schema_id=None,
                                schema=AnonCredsSchema(
                                    issuer_id="issuer-id",
                                    name="name",
                                    version="1.0",
                                    attr_names=["attr1", "attr2"],
                                ),
                            ),
                        ),
                        SchemaResult(
                            job_id=None,
                            schema_state=SchemaState(
                                state="finished",
                                schema_id="schema-id",
                                schema=AnonCredsSchema(
                                    issuer_id="issuer-id",
                                    name="name",
                                    version="1.0",
                                    attr_names=["attr1", "attr2"],
                                ),
                            ),
                        ),
                        SchemaResult(
                            job_id="job-id",
                            schema_state=SchemaState(
                                state="finished",
                                schema_id=None,
                                schema=AnonCredsSchema(
                                    issuer_id="issuer-id",
                                    name="name",
                                    version="1.0",
                                    attr_names=["attr1", "attr2"],
                                ),
                            ),
                        ),
                    ]
                )
            )
        )

        with self.assertRaises(ValueError):
            await self.issuer.create_and_register_schema(
                issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                name="example name",
                version="1.0",
                attr_names=["attr1", "attr2"],
            )

            mock_session_handle.fetch_all.assert_called_once()
            mock_session_handle.insert.assert_not_called

        await self.issuer.create_and_register_schema(
            issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
            name="example name",
            version="1.0",
            attr_names=["attr1", "attr2"],
        )
        await self.issuer.create_and_register_schema(
            issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
            name="example name",
            version="1.0",
            attr_names=["attr1", "attr2"],
        )

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    async def test_create_and_register_schema_fail_insert(self, mock_session_handle):
        mock_session_handle.fetch_all = mock.CoroutineMock(return_value=[])
        mock_session_handle.insert = mock.CoroutineMock(
            side_effect=AskarError(AskarErrorCode.UNEXPECTED, message="test-msg")
        )
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                register_schema=mock.CoroutineMock(return_value=get_mock_schema_result())
            )
        )

        with self.assertRaises(test_module.AnonCredsIssuerError):
            result = await self.issuer.create_and_register_schema(
                issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                name="example name",
                version="1.0",
                attr_names=["attr1", "attr2"],
            )

            assert result is not None
            mock_session_handle.fetch_all.assert_called_once()
            mock_session_handle.insert.assert_called_once()

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    async def test_create_and_register_schema_already_exists_but_not_in_wallet(
        self, mock_session_handle
    ):
        mock_session_handle.fetch_all = mock.CoroutineMock(return_value=[])
        mock_session_handle.insert = mock.CoroutineMock(return_value=None)
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                register_schema=mock.CoroutineMock(
                    side_effect=AnonCredsSchemaAlreadyExists(
                        message="message",
                        obj_id="id",
                        obj=AnonCredsSchema(
                            issuer_id="issuer-id",
                            name="schema-name",
                            version="1.0",
                            attr_names=["attr1", "attr2"],
                        ),
                    )
                )
            )
        )
        with self.assertRaises(test_module.AnonCredsIssuerError):
            await self.issuer.create_and_register_schema(
                issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                name="example",
                version="1.0",
                attr_names=["attr1", "attr2"],
            )

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    async def test_create_and_register_schema_without_job_id_or_schema_id_raises_x(
        self, mock_session_handle
    ):
        mock_session_handle.fetch_all = mock.CoroutineMock(return_value=[])
        mock_session_handle.insert = mock.CoroutineMock(return_value=None)
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                register_schema=mock.CoroutineMock(
                    side_effect=[
                        get_mock_schema_result(job_id=None, schema_id=None),
                        get_mock_schema_result(job_id=None),
                        get_mock_schema_result(schema_id=None),
                    ]
                )
            )
        )
        with self.assertRaises(ValueError):
            await self.issuer.create_and_register_schema(
                issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                name="name",
                version="1.0",
                attr_names=["attr1", "attr2"],
            )
        await self.issuer.create_and_register_schema(
            issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
            name="name",
            version="1.0",
            attr_names=["attr1", "attr2"],
        )
        await self.issuer.create_and_register_schema(
            issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
            name="name",
            version="1.0",
            attr_names=["attr1", "attr2"],
        )

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    @mock.patch.object(test_module.AnonCredsIssuer, "store_schema")
    async def test_create_and_register_schema_with_endorsed_transaction_response_does_not_store_schema(
        self, mock_store_schema, mock_session_handle
    ):
        mock_session_handle.fetch_all = mock.CoroutineMock(return_value=[])
        mock_session_handle.insert = mock.CoroutineMock(return_value=None)
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                register_schema=mock.CoroutineMock(
                    return_value=SchemaResult(
                        job_id="job-id",
                        schema_state=SchemaState(
                            state="finished",
                            schema_id="schema-id",
                            schema=AnonCredsSchema(
                                issuer_id="issuer-id",
                                name="schema-name",
                                version="1.0",
                                attr_names=["attr1", "attr2"],
                            ),
                        ),
                    )
                )
            )
        )
        result = await self.issuer.create_and_register_schema(
            issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
            name="example name",
            version="1.0",
            attr_names=["attr1", "attr2"],
        )

        assert isinstance(result, SchemaResult)
        assert mock_store_schema.called

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_finish_schema(self, mock_notify):
        # Create a mock entry with a valid schema JSON value
        mock_entry = mock.MagicMock()
        mock_entry.value = json.dumps(
            {
                "issuerId": "issuer-id",
                "name": "test-schema",
                "version": "1.0",
                "attrNames": ["attr1", "attr2"],
            }
        )
        mock_entry.tags = {}

        # Mock the transaction context manager
        mock_txn = mock.MagicMock()
        mock_handle = mock.MagicMock()
        mock_handle.fetch = mock.CoroutineMock(return_value=mock_entry)
        mock_handle.insert = mock.CoroutineMock(return_value=None)
        mock_handle.remove = mock.CoroutineMock(return_value=None)
        mock_txn.handle = mock_handle
        mock_txn.commit = mock.CoroutineMock(return_value=None)
        mock_txn.__aenter__ = mock.CoroutineMock(return_value=mock_txn)
        mock_txn.__aexit__ = mock.CoroutineMock(return_value=None)

        self.profile.transaction = mock.Mock(return_value=mock_txn)

        await self.issuer.finish_schema(job_id="job-id", schema_id="schema-id")

        # Verify that SchemaFinishedEvent was emitted
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert isinstance(call_args[0][0], SchemaFinishedEvent)
        event = call_args[0][0]
        assert event.payload.schema_id == "schema-id"
        assert event.payload.issuer_id == "issuer-id"
        assert event.payload.name == "test-schema"
        assert event.payload.version == "1.0"
        assert event.payload.attr_names == ["attr1", "attr2"]

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    async def test_get_created_schemas(self, mock_session_handle):
        mock_session_handle.fetch_all = mock.CoroutineMock(
            return_value=[MockSchemaEntry("name-test")]
        )
        result = await self.issuer.get_created_schemas()
        mock_session_handle.fetch_all.assert_called_once()
        assert result == ["name-test"]

        mock_session_handle.fetch_all = mock.CoroutineMock(
            return_value=[
                MockSchemaEntry("schema1"),
                MockSchemaEntry("schema2"),
            ]
        )
        result = await self.issuer.get_created_schemas()
        mock_session_handle.fetch_all.assert_called_once()
        assert result == ["schema1", "schema2"]

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    async def test_credential_definition_in_wallet(self, mock_session_handle):
        mock_session_handle.fetch = mock.CoroutineMock(
            side_effect=[
                CredDef(
                    issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                    schema_id="schema-id",
                    tag="tag",
                    type="CL",
                    value=CredDefValue(
                        primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")
                    ),
                ),
                None,
                AskarError(AskarErrorCode.UNEXPECTED, message="test-msg"),
            ]
        )
        assert await self.issuer.credential_definition_in_wallet("cred-def-id") is True
        assert await self.issuer.credential_definition_in_wallet("cred-def-id") is False
        with self.assertRaises(test_module.AnonCredsIssuerError):
            await self.issuer.credential_definition_in_wallet("cred-def-id")

    async def test_create_and_register_credential_definition_invalid_options_raises_x(
        self,
    ):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_schema=mock.CoroutineMock(
                    return_value=AnonCredsSchema(
                        issuer_id="issuer-id",
                        name="schema-name",
                        version="1.0",
                        attr_names=["attr1", "attr2"],
                    )
                )
            )
        )
        with self.assertRaises(ValueError):
            await self.issuer.create_and_register_credential_definition(
                issuer_id="issuer-id",
                schema_id="schema-id",
                signature_type="CL",
                options={"support_revocation": "true"},  # requires boolean
            )
        with self.assertRaises(ValueError):
            await self.issuer.create_and_register_credential_definition(
                issuer_id="issuer-id",
                schema_id="schema-id",
                signature_type="CL",
                options={"revocation_registry_size": "100"},  # requires integer
            )

    @mock.patch.object(CredDef, "from_native", return_value=MockCredDefEntry())
    @mock.patch(
        "anoncreds.CredentialDefinition.create",
        return_value=(mock.MagicMock(), mock.MagicMock(), mock.MagicMock()),
    )
    async def test_create_and_register_credential_definition_support_revocation_conditions(
        self, mock_cred_def_create, _
    ):
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
                    issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
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

        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_schema=mock.CoroutineMock(return_value=schema_result),
                register_credential_definition=mock.CoroutineMock(
                    return_value=cred_def_result
                ),
            )
        )

        # Configure author role and auto create rev reg -- expectation: support revocation is True when not specified
        self.profile.settings.set_value("endorser.author", True)
        self.profile.settings.set_value("endorser.auto_create_rev_reg", True)

        # First assert AnonCredsIssuerError if tails_server_base_url is not set
        with self.assertRaises(test_module.AnonCredsIssuerError) as exc:
            await self.issuer.create_and_register_credential_definition(
                issuer_id="issuer-id",
                schema_id="schema-id",
                signature_type="CL",
                tag="tag",
            )
        assert (
            str(exc.exception.message)
            == "tails_server_base_url not configured. Can't create revocable credential definition."
        )

        # Now, set the tails_server_base_url
        self.profile.settings.set_value("tails_server_base_url", "https://example.com")

        for support_revocation in [True, False, None]:
            # Mock the store_credential_definition method
            with mock.patch.object(
                self.issuer, "store_credential_definition"
            ) as mock_store_cred_def:
                # Reset the mocks for each iteration
                mock_cred_def_create.reset_mock()
                mock_store_cred_def.reset_mock()

                await self.issuer.create_and_register_credential_definition(
                    issuer_id="issuer-id",
                    schema_id="schema-id",
                    signature_type="CL",
                    tag="tag",
                    options={"support_revocation": support_revocation},
                )

                # Check if support_revocation is True when None or True was passed
                expected_support_revocation = (
                    support_revocation if support_revocation is not None else True
                )

                # Assert CredentialDefinition.create call was made with correct support_revocation value
                mock_cred_def_create.assert_called_once_with(
                    schema_id="schema-id",
                    schema=schema_result.schema.serialize(),
                    issuer_id="issuer-id",
                    tag="tag",
                    signature_type="CL",
                    support_revocation=expected_support_revocation,
                )

                # Assert store_credential_definition call args
                mock_store_cred_def.assert_called_once_with(
                    schema_result=schema_result,
                    cred_def_result=mock.ANY,
                    cred_def_private=mock.ANY,
                    key_proof=mock.ANY,
                    support_revocation=expected_support_revocation,
                    max_cred_num=mock.ANY,
                    options=mock.ANY,
                )

        # Now, disable author role and auto create rev reg -- expectation: support revocation is False when not specified
        self.profile.settings.set_value("endorser.author", False)
        self.profile.settings.set_value("endorser.auto_create_rev_reg", False)

        for support_revocation in [True, False, None]:
            # Mock the CredentialDefinition.create call, and the store_credential_definition method
            with mock.patch.object(
                self.issuer, "store_credential_definition"
            ) as mock_store_cred_def:
                # Reset the mock for each iteration
                mock_cred_def_create.reset_mock()
                mock_store_cred_def.reset_mock()

                await self.issuer.create_and_register_credential_definition(
                    issuer_id="issuer-id",
                    schema_id="schema-id",
                    signature_type="CL",
                    tag="tag",
                    options={"support_revocation": support_revocation},
                )

                # Check if support_revocation is False when set to None
                expected_support_revocation = (
                    support_revocation if support_revocation is not None else False
                )

                # Assert CredentialDefinition.create call was made with correct support_revocation value
                mock_cred_def_create.assert_called_once_with(
                    schema_id="schema-id",
                    schema=schema_result.schema.serialize(),
                    issuer_id="issuer-id",
                    tag="tag",
                    signature_type="CL",
                    support_revocation=expected_support_revocation,
                )

                # Assert store_credential_definition call args
                mock_store_cred_def.assert_called_once_with(
                    schema_result=schema_result,
                    cred_def_result=mock.ANY,
                    cred_def_private=mock.ANY,
                    key_proof=mock.ANY,
                    support_revocation=expected_support_revocation,
                    max_cred_num=mock.ANY,
                    options=mock.ANY,
                )

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_create_and_register_credential_definition_finishes(self, mock_notify):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_schema=mock.CoroutineMock(
                    return_value=GetSchemaResult(
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
                ),
                register_credential_definition=mock.CoroutineMock(
                    return_value=CredDefResult(
                        job_id="job-id",
                        credential_definition_state=CredDefState(
                            state="finished",
                            credential_definition=CredDef(
                                issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                                schema_id="schema-id",
                                tag="tag",
                                type="CL",
                                value=CredDefValue(
                                    primary=CredDefValuePrimary(
                                        "n", "s", {}, "rctxt", "z"
                                    )
                                ),
                            ),
                            credential_definition_id="cred-def-id",
                        ),
                        credential_definition_metadata={},
                        registration_metadata={},
                    )
                ),
            )
        )
        self.profile.transaction = mock.Mock(
            return_value=mock.MagicMock(
                insert=mock.CoroutineMock(return_value=None),
                commit=mock.CoroutineMock(return_value=None),
            )
        )
        result = await self.issuer.create_and_register_credential_definition(
            issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
            schema_id="CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
            signature_type="CL",
            options={},
        )

        assert isinstance(result, CredDefResult)
        mock_notify.assert_called_once()

    @mock.patch.object(test_module.AnonCredsIssuer, "notify")
    async def test_create_and_register_credential_definition_errors(self, mock_notify):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_schema=mock.CoroutineMock(
                    return_value=GetSchemaResult(
                        schema_id="schema-id",
                        schema=AnonCredsSchema(
                            issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                            name="schema-name",
                            version="1.0",
                            attr_names=["attr1", "attr2"],
                        ),
                        schema_metadata={},
                        resolution_metadata={},
                    )
                ),
                # No job_id or cred_def_id
                register_credential_definition=mock.CoroutineMock(
                    side_effect=[
                        CredDefResult(
                            job_id=None,
                            credential_definition_state=CredDefState(
                                state="finished",
                                credential_definition=CredDef(
                                    issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                                    schema_id="schema-id",
                                    tag="tag",
                                    type="CL",
                                    value=CredDefValue(
                                        primary=CredDefValuePrimary(
                                            "n", "s", {}, "rctxt", "z"
                                        )
                                    ),
                                ),
                                credential_definition_id=None,
                            ),
                            credential_definition_metadata={},
                            registration_metadata={},
                        ),
                    ]
                ),
            )
        )
        self.profile.transaction = mock.Mock(
            return_value=mock.MagicMock(
                insert=mock.CoroutineMock(return_value=None),
                commit=mock.CoroutineMock(return_value=None),
            )
        )
        # Creating fails with bad issuer_id
        with self.assertRaises(AnoncredsError):
            await self.issuer.create_and_register_credential_definition(
                issuer_id="issuer-id",
                schema_id="CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
                signature_type="CL",
                options={},
            )
        # No job_id or cred_def_id
        with self.assertRaises(test_module.AnonCredsIssuerError):
            await self.issuer.create_and_register_credential_definition(
                issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                schema_id="CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
                signature_type="CL",
                options={},
            )

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    async def test_get_created_cred_defs(self, mock_session_handle):
        mock_session_handle.fetch_all = mock.CoroutineMock(
            return_value=[MockCredDefEntry()]
        )
        result = await self.issuer.get_created_credential_definitions()
        mock_session_handle.fetch_all.assert_called_once()
        assert result == ["name"]
        mock_session_handle.fetch_all = mock.CoroutineMock(
            return_value=[MockCredDefEntry("cred_def1"), MockCredDefEntry("cred_def2")]
        )
        result = await self.issuer.get_created_credential_definitions(
            issuer_id="issuer-id-test",
            schema_issuer_id="schema-issuer-id-test",
            schema_id="schema-id-test",
            schema_name="schema-name-test",
            schema_version="schema-version-test",
            epoch="123456789",
        )
        mock_session_handle.fetch_all.assert_called_once()
        assert result == ["cred_def1", "cred_def2"]

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    async def test_match_created_cred_defs(self, mock_session_handle):
        mock_session_handle.fetch_all = mock.CoroutineMock(
            return_value=[
                MockCredDefEntry(name="name2", epoch="2"),
                MockCredDefEntry(name="name3", epoch="3"),
                MockCredDefEntry(name="name4", epoch="4"),
                MockCredDefEntry(name="name1", epoch="1"),
            ]
        )
        result = await self.issuer.match_created_credential_definitions()
        assert result == "name4"

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    async def test_create_credential_offer_cred_def_not_found(self, mock_session_handle):
        """
        None, Valid
        Valid, None
        None, None
        """
        mock_session_handle.fetch = mock.CoroutineMock(
            side_effect=[None, MockKeyProof(), MockCredDefEntry(), None, None, None]
        )
        with self.assertRaises(test_module.AnonCredsIssuerError):
            await self.issuer.create_credential_offer("cred-def-id")
        with self.assertRaises(test_module.AnonCredsIssuerError):
            await self.issuer.create_credential_offer("cred-def-id")
        with self.assertRaises(test_module.AnonCredsIssuerError):
            await self.issuer.create_credential_offer("cred-def-id")

    async def test_cred_def_supports_revocation(self):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    side_effect=[
                        GetCredDefResult(
                            credential_definition_id="cred-def-id",
                            credential_definition=CredDef(
                                issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                                schema_id="schema-id",
                                tag="tag",
                                type="CL",
                                value=CredDefValue(
                                    primary=CredDefValuePrimary(
                                        "n", "s", {}, "rctxt", "z"
                                    )
                                ),
                            ),
                            credential_definition_metadata={},
                            resolution_metadata={},
                        ),
                        GetCredDefResult(
                            credential_definition_id="cred-def-id",
                            credential_definition=CredDef(
                                issuer_id="did:sov:3avoBCqDMFHFaKUHug9s8W",
                                schema_id="schema-id",
                                tag="tag",
                                type="CL",
                                value=CredDefValue(
                                    primary=CredDefValuePrimary(
                                        "n", "s", {}, "rctxt", "z"
                                    ),
                                    revocation=CredDefValueRevocation(
                                        g="g",
                                        g_dash="g_dash",
                                        h="h",
                                        h0="h0",
                                        h1="h1",
                                        h2="h2",
                                        h_cap="h_cap",
                                        htilde="htilde",
                                        pk="pk",
                                        u="u",
                                        y="y",
                                    ),
                                ),
                            ),
                            credential_definition_metadata={},
                            resolution_metadata={},
                        ),
                    ]
                )
            )
        )

        result = await self.issuer.cred_def_supports_revocation("cred-def-id")
        assert result is False
        result = await self.issuer.cred_def_supports_revocation("cred-def-id")
        assert result is True

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    @mock.patch.object(CredentialDefinition, "load", return_value=MockCredDefEntry())
    async def test_create_credential_offer_create_fail(
        self, mock_load, mock_session_handle
    ):
        mock_session_handle.fetch = mock.CoroutineMock(
            side_effect=[MockCredDefEntry(), MockKeyProof()]
        )
        with self.assertRaises(test_module.AnonCredsIssuerError):
            await self.issuer.create_credential_offer("cred-def-id")
        assert mock_session_handle.fetch.called
        assert mock_load.called

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    @mock.patch.object(CredentialDefinition, "load", return_value=MockCredDefEntry())
    @mock.patch.object(CredentialOffer, "create", return_value=MockCredOffer())
    async def test_create_credential_offer_create(
        self, mock_create, mock_load, mock_session_handle
    ):
        mock_session_handle.fetch = mock.CoroutineMock(
            side_effect=[MockCredDefEntry(), MockKeyProof()]
        )
        result = await self.issuer.create_credential_offer("cred-def-id")
        assert mock_session_handle.fetch.called
        assert mock_load.called
        assert mock_create.called
        assert result is not None

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    @mock.patch.object(Credential, "create", return_value=MockCredential())
    async def test_create_credential(self, mock_create, mock_session_handle):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_schema=mock.CoroutineMock(return_value=MockSchemaResult())
            )
        )
        mock_session_handle.fetch = mock.CoroutineMock(return_value=MockCredDefEntry())
        result = await self.issuer.create_credential(
            {"schema_id": "schema-id", "cred_def_id": "cred-def-id"},
            {},
            {"attr1": "value1", "attr2": "value2"},
        )

        assert result is not None
        assert mock_session_handle.fetch.called
        assert mock_create.called

    @mock.patch.object(AskarAnonCredsProfileSession, "handle")
    @mock.patch.object(W3cCredential, "create", return_value=MockCredential())
    async def test_create_credential_vcdi(self, mock_create, mock_session_handle):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_schema=mock.CoroutineMock(return_value=MockSchemaResult()),
            )
        )

        mock_session_handle.fetch = mock.CoroutineMock(return_value=MockCredDefEntry())
        result = await self.issuer.create_credential_w3c(
            {"schema_id": "schema-id", "cred_def_id": "cred-def-id"},
            {},
            {"attr1": "value1", "attr2": "value2"},
        )

        assert result is not None
        assert mock_session_handle.fetch.called
        assert mock_create.called
