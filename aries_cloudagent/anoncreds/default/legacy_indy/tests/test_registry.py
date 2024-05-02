"""Test LegacyIndyRegistry."""

import json
import re
from unittest import IsolatedAsyncioTestCase

import pytest
from anoncreds import Schema
from base58 import alphabet

from .....anoncreds.base import (
    AnonCredsRegistrationError,
    AnonCredsSchemaAlreadyExists,
)
from .....anoncreds.models.anoncreds_schema import (
    AnonCredsSchema,
    GetSchemaResult,
    SchemaResult,
)
from .....askar.profile_anon import AskarAnoncredsProfile
from .....connections.models.conn_record import ConnRecord
from .....core.in_memory.profile import InMemoryProfile
from .....ledger.base import BaseLedger
from .....ledger.error import LedgerError, LedgerObjectAlreadyExistsError
from .....messaging.responder import BaseResponder
from .....protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
)
from .....protocols.endorse_transaction.v1_0.models.transaction_record import (
    TransactionRecord,
)
from .....tests import mock
from ....issuer import AnonCredsIssuer
from ....models.anoncreds_cred_def import (
    CredDef,
    CredDefResult,
    CredDefValue,
    CredDefValuePrimary,
)
from ....models.anoncreds_revocation import (
    RevList,
    RevListResult,
    RevRegDef,
    RevRegDefResult,
    RevRegDefValue,
)
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
class TestLegacyIndyRegistry(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet.type": "askar-anoncreds"},
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

    @mock.patch.object(
        AnonCredsIssuer, "credential_definition_in_wallet", return_value=False
    )
    async def test_register_credential_definition_no_endorsement(self, mock_in_wallet):
        schema = Schema.create(
            name="MYCO Biomarker",
            version="1.0",
            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
            attr_names=["attr1", "attr2"],
        )

        schema_result = GetSchemaResult(
            schema_id="schema-id",
            schema=schema,
            schema_metadata={
                "seqNo": 1,
            },
            resolution_metadata={},
        )

        cred_def = CredDef(
            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
            schema_id="CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
            tag="default",
            type="CL",
            value=CredDefValue(primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")),
        )

        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(
                send_credential_definition_anoncreds=mock.CoroutineMock(return_value=2)
            ),
        )

        result = await self.registry.register_credential_definition(
            self.profile, schema_result, cred_def, {}
        )

        assert isinstance(result, CredDefResult)
        assert mock_in_wallet.called

    @mock.patch.object(
        AnonCredsIssuer, "credential_definition_in_wallet", return_value=False
    )
    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    @mock.patch.object(
        TransactionManager,
        "create_record",
        return_value=TransactionRecord(),
    )
    async def test_register_credential_definition_with_author_role(
        self, mock_create_record, mock_get_endorser_info, mock_in_wallet
    ):
        schema = Schema.create(
            name="MYCO Biomarker",
            version="1.0",
            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
            attr_names=["attr1", "attr2"],
        )

        schema_result = GetSchemaResult(
            schema_id="schema-id",
            schema=schema,
            schema_metadata={
                "seqNo": 1,
            },
            resolution_metadata={},
        )

        cred_def = CredDef(
            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
            schema_id="CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
            tag="default",
            type="CL",
            value=CredDefValue(primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")),
        )

        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(
                send_credential_definition_anoncreds=mock.CoroutineMock(
                    return_value=("id", {"signed_txn": "txn"})
                )
            ),
        )
        self.profile.settings.set_value("endorser.author", True)

        result = await self.registry.register_credential_definition(
            self.profile,
            schema_result,
            cred_def,
            {"endorser_connection_id": "test_connection_id"},
        )

        assert isinstance(result, CredDefResult)
        assert result.job_id is not None
        assert mock_in_wallet.called
        assert mock_get_endorser_info.called
        assert mock_create_record.called

    @mock.patch.object(
        AnonCredsIssuer, "credential_definition_in_wallet", return_value=False
    )
    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    @mock.patch.object(
        TransactionManager,
        "create_record",
        return_value=TransactionRecord(),
    )
    async def test_register_credential_definition_with_create_transaction_option(
        self, mock_create_record, mock_get_endorser_info, mock_in_wallet
    ):
        schema = Schema.create(
            name="MYCO Biomarker",
            version="1.0",
            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
            attr_names=["attr1", "attr2"],
        )

        schema_result = GetSchemaResult(
            schema_id="schema-id",
            schema=schema,
            schema_metadata={
                "seqNo": 1,
            },
            resolution_metadata={},
        )

        cred_def = CredDef(
            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
            schema_id="CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
            tag="default",
            type="CL",
            value=CredDefValue(primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")),
        )

        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(
                send_credential_definition_anoncreds=mock.CoroutineMock(
                    return_value=("id", {"signed_txn": "txn"})
                )
            ),
        )

        result = await self.registry.register_credential_definition(
            self.profile,
            schema_result,
            cred_def,
            {
                "endorser_connection_id": "test_connection_id",
                "create_transaction_for_endorser": True,
            },
        )

        assert isinstance(result, CredDefResult)
        assert result.job_id is not None
        assert mock_in_wallet.called
        assert mock_get_endorser_info.called
        assert mock_create_record.called

    @mock.patch.object(
        AnonCredsIssuer, "credential_definition_in_wallet", return_value=False
    )
    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    @mock.patch.object(
        TransactionManager,
        "create_record",
        return_value=TransactionRecord(),
    )
    @mock.patch.object(
        TransactionManager,
        "create_request",
        return_value=(TransactionRecord(), "transaction_request"),
    )
    async def test_register_credential_definition_with_transaction_and_auto_request(
        self,
        mock_create_request,
        mock_create_record,
        mock_get_endorser_info,
        mock_in_wallet,
    ):
        schema = Schema.create(
            name="MYCO Biomarker",
            version="1.0",
            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
            attr_names=["attr1", "attr2"],
        )

        schema_result = GetSchemaResult(
            schema_id="schema-id",
            schema=schema,
            schema_metadata={
                "seqNo": 1,
            },
            resolution_metadata={},
        )

        cred_def = CredDef(
            issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
            schema_id="CsQY9MGeD3CQP4EyuVFo5m:2:MYCO Biomarker:0.0.3",
            tag="default",
            type="CL",
            value=CredDefValue(primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")),
        )

        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(
                send_credential_definition_anoncreds=mock.CoroutineMock(
                    return_value=("id", {"signed_txn": "txn"})
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            BaseResponder,
            mock.MagicMock(send=mock.CoroutineMock(return_value=None)),
        )
        self.profile.settings.set_value("endorser.auto_request", True)

        result = await self.registry.register_credential_definition(
            self.profile,
            schema_result,
            cred_def,
            {
                "endorser_connection_id": "test_connection_id",
                "create_transaction_for_endorser": True,
            },
        )

        assert isinstance(result, CredDefResult)
        assert result.job_id is not None
        assert mock_in_wallet.called
        assert mock_get_endorser_info.called
        assert mock_create_record.called
        assert mock_create_request.called
        assert self.profile.context.injector.get_provider(
            BaseResponder
        )._instance.send.called

    async def test_register_revocation_registry_definition_no_endorsement(self):
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(send_revoc_reg_def=mock.CoroutineMock(return_value=1)),
        )
        result = await self.registry.register_revocation_registry_definition(
            self.profile,
            RevRegDef(
                tag="tag",
                cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                value=RevRegDefValue(
                    max_cred_num=100,
                    public_keys={
                        "accum_key": {"z": "1 0BB...386"},
                    },
                    tails_hash="not-correct-hash",
                    tails_location="http://tails-server.com",
                ),
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                type="CL_ACCUM",
            ),
            {},
        )

        assert isinstance(result, RevRegDefResult)
        assert self.profile.context.injector.get_provider(
            BaseLedger
        )._instance.send_revoc_reg_def.called

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    @mock.patch.object(
        TransactionManager,
        "create_record",
        return_value=TransactionRecord(),
    )
    @mock.patch.object(
        TransactionManager,
        "create_request",
        return_value=(TransactionRecord(), "transaction_request"),
    )
    async def test_register_revocation_registry_definition_with_author_role(
        self, mock_create_request, mock_create_record, mock_endorser_connection
    ):
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(send_revoc_reg_def=mock.CoroutineMock(return_value=1)),
        )
        self.profile.settings.set_value("endorser.author", True)
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(
                send_revoc_reg_def=mock.CoroutineMock(
                    return_value=("id", {"signed_txn": "txn"})
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            BaseResponder,
            mock.MagicMock(send=mock.CoroutineMock(return_value=None)),
        )

        self.profile.settings.set_value("endorser.auto_request", True)

        result = await self.registry.register_revocation_registry_definition(
            self.profile,
            RevRegDef(
                tag="tag",
                cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                value=RevRegDefValue(
                    max_cred_num=100,
                    public_keys={
                        "accum_key": {"z": "1 0BB...386"},
                    },
                    tails_hash="not-correct-hash",
                    tails_location="http://tails-server.com",
                ),
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                type="CL_ACCUM",
            ),
            {
                "endorser_connection_id": "test_connection_id",
            },
        )

        assert isinstance(result, RevRegDefResult)
        assert self.profile.context.injector.get_provider(
            BaseLedger
        )._instance.send_revoc_reg_def.called
        assert mock_create_record.called
        assert mock_create_request.called
        assert self.profile.context.injector.get_provider(
            BaseResponder
        )._instance.send.called

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    @mock.patch.object(
        TransactionManager,
        "create_record",
        return_value=TransactionRecord(),
    )
    async def test_register_revocation_registry_definition_with_create_transaction_option(
        self, mock_create_record, mock_endorser_connection
    ):
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(send_revoc_reg_def=mock.CoroutineMock(return_value=1)),
        )
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(
                send_revoc_reg_def=mock.CoroutineMock(
                    return_value=("id", {"signed_txn": "txn"})
                )
            ),
        )

        result = await self.registry.register_revocation_registry_definition(
            self.profile,
            RevRegDef(
                tag="tag",
                cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                value=RevRegDefValue(
                    max_cred_num=100,
                    public_keys={
                        "accum_key": {"z": "1 0BB...386"},
                    },
                    tails_hash="not-correct-hash",
                    tails_location="http://tails-server.com",
                ),
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                type="CL_ACCUM",
            ),
            {
                "endorser_connection_id": "test_connection_id",
                "create_transaction_for_endorser": True,
            },
        )

        assert isinstance(result, RevRegDefResult)
        assert self.profile.context.injector.get_provider(
            BaseLedger
        )._instance.send_revoc_reg_def.called
        assert mock_create_record.called

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    @mock.patch.object(
        TransactionManager,
        "create_record",
        return_value=TransactionRecord(),
    )
    async def test_register_revocation_registry_definition_with_create_transaction_and_auto_request(
        self, mock_create_record, mock_endorser_connection
    ):
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(
                send_revoc_reg_def=mock.CoroutineMock(
                    return_value=("id", {"signed_txn": "txn"})
                )
            ),
        )

        result = await self.registry.register_revocation_registry_definition(
            self.profile,
            RevRegDef(
                tag="tag",
                cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                value=RevRegDefValue(
                    max_cred_num=100,
                    public_keys={
                        "accum_key": {"z": "1 0BB...386"},
                    },
                    tails_hash="not-correct-hash",
                    tails_location="http://tails-server.com",
                ),
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                type="CL_ACCUM",
            ),
            {
                "endorser_connection_id": "test_connection_id",
                "create_transaction_for_endorser": True,
            },
        )

        assert isinstance(result, RevRegDefResult)
        assert self.profile.context.injector.get_provider(
            BaseLedger
        )._instance.send_revoc_reg_def.called
        assert mock_create_record.called

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

    async def test_register_revocation_list_no_endorsement(self):
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(send_revoc_reg_entry=mock.CoroutineMock(return_value=1)),
        )
        result = await self.registry.register_revocation_list(
            self.profile,
            RevRegDef(
                tag="tag",
                cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                value=RevRegDefValue(
                    max_cred_num=100,
                    public_keys={
                        "accum_key": {"z": "1 0BB...386"},
                    },
                    tails_hash="not-correct-hash",
                    tails_location="http://tails-server.com",
                ),
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                type="CL_ACCUM",
            ),
            RevList(
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                revocation_list=[0, 1, 1, 0],
                timestamp=1669640864487,
                rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            ),
            {},
        )

        assert isinstance(result, RevListResult)
        assert self.profile.context.injector.get_provider(
            BaseLedger
        )._instance.send_revoc_reg_entry.called

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    @mock.patch.object(
        TransactionManager,
        "create_record",
        return_value=TransactionRecord(),
    )
    async def test_register_revocation_list_with_author_role(
        self, mock_create_record, mock_endorsement_conn
    ):
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(
                send_revoc_reg_entry=mock.CoroutineMock(
                    return_value=("id", {"signed_txn": "txn"})
                )
            ),
        )
        self.profile.settings.set_value("endorser.author", True)

        result = await self.registry.register_revocation_list(
            self.profile,
            RevRegDef(
                tag="tag",
                cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                value=RevRegDefValue(
                    max_cred_num=100,
                    public_keys={
                        "accum_key": {"z": "1 0BB...386"},
                    },
                    tails_hash="not-correct-hash",
                    tails_location="http://tails-server.com",
                ),
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                type="CL_ACCUM",
            ),
            RevList(
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                revocation_list=[0, 1, 1, 0],
                timestamp=1669640864487,
                rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            ),
            {
                "endorser_connection_id": "test_connection_id",
            },
        )

        assert isinstance(result, RevListResult)
        assert self.profile.context.injector.get_provider(
            BaseLedger
        )._instance.send_revoc_reg_entry.called
        assert mock_create_record.called

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    @mock.patch.object(
        TransactionManager,
        "create_record",
        return_value=TransactionRecord(),
    )
    async def test_register_revocation_list_with_create_transaction_option(
        self, mock_create_record, mock_endorsement_conn
    ):
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(
                send_revoc_reg_entry=mock.CoroutineMock(
                    return_value=("id", {"signed_txn": "txn"})
                )
            ),
        )

        result = await self.registry.register_revocation_list(
            self.profile,
            RevRegDef(
                tag="tag",
                cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                value=RevRegDefValue(
                    max_cred_num=100,
                    public_keys={
                        "accum_key": {"z": "1 0BB...386"},
                    },
                    tails_hash="not-correct-hash",
                    tails_location="http://tails-server.com",
                ),
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                type="CL_ACCUM",
            ),
            RevList(
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                revocation_list=[0, 1, 1, 0],
                timestamp=1669640864487,
                rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            ),
            {
                "endorser_connection_id": "test_connection_id",
                "create_transaction_for_endorser": True,
            },
        )

        assert isinstance(result, RevListResult)
        assert self.profile.context.injector.get_provider(
            BaseLedger
        )._instance.send_revoc_reg_entry.called
        assert mock_create_record.called

    @mock.patch.object(
        ConnRecord,
        "retrieve_by_id",
        return_value=mock.CoroutineMock(
            metadata_get=mock.CoroutineMock(return_value={"endorser_did": "test_did"})
        ),
    )
    @mock.patch.object(
        TransactionManager,
        "create_record",
        return_value=TransactionRecord(),
    )
    @mock.patch.object(
        TransactionManager,
        "create_request",
        return_value=(TransactionRecord(), "transaction_request"),
    )
    async def test_register_revocation_list_with_create_transaction_option_and_auto_request(
        self, mock_create_request, mock_create_record, mock_endorsement_conn
    ):
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock.MagicMock(
                send_revoc_reg_entry=mock.CoroutineMock(
                    return_value=("id", {"signed_txn": "txn"})
                )
            ),
        )
        self.profile.context.injector.bind_instance(
            BaseResponder,
            mock.MagicMock(send=mock.CoroutineMock(return_value=None)),
        )
        self.profile.settings.set_value("endorser.auto_request", True)

        result = await self.registry.register_revocation_list(
            self.profile,
            RevRegDef(
                tag="tag",
                cred_def_id="CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
                value=RevRegDefValue(
                    max_cred_num=100,
                    public_keys={
                        "accum_key": {"z": "1 0BB...386"},
                    },
                    tails_hash="not-correct-hash",
                    tails_location="http://tails-server.com",
                ),
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                type="CL_ACCUM",
            ),
            RevList(
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                revocation_list=[0, 1, 1, 0],
                timestamp=1669640864487,
                rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            ),
            {
                "endorser_connection_id": "test_connection_id",
                "create_transaction_for_endorser": True,
            },
        )

        assert isinstance(result, RevListResult)
        assert self.profile.context.injector.get_provider(
            BaseLedger
        )._instance.send_revoc_reg_entry.called
        assert mock_create_record.called
        assert mock_create_request.called
        assert self.profile.context.injector.get_provider(
            BaseResponder
        )._instance.send.called
