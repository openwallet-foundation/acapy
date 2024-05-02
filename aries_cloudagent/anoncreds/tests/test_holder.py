import json
from copy import deepcopy
from unittest import IsolatedAsyncioTestCase

import anoncreds
import pytest
from anoncreds import (
    AnoncredsError,
    AnoncredsErrorCode,
    Credential,
    CredentialDefinition,
    CredentialRequest,
    CredentialRevocationState,
    Presentation,
    PresentCredentials,
    RevocationRegistryDefinition,
    Schema,
)
from aries_askar import AskarError, AskarErrorCode

from aries_cloudagent.anoncreds.holder import AnonCredsHolder, AnonCredsHolderError
from aries_cloudagent.anoncreds.tests.mock_objects import (
    MOCK_CRED,
    MOCK_CRED_DEF,
    MOCK_PRES,
    MOCK_PRES_REQ,
)
from aries_cloudagent.askar.profile_anon import AskarAnoncredsProfile
from aries_cloudagent.core.in_memory.profile import (
    InMemoryProfile,
    InMemoryProfileSession,
)
from aries_cloudagent.indy.sdk.profile import IndySdkProfile
from aries_cloudagent.tests import mock
from aries_cloudagent.wallet.error import WalletNotFoundError

from .. import holder as test_module
from ..models.anoncreds_cred_def import CredDef, CredDefValue, CredDefValuePrimary


class MockCredReceived:
    def __init__(self, bad_schema=False, bad_cred_def=False):
        self.schema_id = "Sc886XPwD1gDcHwmmLDeR2:2:degree schema:45.101.94"
        self.cred_def_id = (
            "Sc886XPwD1gDcHwmmLDeR2:3:CL:229975:faber.agent.degree_schema"
        )

        if bad_schema:
            self.schema_id = "bad-schema-id"
        if bad_cred_def:
            self.cred_def_id = "bad-cred-def-id"

    schema_id = "Sc886XPwD1gDcHwmmLDeR2:2:degree schema:45.101.94"
    cred_def_id = "Sc886XPwD1gDcHwmmLDeR2:3:CL:229975:faber.agent.degree_schema"
    rev_reg_id = None

    def to_json_buffer(self):
        return b"credential"


class MockCredential:
    def __init__(self, bad_schema=False, bad_cred_def=False):
        self.bad_schema = bad_schema
        self.bad_cred_def = bad_cred_def

    cred = mock.AsyncMock(auto_spec=Credential)

    def to_dict(self):
        return MOCK_CRED

    def process(self, *args, **kwargs):
        return MockCredReceived(self.bad_schema, self.bad_cred_def)


class MockMasterSecret:
    value = b"master-secret"


class MockCredEntry:
    def __init__(self, rev_reg=False) -> None:
        mock_cred = deepcopy(MOCK_CRED)
        if rev_reg:
            mock_cred["rev_reg_id"] = "rev-reg-id"
        self.name = "name"
        self.value = mock_cred
        self.raw_value = mock_cred

    def decode(self):
        return MOCK_CRED


class MockCredScan:
    value = [MockCredEntry()]
    name = "name"

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.value:
            return self.value.pop()
        raise StopAsyncIteration


class MockMimeTypeRecord:
    value_json = {"mime-type": "mime-type"}


