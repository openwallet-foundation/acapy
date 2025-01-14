"""Test LegacyIndyRegistry."""

import json
import re
from unittest import IsolatedAsyncioTestCase

import pytest
from anoncreds import (
    CredentialDefinition,
    RevocationRegistryDefinition,
    RevocationRegistryDefinitionPrivate,
    Schema,
)
from base58 import alphabet

from .....anoncreds.base import AnonCredsSchemaAlreadyExists
from .....anoncreds.default.legacy_indy import registry as test_module
from .....anoncreds.issuer import AnonCredsIssuer
from .....askar.profile_anon import (
    AskarAnoncredsProfileSession,
)
from .....connections.models.conn_record import ConnRecord
from .....core.event_bus import EventBus
from .....ledger.base import BaseLedger
from .....ledger.error import LedgerObjectAlreadyExistsError
from .....ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from .....messaging.responder import BaseResponder
from .....protocols.endorse_transaction.v1_0.manager import TransactionManager
from .....protocols.endorse_transaction.v1_0.models.transaction_record import (
    TransactionRecord,
)
from .....revocation_anoncreds.models.issuer_cred_rev_record import (
    IssuerCredRevRecord,
)
from .....tests import mock
from .....utils.testing import create_test_profile
from ....models.credential_definition import (
    CredDef,
    CredDefResult,
    CredDefValue,
    CredDefValuePrimary,
)
from ....models.revocation import (
    RevList,
    RevListResult,
    RevRegDef,
    RevRegDefResult,
    RevRegDefState,
    RevRegDefValue,
)
from ....models.schema import AnonCredsSchema, GetSchemaResult, SchemaResult

B58 = alphabet if isinstance(alphabet, str) else alphabet.decode("ascii")
INDY_DID = rf"^(did:sov:)?[{B58}]{{21,22}}$"
INDY_SCHEMA_ID = rf"^[{B58}]{{21,22}}:2:.+:[0-9.]+$"
INDY_SCHEMA_TXN_ID = r"^[0-9.]+$"
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
    rf"{INDY_DID}|{INDY_SCHEMA_ID}|{INDY_SCHEMA_TXN_ID}|{INDY_CRED_DEF_ID}|{INDY_REV_REG_DEF_ID}"
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


class MockTxn:
    def to_json(self):
        return json.dumps(self.__dict__)


class MockRevRegDefEntry:
    def __init__(self, name="name"):
        self.name = name

    tags = {
        "state": RevRegDefState.STATE_ACTION,
    }
    value = "mock_value"
    value_json = {
        "value": {
            "maxCredNum": 100,
            "publicKeys": {"accumKey": {"z": "1 0BB...386"}},
            "tailsHash": "string",
            "tailsLocation": "string",
        },
        "credDefId": "CsQY9MGeD3CQP4EyuVFo5m:3:CL:14951:MYCO_Biomarker",
        "issuerId": "CsQY9MGeD3CQP4EyuVFo5m",
        "revocDefType": "CL_ACCUM",
        "tag": "string",
    }


class MockCredDefEntry:
    value_json = {}


class MockRevListEntry:
    tags = {}
    value = "mock_value"
    value_json = {
        "issuerId": "CsQY9MGeD3CQP4EyuVFo5m",
        "revRegDefId": "4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
        "revocationList": [0, 1, 0, 0],
        "currentAccumulator": "21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
        "timestamp": 1669640864487,
    }

    def to_json(self):
        return self.value_json

    def to_dict(self):
        return self.value_json


