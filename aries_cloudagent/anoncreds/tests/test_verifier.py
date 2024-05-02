from copy import deepcopy
from unittest import IsolatedAsyncioTestCase

import pytest

from aries_cloudagent.anoncreds.models.anoncreds_cred_def import (
    CredDef,
    CredDefValue,
    CredDefValuePrimary,
    CredDefValueRevocation,
    GetCredDefResult,
)
from aries_cloudagent.anoncreds.models.anoncreds_revocation import (
    GetRevListResult,
    GetRevRegDefResult,
    RevList,
    RevRegDef,
    RevRegDefValue,
)
from aries_cloudagent.anoncreds.models.anoncreds_schema import (
    AnonCredsSchema,
    GetSchemaResult,
)
from aries_cloudagent.askar.profile_anon import AskarAnoncredsProfile
from aries_cloudagent.core.in_memory.profile import (
    InMemoryProfile,
)
from aries_cloudagent.tests import mock

from .. import verifier as test_module
from .mock_objects import (
    MOCK_CRED_DEFS,
    MOCK_PRES,
    MOCK_PRES_REQ,
    MOCK_REV_REG_DEFS,
    MOCK_SCHEMAS,
)


@pytest.mark.anoncreds
class TestAnonCredsVerifier(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet.type": "askar-anoncreds"},
            profile_class=AskarAnoncredsProfile,
        )
        self.verifier = test_module.AnonCredsVerifier(self.profile)

    async def test_init(self):
        assert self.verifier.profile == self.profile

    async def test_non_revoc_intervals(self):
        result = self.verifier.non_revoc_intervals(
            MOCK_PRES_REQ, MOCK_PRES, MOCK_CRED_DEFS
        )
        assert isinstance(result, list)

        non_revoked_req = deepcopy(MOCK_PRES_REQ)
        non_revoked_req["requested_attributes"]["biomarker_attrs_0"]["non_revoked"] = (
            {
                "from": 1593922800,
                "to": 1593922800,
            },
        )

        result = self.verifier.non_revoc_intervals(
            non_revoked_req, MOCK_PRES, MOCK_CRED_DEFS
        )

    async def test_check_timestamps_with_names(self):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    return_value=GetCredDefResult(
                        credential_definition_id="TUku9MDGa7QALbAJX4oAww:3:CL:531757:MYCO_Consent_Enablement",
                        credential_definition=CredDef(
                            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
                            schema_id="schema-id",
                            tag="tag",
                            type="CL",
                            value=CredDefValue(
                                primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")
                            ),
                        ),
                        credential_definition_metadata={},
                        resolution_metadata={},
                    )
                )
            )
        )
        await self.verifier.check_timestamps(
            self.profile, MOCK_PRES_REQ, MOCK_PRES, MOCK_REV_REG_DEFS
        )

        # irrevocable cred-def with timestamp
        mock_pres = deepcopy(MOCK_PRES)
        mock_pres["identifiers"][0]["timestamp"] = 9999999999
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, MOCK_PRES_REQ, mock_pres, MOCK_REV_REG_DEFS
            )

        # revocable cred-def with timestamp
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    return_value=GetCredDefResult(
                        credential_definition_id="TUku9MDGa7QALbAJX4oAww:3:CL:531757:MYCO_Consent_Enablement",
                        credential_definition=CredDef(
                            issuer_id="issuer-id",
                            schema_id="schema-id",
                            tag="tag",
                            type="CL",
                            value=CredDefValue(
                                primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z"),
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
                    )
                )
            )
        )

        # too far in future
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, MOCK_PRES_REQ, mock_pres, MOCK_REV_REG_DEFS
            )

        # no rev_reg_id
        mock_pres["identifiers"][0]["timestamp"] = 1234567890
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, MOCK_PRES_REQ, mock_pres, MOCK_REV_REG_DEFS
            )

        # with rev_reg_id
        mock_pres["identifiers"][0][
            "rev_reg_id"
        ] = "TUku9MDGa7QALbAJX4oAww:3:TUku9MDGa7QALbAJX4oAww:3:CL:18:tag:CL_ACCUM:0"

        # Superfluous timestamp
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, MOCK_PRES_REQ, mock_pres, MOCK_REV_REG_DEFS
            )

        # Valid
        mock_pres["identifiers"][0]["timestamp"] = None
        await self.verifier.check_timestamps(
            self.profile, MOCK_PRES_REQ, mock_pres, MOCK_REV_REG_DEFS
        )

        #  outside of non-revocation interval
        mock_pres_req = deepcopy(MOCK_PRES_REQ)
        mock_pres_req["requested_attributes"]["biomarker_attrs_0"]["non_revoked"] = {
            "from": 9000000000,
            "to": 1000000000,
        }
        mock_pres["identifiers"][0]["timestamp"] = 123456789
        await self.verifier.check_timestamps(
            self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
        )

        # no revealed attr groups
        mock_pres["requested_proof"]["revealed_attr_groups"] = {}
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
            )

    async def test_check_timestamps_with_name(self):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    return_value=GetCredDefResult(
                        credential_definition_id="TUku9MDGa7QALbAJX4oAww:3:CL:531757:MYCO_Consent_Enablement",
                        credential_definition=CredDef(
                            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
                            schema_id="schema-id",
                            tag="tag",
                            type="CL",
                            value=CredDefValue(
                                primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")
                            ),
                        ),
                        credential_definition_metadata={},
                        resolution_metadata={},
                    )
                )
            )
        )
        mock_pres_req = deepcopy(MOCK_PRES_REQ)
        mock_pres = deepcopy(MOCK_PRES)
        del mock_pres_req["requested_attributes"]["biomarker_attrs_0"]["names"]
        mock_pres_req["requested_attributes"]["biomarker_attrs_0"]["name"] = "name"

        # invalid group
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
            )

        # valid
        del mock_pres["requested_proof"]["revealed_attrs"]["consent_attrs"]
        del mock_pres["requested_proof"]["revealed_attr_groups"]["biomarker_attrs_0"]
        del mock_pres_req["requested_attributes"]["consent_attrs"]
        mock_pres["requested_proof"]["revealed_attrs"]["biomarker_attrs_0"] = {
            "sub_proof_index": 0,
            "raw": "Iron",
            "encoded": "85547618788485118809771015708850341281587970912661276233439574555663751388073",
        }

        await self.verifier.check_timestamps(
            self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
        )

        # revocable cred-def with timestamp
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    return_value=GetCredDefResult(
                        credential_definition_id="TUku9MDGa7QALbAJX4oAww:3:CL:531757:MYCO_Consent_Enablement",
                        credential_definition=CredDef(
                            issuer_id="issuer-id",
                            schema_id="schema-id",
                            tag="tag",
                            type="CL",
                            value=CredDefValue(
                                primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z"),
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
                    )
                )
            )
        )

        # no rev_reg_id
        mock_pres["identifiers"][0]["timestamp"] = 1234567890
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
            )

        # with rev_reg_id
        mock_pres["identifiers"][0][
            "rev_reg_id"
        ] = "TUku9MDGa7QALbAJX4oAww:3:TUku9MDGa7QALbAJX4oAww:3:CL:18:tag:CL_ACCUM:0"

        # Superfluous timestamp
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
            )

        #  outside of non-revocation interval
        mock_pres_req["requested_attributes"]["biomarker_attrs_0"]["non_revoked"] = {
            "from": 9000000000,
            "to": 1000000000,
        }
        mock_pres["identifiers"][0]["timestamp"] = 123456789
        await self.verifier.check_timestamps(
            self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
        )

        # unrevealed attr
        mock_pres["requested_proof"]["revealed_attrs"] = {}
        mock_pres["requested_proof"]["unrevealed_attrs"]["biomarker_attrs_0"] = {
            "sub_proof_index": 0,
        }
        await self.verifier.check_timestamps(
            self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
        )

    async def test_check_timestamps_predicates(self):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    return_value=GetCredDefResult(
                        credential_definition_id="TUku9MDGa7QALbAJX4oAww:3:CL:531757:MYCO_Consent_Enablement",
                        credential_definition=CredDef(
                            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
                            schema_id="schema-id",
                            tag="tag",
                            type="CL",
                            value=CredDefValue(
                                primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")
                            ),
                        ),
                        credential_definition_metadata={},
                        resolution_metadata={},
                    )
                )
            )
        )

        mock_pres_req = deepcopy(MOCK_PRES_REQ)
        mock_pres_req["requested_attributes"] = {}
        mock_pres_req["requested_predicates"]["0_concentration_GE_uuid"] = {
            "name": "concentration",
            "p_type": "<=",
            "p_value": 9,
            "restrictions": [{"schema_name": "MYCO Biomarker"}],
        }

        # predicate not in proof
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, mock_pres_req, MOCK_PRES, MOCK_REV_REG_DEFS
            )

        mock_pres = deepcopy(MOCK_PRES)
        mock_pres["requested_proof"]["predicates"] = {
            "0_concentration_GE_uuid": {"sub_proof_index": 0}
        }

        #  valid - no revocation
        await self.verifier.check_timestamps(
            self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
        )

        # revocation

        # revocable cred-def with timestamp
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    return_value=GetCredDefResult(
                        credential_definition_id="TUku9MDGa7QALbAJX4oAww:3:CL:531757:MYCO_Consent_Enablement",
                        credential_definition=CredDef(
                            issuer_id="issuer-id",
                            schema_id="schema-id",
                            tag="tag",
                            type="CL",
                            value=CredDefValue(
                                primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z"),
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
                    )
                )
            )
        )

        # no rev_reg_id
        mock_pres["identifiers"][0]["timestamp"] = 1234567890
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
            )

        # with rev_reg_id
        mock_pres["identifiers"][0][
            "rev_reg_id"
        ] = "TUku9MDGa7QALbAJX4oAww:3:TUku9MDGa7QALbAJX4oAww:3:CL:18:tag:CL_ACCUM:0"

        # Superfluous timestamp
        with self.assertRaises(ValueError):
            await self.verifier.check_timestamps(
                self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
            )

        #  outside of non-revocation interval
        mock_pres_req["requested_predicates"]["0_concentration_GE_uuid"][
            "non_revoked"
        ] = {
            "from": 9000000000,
            "to": 1000000000,
        }
        mock_pres["identifiers"][0]["timestamp"] = 123456789
        await self.verifier.check_timestamps(
            self.profile, mock_pres_req, mock_pres, MOCK_REV_REG_DEFS
        )

    async def test_pre_verify_incomplete_objects(self):
        mock_pres_req = deepcopy(MOCK_PRES_REQ)
        mock_pres = deepcopy(MOCK_PRES)

        with self.assertRaises(ValueError):
            await self.verifier.pre_verify(mock_pres_req, {})

        with self.assertRaises(ValueError):
            await self.verifier.pre_verify({}, mock_pres)

        del mock_pres_req["requested_predicates"]
        with self.assertRaises(ValueError):
            await self.verifier.pre_verify(mock_pres_req, mock_pres)
        mock_pres_req["requested_predicates"] = {}

        del mock_pres_req["requested_attributes"]
        with self.assertRaises(ValueError):
            await self.verifier.pre_verify(mock_pres_req, mock_pres)
        mock_pres_req["requested_attributes"] = {}

        del mock_pres["requested_proof"]
        with self.assertRaises(ValueError):
            await self.verifier.pre_verify(mock_pres_req, mock_pres)
        mock_pres["requested_proof"] = {}

        del mock_pres["proof"]
        with self.assertRaises(ValueError):
            await self.verifier.pre_verify(mock_pres_req, mock_pres)

    async def test_pre_verify(self):
        mock_pres_req = deepcopy(MOCK_PRES_REQ)
        mock_pres = deepcopy(MOCK_PRES)

        # valid - with names and name
        result = await self.verifier.pre_verify(mock_pres_req, mock_pres)
        assert isinstance(result, list)

        # name in unrevealed attrs
        mock_pres["requested_proof"]["revealed_attrs"] = {}
        mock_pres["requested_proof"]["unrevealed_attrs"] = {
            "consent_attrs": {"sub_proof_index": 1}
        }
        await self.verifier.pre_verify(mock_pres_req, mock_pres)

        # self-attested attrs with restrictions
        mock_pres["requested_proof"]["unrevealed_attrs"] = {}
        mock_pres["requested_proof"]["self_attested_attrs"] = {
            "consent_attrs": "I agree to share my data with the verifier"
        }
        with self.assertRaises(ValueError):
            await self.verifier.pre_verify(mock_pres_req, mock_pres)

        # valid - self-attested
        mock_pres_req["requested_attributes"]["consent_attrs"]["restrictions"] = []
        await self.verifier.pre_verify(mock_pres_req, mock_pres)

        #  no name or names
        del mock_pres_req["requested_attributes"]["consent_attrs"]["name"]
        with self.assertRaises(ValueError):
            await self.verifier.pre_verify(mock_pres_req, mock_pres)
        mock_pres_req["requested_attributes"]["consent_attrs"][
            "name"
        ] = "jti_unique_identifier"
        # attr not in proof
        mock_pres["requested_proof"]["self_attested_attrs"] = {}
        with self.assertRaises(ValueError):
            await self.verifier.pre_verify(mock_pres_req, mock_pres)

        # predicates

        # predicate not in proof
        mock_pres_req["requested_attributes"] = {}
        mock_pres_req["requested_predicates"]["0_concentration_GE_uuid"] = {
            "name": "concentration",
            "p_type": "<=",
            "p_value": 9,
            "restrictions": [{"schema_name": "MYCO Biomarker"}],
        }

        mock_pres["requested_proof"]["predicates"] = {
            "0_concentration_GE_uuid": {"sub_proof_index": 0}
        }
        with self.assertRaises(ValueError):
            await self.verifier.pre_verify(mock_pres_req, mock_pres)

        mock_pres["proof"]["proofs"][0]["primary_proof"]["ge_proofs"] = [
            {
                "predicate": {
                    "attr_name": "concentration",
                    "p_type": "<=",
                    "value": 9,
                },
            }
        ]
        await self.verifier.pre_verify(mock_pres_req, mock_pres)

    async def test_process_pres_identifiers(self):
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
                get_credential_definition=mock.CoroutineMock(
                    return_value=GetCredDefResult(
                        credential_definition_id="cred-def-id",
                        credential_definition=CredDef(
                            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
                            schema_id="schema-id",
                            tag="tag",
                            type="CL",
                            value=CredDefValue(
                                primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")
                            ),
                        ),
                        credential_definition_metadata={},
                        resolution_metadata={},
                    )
                ),
                get_revocation_registry_definition=mock.CoroutineMock(
                    return_value=GetRevRegDefResult(
                        revocation_registry_id="rev-reg-id",
                        revocation_registry=RevRegDef(
                            issuer_id="issuer-id",
                            cred_def_id="cred-def-id",
                            type="CL_ACCUM",
                            tag="tag",
                            value=RevRegDefValue(
                                public_keys={},
                                max_cred_num=1000,
                                tails_hash="tails-hash",
                                tails_location="tails-location",
                            ),
                        ),
                        resolution_metadata={},
                        revocation_registry_metadata={},
                    )
                ),
                get_revocation_list=mock.CoroutineMock(
                    return_value=GetRevListResult(
                        revocation_list=RevList(
                            issuer_id="issuer-id",
                            rev_reg_def_id="rev-reg-def-id",
                            revocation_list=[],
                            current_accumulator="current-accumulator",
                        ),
                        resolution_metadata={},
                        revocation_registry_metadata={},
                    )
                ),
            )
        )
        result = await self.verifier.process_pres_identifiers(
            [
                {
                    "schema_id": "schema-id",
                    "cred_def_id": "cred-def-id",
                    "rev_reg_id": "rev-reg-id",
                    "timestamp": 1234567890,
                }
            ]
        )

        assert isinstance(result, tuple)
        assert len(result) == 4

    async def test_verify_presentation(self):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    return_value=GetCredDefResult(
                        credential_definition_id="cred-def-id",
                        credential_definition=CredDef(
                            issuer_id="did:indy:sovrin:SGrjRL82Y9ZZbzhUDXokvQ",
                            schema_id="schema-id",
                            tag="tag",
                            type="CL",
                            value=CredDefValue(
                                primary=CredDefValuePrimary("n", "s", {}, "rctxt", "z")
                            ),
                        ),
                        credential_definition_metadata={},
                        resolution_metadata={},
                    )
                )
            )
        )
        result = await self.verifier.verify_presentation(
            pres_req=MOCK_PRES_REQ,
            pres=MOCK_PRES,
            schemas=MOCK_SCHEMAS,
            credential_definitions=MOCK_CRED_DEFS,
            rev_reg_defs=[],
            rev_lists={},
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] is False

    @mock.patch.object(
        test_module.AnonCredsVerifier, "pre_verify", side_effect=ValueError()
    )
    async def test_verify_presentation_value_error_caught(self, mock_verify):
        self.profile.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    side_effect=ValueError("Bad credential definition")
                )
            )
        )
        (result, msgs) = await self.verifier.verify_presentation(
            pres_req=MOCK_PRES_REQ,
            pres=MOCK_PRES,
            schemas=MOCK_SCHEMAS,
            credential_definitions=MOCK_CRED_DEFS,
            rev_reg_defs=[],
            rev_lists={},
        )
        assert result is False
        assert isinstance(msgs, list)