@pytest.mark.anoncreds
class TestAnonCredsHolder(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet.type": "askar-anoncreds"},
            profile_class=AskarAnoncredsProfile,
        )
        self.holder = test_module.AnonCredsHolder(self.profile)

    async def test_init(self):
        assert isinstance(self.holder, AnonCredsHolder)
        assert isinstance(self.holder.profile, AskarAnoncredsProfile)

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_master_secret(self, mock_session_handle):
        mock_session_handle.fetch = mock.CoroutineMock(return_value=MockMasterSecret())
        secret = await self.holder.get_master_secret()
        assert secret is not None

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_master_secret_errors(self, mock_session_handle):
        # Not found
        mock_session_handle.fetch = mock.CoroutineMock(
            side_effect=[AskarError(code=AskarErrorCode.NOT_FOUND, message="test")]
        )
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.get_master_secret()

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_master_secret_does_not_return_master_secret(
        self, mock_session_handle
    ):
        # Duplicate - Retry
        mock_session_handle.fetch = mock.CoroutineMock(return_value=None)
        mock_session_handle.insert = mock.CoroutineMock(
            side_effect=[AskarError(code=AskarErrorCode.DUPLICATE, message="test")]
        )
        with self.assertRaises(StopAsyncIteration):
            await self.holder.get_master_secret()
        # Other error
        mock_session_handle.fetch = mock.CoroutineMock(return_value=None)
        mock_session_handle.insert = mock.CoroutineMock(
            side_effect=[AskarError(code=AskarErrorCode.UNEXPECTED, message="test")]
        )
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.get_master_secret()

    @mock.patch.object(
        AnonCredsHolder, "get_master_secret", return_value="master-secret"
    )
    @mock.patch.object(
        CredentialRequest,
        "create",
        return_value=(mock.Mock(), mock.Mock()),
    )
    async def test_create_credential_request(
        self, mock_credential_request, mock_master_secret
    ):
        cred_def = CredDef(
            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
            schema_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ/anoncreds/v0/SCHEMA/MemberPass/1.0",
            tag="tag",
            type="CL",
            value=CredDefValue(primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")),
        )
        # error - to_native_fails
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.create_credential_request(
                {"offer": "offer"},
                cred_def,
                "holder-did",
            )

        # Need to mock or else it will get ssl error
        cred_def.to_native = mock.MagicMock(return_value="native-cred-request")

        (
            cred_req_json,
            cred_req_metadata_json,
        ) = await self.holder.create_credential_request(
            {"offer": "offer"},
            cred_def,
            "holder-did",
        )

        assert cred_req_json is not None
        assert cred_req_metadata_json is not None
        assert mock_master_secret.called
        assert mock_credential_request.called

    async def test_create_credential_request_with_non_anoncreds_profile_throws_x(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet-type": "askar"},
            profile_class=IndySdkProfile,
        )
        self.holder = test_module.AnonCredsHolder(self.profile)
        with self.assertRaises(ValueError):
            await self.holder.create_credential_request(
                {"offer": "offer"},
                CredDef(
                    issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
                    schema_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ/anoncreds/v0/SCHEMA/MemberPass/1.0",
                    tag="tag",
                    type="CL",
                    value=CredDefValue(
                        primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")
                    ),
                ),
                "holder-did",
            )

    @mock.patch.object(
        AnonCredsHolder, "get_master_secret", return_value="master-secret"
    )
    async def test_store_credential_fails_to_load_raises_x(self, mock_master_secret):
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.store_credential(
                {"cred-def": "cred-def"},
                {
                    "values": [
                        "name",
                        "date",
                        "degree",
                        "birthdate_dateint",
                        "timestamp",
                    ]
                },
                {"cred-req-meta": "cred-req-meta"},
            )
            assert mock_master_secret.called

    @mock.patch.object(
        AnonCredsHolder, "get_master_secret", return_value="master-secret"
    )
    @mock.patch.object(
        Credential,
        "load",
        side_effect=[
            MockCredential(),
            MockCredential(),
            MockCredential(bad_schema=True),
            MockCredential(bad_cred_def=True),
        ],
    )
    async def test_store_credential(self, mock_load, mock_master_secret):
        self.profile.transaction = mock.Mock(
            return_value=mock.MagicMock(
                insert=mock.CoroutineMock(return_value=None),
                commit=mock.CoroutineMock(return_value=None),
            )
        )

        # Valid
        result = await self.holder.store_credential(
            MOCK_CRED_DEF,
            MOCK_CRED,
            {"cred-req-meta": "cred-req-meta"},
            credential_attr_mime_types={"first_name": "application/json"},
        )

        assert result is not None
        assert mock_master_secret.called
        assert mock_load.called
        assert self.profile.transaction.called

        # Testing normalizing attr names
        await self.holder.store_credential(
            MOCK_CRED_DEF,
            {
                "values": {
                    "First Name": {"raw": "Alice", "encoded": "113...335"},
                },
            },
            {"cred-req-meta": "cred-req-meta"},
        )

        # Test bad id's
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.store_credential(
                MOCK_CRED_DEF,
                MOCK_PRES,
                {"cred-req-meta": "cred-req-meta"},
            )
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.store_credential(
                MOCK_CRED_DEF,
                MOCK_CRED,
                {"cred-req-meta": "cred-req-meta"},
            )

    @mock.patch.object(
        AnonCredsHolder, "get_master_secret", return_value="master-secret"
    )
    @mock.patch.object(Credential, "load", return_value=MockCredential())
    async def test_store_credential_failed_trx(self, mock_load, mock_master_secret):
        self.profile.transaction = mock.MagicMock(
            side_effect=[AskarError(AskarErrorCode.UNEXPECTED, "test")]
        )

        with self.assertRaises(AnonCredsHolderError):
            await self.holder.store_credential(
                MOCK_CRED_DEF,
                MOCK_CRED,
                {"cred-req-meta": "cred-req-meta"},
                credential_attr_mime_types={"first_name": "application/json"},
            )

    async def test_get_credentials(self):
        self.profile.store = mock.Mock()
        self.profile.store.scan = mock.Mock(return_value=MockCredScan())

        result = await self.holder.get_credentials(0, 10, {})
        assert isinstance(result, list)
        assert len(result) == 1

    async def test_get_credentials_errors(self):
        self.profile.store = mock.Mock()
        self.profile.store.scan = mock.Mock(
            side_effect=[
                AskarError(AskarErrorCode.UNEXPECTED, "test"),
                AnoncredsError(AnoncredsErrorCode.UNEXPECTED, "test"),
            ]
        )

        with self.assertRaises(AnonCredsHolderError):
            await self.holder.get_credentials(0, 10, {})
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.get_credentials(0, 10, {})

    async def test_get_credentials_for_presentation_request_by_referent(self):
        self.profile.store = mock.Mock()
        self.profile.store.scan = mock.Mock(
            return_value=mock.CoroutineMock(
                side_effect=[
                    MockCredScan(),
                ]
            )
        )

        # add predicates
        mock_pres_req = deepcopy(MOCK_PRES_REQ)
        mock_pres_req["requested_predicates"]["0_concentration_GE_uuid"] = {
            "name": "concentration",
            "p_type": "<=",
            "p_value": 9,
            "restrictions": [{"schema_name": "MYCO Biomarker"}],
        }
        await self.holder.get_credentials_for_presentation_request_by_referent(
            mock_pres_req, None, start=0, count=10
        )

        # non-existent referent
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.get_credentials_for_presentation_request_by_referent(
                mock_pres_req, "not-found-ref", start=0, count=10
            )

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_credential(self, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(side_effect=[MockCredEntry(), None])
        result = await self.holder.get_credential("cred-id")
        assert isinstance(result, str)

        with self.assertRaises(WalletNotFoundError):
            await self.holder.get_credential("cred-id")

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_credential_revoked(self, mock_handle):
        mock_ledger = mock.MagicMock(
            get_revoc_reg_delta=mock.CoroutineMock(
                return_value=(
                    {
                        "value": {
                            "revoked": [100],
                        }
                    },
                    0,
                ),
            )
        )
        mock_handle.fetch = mock.CoroutineMock(return_value=MockCredEntry())
        assert (
            await self.holder.credential_revoked(
                ledger=mock_ledger,
                credential_id="cred-id",
                to=None,
                fro=None,
            )
            is False
        )

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_delete_credential(self, mock_handle):
        mock_handle.remove = mock.CoroutineMock(
            side_effect=[
                None,
                None,
                AskarError(AskarErrorCode.NOT_FOUND, "test"),
                AskarError(AskarErrorCode.UNEXPECTED, "test"),
            ]
        )
        await self.holder.delete_credential("cred-id")

        mock_handle.remove.call_args_list[0].args == ("credential", "cred-id")
        mock_handle.remove.call_args_list[0].args == ("attribute-mime-types", "cred-id")

        # not found, don't raise error
        await self.holder.delete_credential("cred-id")
        # other asker error, raise error
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.delete_credential("cred-id")

    @mock.patch.object(InMemoryProfileSession, "handle")
    async def test_get_mime_type(self, mock_handle):
        mock_handle.fetch = mock.CoroutineMock(
            side_effect=[
                MockMimeTypeRecord(),
                AskarError(AskarErrorCode.UNEXPECTED, "test"),
            ]
        )
        result = await self.holder.get_mime_type("cred-id", "mime-type")
        assert result == "mime-type"

        # asker error
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.get_mime_type("cred-id", "mime-type")
            assert mock_handle.fetch.call_count == 2

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(
        AnonCredsHolder, "get_master_secret", return_value="master-secret"
    )
    @mock.patch.object(
        anoncreds.Presentation, "create", return_value=Presentation.load(MOCK_PRES)
    )
    async def test_create_presentation(
        self, mock_pres_create, mock_master_secret, mock_handle
    ):
        mock_handle.fetch = mock.CoroutineMock(return_value=MockCredEntry())
        result = await self.holder.create_presentation(
            presentation_request=MOCK_PRES_REQ,
            requested_credentials={
                "self_attested_attributes": {},
                "requested_attributes": {},
                "requested_predicates": {},
            },
            schemas={},
            credential_definitions={},
            rev_states={},
        )

        json.loads(result)
        assert mock_pres_create.called
        assert mock_master_secret.called
        mock_handle.fetch.assert_called

        # requested_attributes and predicates
        await self.holder.create_presentation(
            presentation_request=MOCK_PRES_REQ,
            requested_credentials={
                "self_attested_attributes": {},
                "requested_attributes": {
                    "biomarker_attrs_0": {
                        "cred_id": "cred-id-requested",
                        "revealed": True,
                    },
                },
                "requested_predicates": {
                    "0_concentration_GE_uuid": {
                        "cred_id": "cred-id-predicate",
                    }
                },
            },
            schemas={},
            credential_definitions={},
            rev_states={},
        )

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(
        AnonCredsHolder, "get_master_secret", return_value="master-secret"
    )
    @mock.patch.object(
        anoncreds.Presentation, "create", return_value=Presentation.load(MOCK_PRES)
    )
    @mock.patch.object(PresentCredentials, "add_attributes")
    async def test_create_presentation_with_revocation(
        self, mock_add_attributes, mock_pres_create, mock_master_secret, mock_handle
    ):
        mock_handle.fetch = mock.CoroutineMock(return_value=MockCredEntry(rev_reg=True))

        # not in rev_states
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.create_presentation(
                presentation_request=MOCK_PRES_REQ,
                requested_credentials={
                    "self_attested_attributes": {},
                    "requested_attributes": {
                        "biomarker_attrs_0": {
                            "cred_id": "cred-id-requested",
                            "revealed": True,
                            "timestamp": 1234567890,
                        },
                    },
                    "requested_predicates": {
                        "0_concentration_GE_uuid": {
                            "cred_id": "cred-id-predicate",
                        }
                    },
                },
                schemas={},
                credential_definitions={},
                rev_states={},
            )
        # wrong timestamp
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.create_presentation(
                presentation_request=MOCK_PRES_REQ,
                requested_credentials={
                    "self_attested_attributes": {},
                    "requested_attributes": {
                        "biomarker_attrs_0": {
                            "cred_id": "cred-id-requested",
                            "revealed": True,
                            "timestamp": 1234567890,
                        },
                    },
                    "requested_predicates": {
                        "0_concentration_GE_uuid": {
                            "cred_id": "cred-id-predicate",
                        }
                    },
                },
                schemas={},
                credential_definitions={},
                rev_states={
                    "rev-reg-id": {
                        "9999999999": b"100",
                    }
                },
            )

        await self.holder.create_presentation(
            presentation_request=MOCK_PRES_REQ,
            requested_credentials={
                "self_attested_attributes": {},
                "requested_attributes": {
                    "biomarker_attrs_0": {
                        "cred_id": "cred-id-requested",
                        "revealed": True,
                        "timestamp": 1234567890,
                    },
                },
                "requested_predicates": {
                    "0_concentration_GE_uuid": {
                        "cred_id": "cred-id-predicate",
                    }
                },
            },
            schemas={},
            credential_definitions={},
            rev_states={
                "rev-reg-id": {
                    1234567890: b'{"witness":{"omega": "21 124...AC8"}}',
                }
            },
        )

        assert mock_add_attributes.called
        assert mock_pres_create.called
        assert mock_master_secret.called
        assert mock_handle.fetch.called

    @mock.patch.object(InMemoryProfileSession, "handle")
    @mock.patch.object(
        AnonCredsHolder, "get_master_secret", return_value="master-secret"
    )
    @mock.patch.object(
        anoncreds.Presentation,
        "create",
        side_effect=AnoncredsError(AnoncredsErrorCode.UNEXPECTED, "test"),
    )
    async def test_create_presentation_create_error(
        self, mock_pres_create, mock_master_secret, mock_handle
    ):
        mock_handle.fetch = mock.CoroutineMock(return_value=MockCredEntry())
        # anoncreds error when creating presentation
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.create_presentation(
                presentation_request=MOCK_PRES_REQ,
                requested_credentials={
                    "self_attested_attributes": {},
                    "requested_attributes": {},
                    "requested_predicates": {},
                },
                schemas={},
                credential_definitions={},
                rev_states={},
            )

    @mock.patch.object(
        CredentialRevocationState,
        "create",
    )
    async def test_create_revocation_state(self, mock_create):
        schema = Schema.create(
            name="MemberPass",
            attr_names=["member", "score"],
            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
            version="1.0",
        )

        (cred_def, _, _) = CredentialDefinition.create(
            schema_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ/anoncreds/v0/SCHEMA/MemberPass/1.0",
            schema=schema,
            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
            tag="tag",
            support_revocation=True,
            signature_type="CL",
        )
        (rev, _) = RevocationRegistryDefinition.create(
            cred_def_id="SGrjRL82Y9ZZbzhUDXokvQ:3:CL:531757:MemberPass",
            cred_def=cred_def,
            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
            registry_type="CL_ACCUM",
            max_cred_num=100,
            tag="tag",
        )
        mock_create.return_value = rev
        result = await self.holder.create_revocation_state(
            cred_rev_id="1",
            rev_reg_def={"def": 1},
            rev_list={"accum": "1"},
            tails_file_path="/tmp/some.tails",
        )

        result = json.loads(result)
        assert mock_create.called

        # error
        mock_create.side_effect = AnoncredsError(AnoncredsErrorCode.UNEXPECTED, "test")
        with self.assertRaises(AnonCredsHolderError):
            await self.holder.create_revocation_state(
                cred_rev_id="1",
                rev_reg_def={"def": 1},
                rev_list={"accum": "1"},
                tails_file_path="/tmp/some.tails",
            )
