"""Test LegacyIndyRegistry."""

import json
import re

import pytest
from asynctest import TestCase
from base58 import alphabet

from aries_cloudagent.anoncreds.base import (
    AnonCredsRegistrationError,
    AnonCredsSchemaAlreadyExists,
)
from aries_cloudagent.anoncreds.models.anoncreds_schema import (
    AnonCredsSchema,
    SchemaResult,
)
from aries_cloudagent.askar.profile_anon import AskarAnoncredsProfile
from aries_cloudagent.connections.models.conn_record import ConnRecord
from aries_cloudagent.core.in_memory.profile import InMemoryProfile
from aries_cloudagent.ledger.error import LedgerError, LedgerObjectAlreadyExistsError
from aries_cloudagent.messaging.responder import BaseResponder
from aries_cloudagent.protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
)
from aries_cloudagent.tests import mock

from .. import registry as test_module

B58 = alphabet if isinstance(alphabet, str) else alphabet.decode("ascii")
INDY_DID = rf"^(did:sov:)?[{B58}]{{21,22}}$"
INDY_SCHEMA_ID = rf"^[{B58}]{{21,22}}:2:.+:[0-9.]+$"
INDY_CRED_DEF_ID = (
    rf"^([{B58}]{{21,22}})"  # issuer DID
    f":3"  # cred def id marker
    f":CL"  # sig alg
    rf":(([1-9][0-9]*)|([{B58}]{{21,22}}:2:.+:[0-9.]+))"  # schema txn / id
    f":(.+)?$"  # tag
)
INDY_REV_REG_DEF_ID = (
    rf"^([{B58}]{{21,22}}):4:"
    rf"([{B58}]{{21,22}}):3:"
    rf"CL:(([1-9][0-9]*)|([{B58}]{{21,22}}:2:.+:[0-9.]+))(:.+)?:"
    rf"CL_ACCUM:(.+$)"
)
SUPPORTED_ID_REGEX = re.compile(
    rf"{INDY_DID}|{INDY_SCHEMA_ID}|{INDY_CRED_DEF_ID}|{INDY_REV_REG_DEF_ID}"
)

TEST_INDY_DID = "WgWxqztrNooG92RXvxSTWv"
TEST_INDY_DID_1 = "did:sov:WgWxqztrNooG92RXvxSTWv"
TEST_INDY_SCHEMA_ID = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
TEST_INDY_CRED_DEF_ID = "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"
TEST_INDY_REV_REG_DEF_ID = (
    "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0"
)

mock_schema = AnonCredsSchema(
    issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
    attr_names=["name", "age", "vmax"],
    name="test_schema",
    version="1.0",
)