@pytest.mark.anoncreds
class TestLegacyIndyRegistry(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile(
            settings={"wallet.type": "askar-anoncreds"},
        )
        self.registry = test_module.LegacyIndyRegistry()

    async def test_supported_did_regex(self):
        """Test the supported_did_regex."""

        assert self.registry.supported_identifiers_regex == SUPPORTED_ID_REGEX
        assert bool(self.registry.supported_identifiers_regex.match(TEST_INDY_DID))
        assert bool(self.registry.supported_identifiers_regex.match(TEST_INDY_DID_1))
        assert bool(self.registry.supported_identifiers_regex.match(TEST_INDY_SCHEMA_ID))
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
            BaseResponder, mock.MagicMock(BaseResponder, autospec=True)
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

        mock_base_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_base_ledger.send_credential_definition_anoncreds = mock.CoroutineMock(
            return_value=2
        )
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock_base_ledger,
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

        mock_base_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_base_ledger.send_credential_definition_anoncreds = mock.CoroutineMock(
            return_value=("id", {"signed_txn": "txn"})
        )
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock_base_ledger,
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

        mock_base_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_base_ledger.send_credential_definition_anoncreds = mock.CoroutineMock(
            return_value=("id", {"signed_txn": "txn"})
        )
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock_base_ledger,
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

        mock_base_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_base_ledger.send_credential_definition_anoncreds = mock.CoroutineMock(
            return_value=("id", {"signed_txn": "txn"})
        )
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock_base_ledger,
        )

        self.profile.context.injector.bind_instance(
            BaseResponder,
            mock.MagicMock(BaseResponder, autospec=True),
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
        mock_base_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_base_ledger.send_revoc_reg_def = mock.CoroutineMock(return_value=1)
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock_base_ledger,
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
        self.profile.settings.set_value("endorser.author", True)
        mock_base_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_base_ledger.send_revoc_reg_def = mock.CoroutineMock(
            return_value=("id", {"signed_txn": "txn"})
        )
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock_base_ledger,
        )
        self.profile.context.injector.bind_instance(
            BaseResponder,
            mock.MagicMock(BaseResponder, autospec=True),
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
        mock_base_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_base_ledger.send_revoc_reg_def = mock.CoroutineMock(
            return_value=("id", {"signed_txn": "txn"})
        )
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock_base_ledger,
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
        mock_base_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_base_ledger.send_revoc_reg_def = mock.CoroutineMock(
            return_value=("id", {"signed_txn": "txn"})
        )
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock_base_ledger,
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
        mock_base_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_base_ledger.txn_submit = mock.CoroutineMock(return_value="transaction_id")
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock_base_ledger,
        )

        async with self.profile.session() as session:
            ledger = session.inject(BaseLedger)
            result = await self.registry.txn_submit(ledger, "test_txn")
            assert result == "transaction_id"

    @mock.patch.object(
        IndyLedgerRequestsExecutor,
        "get_ledger_for_identifier",
        return_value=(
            "id",
            mock.MagicMock(
                send_revoc_reg_entry=mock.CoroutineMock(return_value="transaction_id")
            ),
        ),
    )
    @mock.patch.object(AskarAnoncredsProfileSession, "handle")
    async def test_register_revocation_list_no_endorsement(
        self, mock_handle, mock_send_revoc_reg_entry
    ):
        self.profile.inject_or = mock.MagicMock()
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                mock.CoroutineMock(return_value=None),
                mock.CoroutineMock(return_value=None),
                mock.CoroutineMock(return_value=None),
            ]
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
        assert mock_send_revoc_reg_entry.called

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
        IndyLedgerRequestsExecutor,
        "get_ledger_for_identifier",
        return_value=(
            "id",
            mock.MagicMock(
                send_revoc_reg_entry=mock.CoroutineMock(
                    return_value=(
                        "rev_reg_def_id",
                        {
                            "signed_txn": "txn",
                        },
                    )
                )
            ),
        ),
    )
    async def test_register_revocation_list_with_author_role(
        self, mock_send_revoc_reg_entry, mock_create_record, _
    ):
        self.profile.inject_or = mock.MagicMock()
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
        assert mock_create_record.called
        assert mock_send_revoc_reg_entry.called

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
        IndyLedgerRequestsExecutor,
        "get_ledger_for_identifier",
        return_value=(
            "id",
            mock.MagicMock(
                send_revoc_reg_entry=mock.CoroutineMock(
                    return_value=(
                        "rev_reg_def_id",
                        {
                            "signed_txn": "txn",
                        },
                    )
                )
            ),
        ),
    )
    async def test_register_revocation_list_with_create_transaction_option(
        self, mock_send_revoc_reg_entry, mock_create_record, _
    ):
        self.profile.inject_or = mock.MagicMock()

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
        assert mock_create_record.called
        assert mock_send_revoc_reg_entry.called

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
    @mock.patch.object(
        IndyLedgerRequestsExecutor,
        "get_ledger_for_identifier",
        return_value=(
            "id",
            mock.MagicMock(
                send_revoc_reg_entry=mock.CoroutineMock(
                    return_value=(
                        "rev_reg_def_id",
                        {
                            "signed_txn": "txn",
                        },
                    )
                )
            ),
        ),
    )
    async def test_register_revocation_list_with_create_transaction_option_and_auto_request(
        self, mock_send_revoc_reg_entry, mock_create_request, mock_create_record, _
    ):
        self.profile.inject_or = mock.MagicMock()
        self.profile.context.injector.bind_instance(
            BaseResponder,
            mock.MagicMock(BaseResponder, autospec=True),
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
        assert mock_create_record.called
        assert mock_create_request.called
        assert mock_send_revoc_reg_entry.called
        assert self.profile.context.injector.get_provider(
            BaseResponder
        )._instance.send.called

    @mock.patch.object(
        IndyLedgerRequestsExecutor,
        "get_ledger_for_identifier",
        return_value=(
            "id",
            mock.MagicMock(
                get_revoc_reg_delta=mock.CoroutineMock(
                    return_value=(
                        {
                            "value": {
                                "accum": "21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                            }
                        },
                        123,
                    )
                )
            ),
        ),
    )
    @mock.patch.object(
        test_module.LegacyIndyRegistry,
        "_sync_wallet_rev_list_with_issuer_cred_rev_records",
        mock.CoroutineMock(
            return_value=RevList(
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                current_accumulator="2 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                revocation_list=[1, 0, 1, 0],
                timestamp=1669640864487,
                rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            )
        ),
    )
    @mock.patch(
        "acapy_agent.anoncreds.default.legacy_indy.registry.generate_ledger_rrrecovery_txn",
        mock.CoroutineMock(return_value=MockTxn()),
    )
    async def test_fix_ledger_entry(self, *_):
        mock_base_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_base_ledger.send_revoc_reg_entry = mock.CoroutineMock(return_value={})
        self.profile.context.injector.bind_instance(
            BaseLedger,
            mock_base_ledger,
        )

        self.profile.context.injector.bind_instance(
            EventBus,
            {},
        )

        async with self.profile.transaction() as txn:
            issuer_cr_rec = IssuerCredRevRecord(
                state=IssuerCredRevRecord.STATE_ISSUED,
                cred_ex_id="cred_ex_id",
                cred_ex_version=IssuerCredRevRecord.VERSION_1,
                rev_reg_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
                cred_rev_id="cred_rev_id",
            )
            await issuer_cr_rec.save(
                txn,
                reason=("Testing"),
            )

        self.profile.inject_or = mock.MagicMock()
        result = await self.registry.fix_ledger_entry(
            self.profile,
            RevList(
                issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                revocation_list=[0, 1, 1, 0],
                timestamp=1669640864487,
                rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
            ),
            True,
            '{"reqSignature":{},"txn":{"data":{"data":{"alias":"Node1","blskey":"4N8aUNHSgjQVgkpm8nhNEfDf6txHznoYREg9kirmJrkivgL4oSEimFF6nsQ6M41QvhM2Z33nves5vfSn9n1UwNFJBYtWVnHYMATn76vLuL3zU88KyeAYcHfsih3He6UHcXDxcaecHVz6jhCYz1P2UZn2bDVruL5wXpehgBfBaLKm3Ba","blskey_pop":"RahHYiCvoNCtPTrVtP7nMC5eTYrsUA8WjXbdhNc8debh1agE9bGiJxWBXYNFbnJXoXhWFMvyqhqhRoq737YQemH5ik9oL7R4NTTCz2LEZhkgLJzB3QRQqJyBNyv7acbdHrAT8nQ9UkLbaVL9NBpnWXBTw4LEMePaSHEw66RzPNdAX1","client_ip":"172.17.0.2","client_port":9702,"node_ip":"172.17.0.2","node_port":9701,"services":["VALIDATOR"]},"dest":"Gw6pDLhcBcoQesN72qfotTgFa7cbuqZpkX3Xo6pLhPhv"},"metadata":{"from":"Th7MpTaRZVRYnPiabds81Y"},"type":"0"},"txnMetadata":{"seqNo":1,"txnId":"fea82e10e894419fe2bea7d96296a6d46f50f93f9eeda954ec461b2ed2950b62"},"ver":"1"}\n{"reqSignature":{},"txn":{"data":{"data":{"alias":"Node2","blskey":"37rAPpXVoxzKhz7d9gkUe52XuXryuLXoM6P6LbWDB7LSbG62Lsb33sfG7zqS8TK1MXwuCHj1FKNzVpsnafmqLG1vXN88rt38mNFs9TENzm4QHdBzsvCuoBnPH7rpYYDo9DZNJePaDvRvqJKByCabubJz3XXKbEeshzpz4Ma5QYpJqjk","blskey_pop":"Qr658mWZ2YC8JXGXwMDQTzuZCWF7NK9EwxphGmcBvCh6ybUuLxbG65nsX4JvD4SPNtkJ2w9ug1yLTj6fgmuDg41TgECXjLCij3RMsV8CwewBVgVN67wsA45DFWvqvLtu4rjNnE9JbdFTc1Z4WCPA3Xan44K1HoHAq9EVeaRYs8zoF5","client_ip":"172.17.0.2","client_port":9704,"node_ip":"172.17.0.2","node_port":9703,"services":["VALIDATOR"]},"dest":"8ECVSk179mjsjKRLWiQtssMLgp6EPhWXtaYyStWPSGAb"},"metadata":{"from":"EbP4aYNeTHL6q385GuVpRV"},"type":"0"},"txnMetadata":{"seqNo":2,"txnId":"1ac8aece2a18ced660fef8694b61aac3af08ba875ce3026a160acbc3a3af35fc"},"ver":"1"}\n{"reqSignature":{},"txn":{"data":{"data":{"alias":"Node3","blskey":"3WFpdbg7C5cnLYZwFZevJqhubkFALBfCBBok15GdrKMUhUjGsk3jV6QKj6MZgEubF7oqCafxNdkm7eswgA4sdKTRc82tLGzZBd6vNqU8dupzup6uYUf32KTHTPQbuUM8Yk4QFXjEf2Usu2TJcNkdgpyeUSX42u5LqdDDpNSWUK5deC5","blskey_pop":"QwDeb2CkNSx6r8QC8vGQK3GRv7Yndn84TGNijX8YXHPiagXajyfTjoR87rXUu4G4QLk2cF8NNyqWiYMus1623dELWwx57rLCFqGh7N4ZRbGDRP4fnVcaKg1BcUxQ866Ven4gw8y4N56S5HzxXNBZtLYmhGHvDtk6PFkFwCvxYrNYjh","client_ip":"172.17.0.2","client_port":9706,"node_ip":"172.17.0.2","node_port":9705,"services":["VALIDATOR"]},"dest":"DKVxG2fXXTU8yT5N7hGEbXB3dfdAnYv1JczDUHpmDxya"},"metadata":{"from":"4cU41vWW82ArfxJxHkzXPG"},"type":"0"},"txnMetadata":{"seqNo":3,"txnId":"7e9f355dffa78ed24668f0e0e369fd8c224076571c51e2ea8be5f26479edebe4"},"ver":"1"}\n{"reqSignature":{},"txn":{"data":{"data":{"alias":"Node4","blskey":"2zN3bHM1m4rLz54MJHYSwvqzPchYp8jkHswveCLAEJVcX6Mm1wHQD1SkPYMzUDTZvWvhuE6VNAkK3KxVeEmsanSmvjVkReDeBEMxeDaayjcZjFGPydyey1qxBHmTvAnBKoPydvuTAqx5f7YNNRAdeLmUi99gERUU7TD8KfAa6MpQ9bw","blskey_pop":"RPLagxaR5xdimFzwmzYnz4ZhWtYQEj8iR5ZU53T2gitPCyCHQneUn2Huc4oeLd2B2HzkGnjAff4hWTJT6C7qHYB1Mv2wU5iHHGFWkhnTX9WsEAbunJCV2qcaXScKj4tTfvdDKfLiVuU2av6hbsMztirRze7LvYBkRHV3tGwyCptsrP","client_ip":"172.17.0.2","client_port":9708,"node_ip":"172.17.0.2","node_port":9707,"services":["VALIDATOR"]},"dest":"4PS3EDQ3dW1tci1Bp6543CfuuebjFrg36kLAUcskGfaA"},"metadata":{"from":"TWwCRQRZ2ZHMJFn9TzLp7W"},"type":"0"},"txnMetadata":{"seqNo":4,"txnId":"aa5e817d7cc626170eca175822029339a444eb0ee8f0bd20d3b0b76e566fb008"},"ver":"1"}',
            True,
            "endorser_did",
        )

        assert isinstance(result, tuple)

    @mock.patch.object(CredentialDefinition, "load")
    @mock.patch.object(RevocationRegistryDefinition, "load")
    @mock.patch.object(RevocationRegistryDefinitionPrivate, "load")
    @mock.patch.object(
        IssuerCredRevRecord,
        "query_by_ids",
        return_value=[
            IssuerCredRevRecord(
                state=IssuerCredRevRecord.STATE_REVOKED,
                cred_ex_id="cred_ex_id",
                rev_reg_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
                cred_rev_id="1",
            ),
            IssuerCredRevRecord(
                state=IssuerCredRevRecord.STATE_REVOKED,
                cred_ex_id="cred_ex_id",
                rev_reg_id="4xE68b6S5VRFrKMMG1U95M:5:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
                cred_rev_id="2",
            ),
        ],
    )
    @mock.patch.object(
        RevList,
        "to_native",
        return_value=mock.MagicMock(
            update=mock.MagicMock(return_value=MockRevListEntry())
        ),
    )
    @mock.patch.object(AskarAnoncredsProfileSession, "handle")
    async def test_sync_wallet_rev_list_with_issuer_cred_rev_records(
        self, mock_handle, *_
    ):
        async with self.profile.session() as session:
            # Matching revocations and rev_list
            mock_handle.fetch = mock.CoroutineMock(
                side_effect=[
                    MockRevRegDefEntry(),
                    MockCredDefEntry(),
                    mock.CoroutineMock(return_value=None),
                ]
            )
            result = await self.registry._sync_wallet_rev_list_with_issuer_cred_rev_records(
                session,
                RevList(
                    issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                    current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                    revocation_list=[0, 1, 1, 0],
                    timestamp=1669640864487,
                    rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
                ),
            )
            assert isinstance(result, RevList)
            # Non-matching revocations and rev_list
            mock_handle.fetch = mock.CoroutineMock(
                side_effect=[
                    MockRevRegDefEntry(),
                    MockCredDefEntry(),
                    mock.CoroutineMock(return_value=None),
                    MockRevListEntry(),
                ]
            )
            mock_handle.replace = mock.CoroutineMock(return_value=None)
            result = await self.registry._sync_wallet_rev_list_with_issuer_cred_rev_records(
                session,
                RevList(
                    issuer_id="CsQY9MGeD3CQP4EyuVFo5m",
                    current_accumulator="21 124C594B6B20E41B681E92B2C43FD165EA9E68BC3C9D63A82C8893124983CAE94 21 124C5341937827427B0A3A32113BD5E64FB7AB39BD3E5ABDD7970874501CA4897 6 5438CB6F442E2F807812FD9DC0C39AFF4A86B1E6766DBB5359E86A4D70401B0F 4 39D1CA5C4716FFC4FE0853C4FF7F081DFD8DF8D2C2CA79705211680AC77BF3A1 6 70504A5493F89C97C225B68310811A41AD9CD889301F238E93C95AD085E84191 4 39582252194D756D5D86D0EED02BF1B95CE12AED2FA5CD3C53260747D891993C",
                    revocation_list=[0, 1, 0, 0],
                    timestamp=1669640864487,
                    rev_reg_def_id="4xE68b6S5VRFrKMMG1U95M:4:4xE68b6S5VRFrKMMG1U95M:3:CL:59232:default:CL_ACCUM:4ae1cc6c-f6bd-486c-8057-88f2ce74e960",
                ),
            )
            assert isinstance(result, RevList)

    async def test_get_schem_info(self):
        result = await self.registry.get_schema_info_by_id(
            self.profile,
            "XduBsoPyEA4szYMy3pZ8De:2:minimal-33279d005748b3cc:1.0",
        )
        assert result.issuer_id == "XduBsoPyEA4szYMy3pZ8De"
        assert result.name == "minimal-33279d005748b3cc"
        assert result.version == "1.0"