@pytest.mark.anoncreds
class TestLegacyIndyRegistry(TestCase):
    def setUp(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet-type": "askar-anoncreds"},
            profile_class=AskarAnoncredsProfile,
        )
        self.registry = test_module.LegacyIndyRegistry()

    async def test_supported_did_regex(self):
        """Test the supported_did_regex."""

        assert self.registry.supported_identifiers_regex == SUPPORTED_ID_REGEX
        assert bool(self.registry.supported_identifiers_regex.match(TEST_INDY_DID))
        assert bool(self.registry.supported_identifiers_regex.match(TEST_INDY_DID_1))
        assert bool(
            self.registry.supported_identifiers_regex.match(TEST_INDY_SCHEMA_ID)
        )
        assert bool(
            self.registry.supported_identifiers_regex.match(TEST_INDY_REV_REG_DEF_ID)
        )

    async def test_register_schema_no_endorsement(self):
        self.profile.inject_or = mock.MagicMock(
            return_value=mock.CoroutineMock(
                send_schema_anoncreds=mock.CoroutineMock(return_value=1)
            )
        )

        result = await self.registry.register_schema(self.profile, mock_schema, {})

        assert isinstance(result, SchemaResult)

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    async def test_register_schema_with_author_role(self, mock_endorser_conn_record):
        self.profile.inject_or = mock.MagicMock(
            return_value=mock.CoroutineMock(
                send_schema_anoncreds=mock.CoroutineMock(
                    return_value=(
                        "test_schema_id",
                        {
                            "signed_txn": "test_signed_txn",
                        },
                    )
                )
            )
        )
        self.profile.settings.set_value("endorser.author", True)

        result = await self.registry.register_schema(
            self.profile, mock_schema, {"endorser_connection_id": "test_connection_id"}
        )

        assert result.registration_metadata["txn"] is not None
        assert mock_endorser_conn_record.called

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    async def test_register_schema_already_exists(self, mock_endorser_conn_record):
        self.profile.inject_or = mock.MagicMock(
            return_value=mock.CoroutineMock(
                send_schema_anoncreds=mock.CoroutineMock(
                    side_effect=LedgerObjectAlreadyExistsError(
                        "test", "test", mock_schema
                    )
                )
            )
        )
        self.profile.settings.set_value("endorser.author", True)

        with self.assertRaises(AnonCredsSchemaAlreadyExists):
            await self.registry.register_schema(
                self.profile,
                mock_schema,
                {"endorser_connection_id": "test_connection_id"},
            )

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    async def test_register_schema_with_create_trasaction_param(
        self, mock_endorser_conn_record
    ):
        self.profile.inject_or = mock.MagicMock(
            return_value=mock.CoroutineMock(
                send_schema_anoncreds=mock.CoroutineMock(
                    return_value=(
                        "test_schema_id",
                        {
                            "signed_txn": "test_signed_txn",
                        },
                    )
                )
            )
        )

        result = await self.registry.register_schema(
            self.profile,
            mock_schema,
            {
                "endorser_connection_id": "test_connection_id",
                "create_transaction_for_endorser": True,
            },
        )

        assert result.registration_metadata["txn"] is not None
        assert mock_endorser_conn_record.called

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    @mock.patch.object(
        TransactionManager,
        "create_request",
    )
    async def test_register_schema_with_author_role_and_create_request(
        self, mock_create_request, mock_endorser_conn_record
    ):
        class MockTransaction:
            def __init__(self, txn):
                self.txn = txn

            def serialize(self):
                return json.dumps(self.txn)

        self.profile.inject_or = mock.MagicMock(
            return_value=mock.CoroutineMock(
                send_schema_anoncreds=mock.CoroutineMock(
                    return_value=(
                        "test_schema_id",
                        {
                            "signed_txn": "test_signed_txn",
                        },
                    )
                )
            )
        )

        mock_create_request.return_value = (
            MockTransaction({"test": "test"}),
            "transaction_request",
        )

        self.profile.settings.set_value("endorser.author", True)
        self.profile.settings.set_value("endorser.auto_request", True)
        self.profile.context.injector.bind_instance(
            BaseResponder, mock.MagicMock(send=mock.CoroutineMock(return_value=None))
        )

        result = await self.registry.register_schema(
            self.profile, mock_schema, {"endorser_connection_id": "test_connection_id"}
        )

        assert result.registration_metadata["txn"] is not None
        assert mock_create_request.called
        assert self.profile.context.injector.get_provider(
            BaseResponder
        )._instance.send.called

    async def test_txn_submit(self):
        self.profile.inject = mock.MagicMock(
            side_effect=[
                None,
                mock.CoroutineMock(
                    txn_submit=mock.CoroutineMock(side_effect=LedgerError("test error"))
                ),
                mock.CoroutineMock(
                    txn_submit=mock.CoroutineMock(return_value="transaction response")
                ),
            ]
        )

        # No ledger
        with self.assertRaises(LedgerError):
            await self.registry.txn_submit(self.profile, "test_txn")
        # Write error
        with self.assertRaises(AnonCredsRegistrationError):
            await self.registry.txn_submit(self.profile, "test_txn")

        result = await self.registry.txn_submit(self.profile, "test_txn")
        assert result == "transaction response"
