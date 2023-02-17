import asyncio
from copy import deepcopy
from datetime import datetime
from typing import Sequence
from uuid import uuid4

import mock as async_mock
import pytest

from aries_cloudagent.wallet.key_type import BLS12381G2, ED25519

from .....core.in_memory import InMemoryProfile
from .....did.did_key import DIDKey
from .....resolver.did_resolver import DIDResolver
from .....storage.vc_holder.vc_record import VCRecord
from .....wallet.base import BaseWallet, DIDInfo
from .....wallet.crypto import KeyType
from .....wallet.did_method import SOV, KEY, DIDMethods
from .....wallet.error import WalletNotFoundError
from .....vc.ld_proofs import (
    BbsBlsSignature2020,
)
from .....vc.ld_proofs.document_loader import DocumentLoader
from .....vc.ld_proofs.error import LinkedDataProofException
from .....vc.ld_proofs.constants import SECURITY_CONTEXT_BBS_URL
from .....vc.tests.document_loader import custom_document_loader
from .....vc.tests.data import (
    BBS_SIGNED_VC_MATTR,
)

from .. import pres_exch_handler as test_module
from ..pres_exch import (
    PresentationDefinition,
    Requirement,
    Filter,
    SchemaInputDescriptor,
    SchemasInputDescriptorFilter,
    Constraints,
    DIFField,
)
from ..pres_exch_handler import (
    DIFPresExchHandler,
    DIFPresExchError,
)

from .test_data import (
    get_test_data,
    edd_jsonld_creds,
    bbs_bls_number_filter_creds,
    bbs_signed_cred_no_credsubjectid,
    bbs_signed_cred_credsubjectid,
    creds_with_no_id,
    is_holder_pd,
    is_holder_pd_multiple_fields_excluded,
    is_holder_pd_multiple_fields_included,
    EXPANDED_CRED_FHIR_TYPE_1,
    EXPANDED_CRED_FHIR_TYPE_2,
    TEST_CRED_DICT,
    TEST_CRED_WILDCARD,
)


@pytest.fixture(scope="class")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="class")
def profile():
    profile = InMemoryProfile.test_profile(bind={DIDMethods: DIDMethods()})
    context = profile.context
    context.injector.bind_instance(DIDResolver, DIDResolver([]))
    context.injector.bind_instance(DocumentLoader, custom_document_loader)
    context.settings["debug.auto_respond_presentation_request"] = True
    return profile


@pytest.fixture(scope="class")
async def setup_tuple(profile):
    async with profile.session() as session:
        wallet = session.inject_or(BaseWallet)
        await wallet.create_local_did(
            method=SOV, key_type=ED25519, did="WgWxqztrNooG92RXvxSTWv"
        )
        await wallet.create_local_did(
            method=KEY,
            key_type=BLS12381G2,
        )
        creds, pds = get_test_data()
        return creds, pds


class TestPresExchHandler:
    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_load_cred_json_a(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        # assert len(cred_list) == 6
        for tmp_pd in pd_list:
            # tmp_pd is tuple of presentation_definition and expected number of VCs
            tmp_vp = await dif_pres_exch_handler.create_vp(
                credentials=cred_list,
                pd=tmp_pd[0],
                challenge="1f44d55f-f161-4938-a659-f8026467f126",
            )

            if isinstance(tmp_vp, Sequence):
                cred_count_list = []
                for tmp_vp_single in tmp_vp:
                    cred_count_list.append(
                        len(tmp_vp_single.get("verifiableCredential"))
                    )

                assert min(cred_count_list) == tmp_pd[1]
            else:
                assert len(tmp_vp.get("verifiableCredential")) == tmp_pd[1]

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_load_cred_json_b(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, pres_signing_did="did:sov:WgWxqztrNooG92RXvxSTWv"
        )
        # assert len(cred_list) == 6
        for tmp_pd in pd_list:
            # tmp_pd is tuple of presentation_definition and expected number of VCs
            tmp_vp = await dif_pres_exch_handler.create_vp(
                credentials=cred_list,
                pd=tmp_pd[0],
                challenge="1f44d55f-f161-4938-a659-f8026467f126",
            )

            if isinstance(tmp_vp, Sequence):
                cred_count_list = []
                for tmp_vp_single in tmp_vp:
                    cred_count_list.append(
                        len(tmp_vp_single.get("verifiableCredential"))
                    )

                assert min(cred_count_list) == tmp_pd[1]
            else:
                assert len(tmp_vp.get("verifiableCredential")) == tmp_pd[1]

    @pytest.mark.asyncio
    async def test_to_requirement_catch_errors(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_json_pd = """
            {
                "submission_requirements": [
                    {
                        "name": "Banking Information",
                        "purpose": "We need you to prove you currently hold a bank account older than 12months.",
                        "rule": "pick",
                        "count": 1,
                        "from": "A"
                    }
                ],
                "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
                "input_descriptors": [
                    {
                        "id": "banking_input_1",
                        "name": "Bank Account Information",
                        "purpose": "We can only remit payment to a currently-valid bank account.",
                        "group": [
                            "B"
                        ],
                        "schema": [
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints": {
                            "fields": [
                                {
                                    "path": [
                                        "$.issuer.id",
                                        "$.vc.issuer.id"
                                    ],
                                    "purpose": "We can only verify bank accounts if they are attested by a trusted bank, auditor or regulatory authority.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "did:example:489398593"
                                    }
                                },
                                {
                                    "path": [
                                        "$.credentialSubject.account[*].route",
                                        "$.vc.credentialSubject.account[*].route",
                                        "$.account[*].route"
                                    ],
                                    "purpose": "We can only remit payment to a currently-valid account at a US, Japanese, or German federally-accredited bank, submitted as an ABA RTN or SWIFT code.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "^[0-9]{9}|^([a-zA-Z]){4}([a-zA-Z]){2}([0-9a-zA-Z]){2}([0-9a-zA-Z]{3})?$"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        with pytest.raises(DIFPresExchError):
            test_pd = PresentationDefinition.deserialize(test_json_pd)
            await dif_pres_exch_handler.make_requirement(
                srs=test_pd.submission_requirements,
                descriptors=test_pd.input_descriptors,
            )

        test_json_pd_nested_srs = """
            {
                "submission_requirements": [
                    {
                        "name": "Citizenship Information",
                        "rule": "pick",
                        "max": 3,
                        "from_nested": [
                            {
                                "name": "United States Citizenship Proofs",
                                "purpose": "We need you to prove your US citizenship.",
                                "rule": "all",
                                "from": "C"
                            },
                            {
                                "name": "European Union Citizenship Proofs",
                                "purpose": "We need you to prove you are a citizen of an EU member state.",
                                "rule": "all",
                                "from": "D"
                            }
                        ]
                    }
                ],
                "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
                "input_descriptors": [
                    {
                        "id": "banking_input_1",
                        "name": "Bank Account Information",
                        "purpose": "We can only remit payment to a currently-valid bank account.",
                        "group": [
                            "B"
                        ],
                        "schema": [
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints": {
                            "fields": [
                                {
                                    "path": [
                                        "$.issuer.id",
                                        "$.vc.issuer.id"
                                    ],
                                    "purpose": "We can only verify bank accounts if they are attested by a trusted bank, auditor or regulatory authority.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "did:example:489398593"
                                    }
                                },
                                {
                                    "path": [
                                        "$.credentialSubject.account[*].route",
                                        "$.vc.credentialSubject.account[*].route",
                                        "$.account[*].route"
                                    ],
                                    "purpose": "We can only remit payment to a currently-valid account at a US, Japanese, or German federally-accredited bank, submitted as an ABA RTN or SWIFT code.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "^[0-9]{9}|^([a-zA-Z]){4}([a-zA-Z]){2}([0-9a-zA-Z]){2}([0-9a-zA-Z]{3})?$"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        with pytest.raises(DIFPresExchError):
            test_pd = PresentationDefinition.deserialize(test_json_pd_nested_srs)
            await dif_pres_exch_handler.make_requirement(
                srs=test_pd.submission_requirements,
                descriptors=test_pd.input_descriptors,
            )

    @pytest.mark.asyncio
    async def test_make_requirement_with_none_params(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_json_pd_no_sr = """
            {
                "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
                "input_descriptors": [
                    {
                        "id": "banking_input_1",
                        "name": "Bank Account Information",
                        "purpose": "We can only remit payment to a currently-valid bank account.",
                        "group": [
                            "B"
                        ],
                        "schema": [
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints": {
                            "fields": [
                                {
                                    "path": [
                                        "$.issuer.id",
                                        "$.vc.issuer.id"
                                    ],
                                    "purpose": "We can only verify bank accounts if they are attested by a trusted bank, auditor or regulatory authority.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "did:example:489398593"
                                    }
                                },
                                {
                                    "path": [
                                        "$.credentialSubject.account[*].route",
                                        "$.vc.credentialSubject.account[*].route",
                                        "$.account[*].route"
                                    ],
                                    "purpose": "We can only remit payment to a currently-valid account at a US, Japanese, or German federally-accredited bank, submitted as an ABA RTN or SWIFT code.",
                                    "filter": {
                                        "type": "string",
                                        "pattern": "^[0-9]{9}|^([a-zA-Z]){4}([a-zA-Z]){2}([0-9a-zA-Z]){2}([0-9a-zA-Z]{3})?$"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        test_pd = PresentationDefinition.deserialize(test_json_pd_no_sr)
        assert test_pd.submission_requirements is None
        await dif_pres_exch_handler.make_requirement(
            srs=test_pd.submission_requirements, descriptors=test_pd.input_descriptors
        )

        test_json_pd_no_input_desc = """
            {
                "submission_requirements": [
                    {
                        "name": "Banking Information",
                        "purpose": "We need you to prove you currently hold a bank account older than 12months.",
                        "rule": "pick",
                        "count": 1,
                        "from": "A"
                    }
                ],
                "id": "32f54163-7166-48f1-93d8-ff217bdb0653"
            }
        """

        with pytest.raises(DIFPresExchError):
            test_pd = PresentationDefinition.deserialize(test_json_pd_no_input_desc)
            await dif_pres_exch_handler.make_requirement(
                srs=test_pd.submission_requirements,
                descriptors=test_pd.input_descriptors,
            )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_subject_is_issuer_check(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                    "name": "Citizenship Information",
                    "rule": "pick",
                    "min": 1,
                    "from": "A"
                    },
                    {
                    "name": "European Union Citizenship Proofs",
                    "rule": "all",
                    "from": "B"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "subject_is_issuer": "required",
                            "fields":[
                                {
                                    "path":[
                                        "$.issuer.id",
                                        "$.vc.issuer.id"
                                    ],
                                    "purpose":"The claim must be from one of the specified issuers",
                                    "filter":{
                                        "type":"string",
                                        "enum": ["did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa", "did:example:489398593", "did:sov:2wJPyULfLLnYTEFYzByfUR"]
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "id":"citizenship_input_2",
                        "name":"US Passport",
                        "group":[
                            "B"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.issuanceDate",
                                        "$.vc.issuanceDate"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "format":"date",
                                        "minimum":"2009-5-16"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=PresentationDefinition.deserialize(test_pd),
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_limit_disclosure_required_check(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                    "name": "Citizenship Information",
                    "rule": "pick",
                    "min": 1,
                    "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "limit_disclosure": "required",
                            "fields":[
                                {
                                    "path":[
                                        "$.credentialSubject.givenName"
                                    ],
                                    "purpose":"The claim must be from one of the specified issuers",
                                    "filter":{
                                        "type":"string",
                                        "enum": ["JOHN", "CAI"]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd)
        assert tmp_pd.input_descriptors[0].constraint.limit_disclosure
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 1
        for cred in tmp_vp.get("verifiableCredential"):
            assert cred["issuer"] in [
                "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
                "did:example:489398593",
                "did:sov:2wJPyULfLLnYTEFYzByfUR",
            ]
            assert cred["proof"]["type"] == "BbsBlsSignatureProof2020"

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_reveal_doc_with_frame_provided(self, profile):
        reveal_doc_frame = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "type": ["VerifiableCredential", "LabReport"],
            "@explicit": True,
            "@requireAll": True,
            "issuanceDate": {},
            "issuer": {},
            "credentialSubject": {
                "Observation": [
                    {"effectiveDateTime": {}, "@explicit": True, "@requireAll": True}
                ],
                "@explicit": True,
                "@requireAll": True,
            },
        }
        dif_pres_exch_handler = DIFPresExchHandler(profile, reveal_doc=reveal_doc_frame)
        test_constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.givenName"],
                    "filter": {"type": "string", "const": "JOHN"},
                },
                {
                    "path": ["$.credentialSubject.familyName"],
                    "filter": {"type": "string", "const": "SMITH"},
                },
                {
                    "path": ["$.credentialSubject.type"],
                    "filter": {
                        "type": "string",
                        "enum": ["PermanentResident", "Person"],
                    },
                },
                {
                    "path": ["$.credentialSubject.gender"],
                    "filter": {"type": "string", "const": "Male"},
                },
            ],
        }

        test_constraint = Constraints.deserialize(test_constraint)
        tmp_reveal_doc = dif_pres_exch_handler.reveal_doc(
            credential_dict=BBS_SIGNED_VC_MATTR, constraints=test_constraint
        )
        assert tmp_reveal_doc == reveal_doc_frame

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_reveal_doc_a(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.givenName"],
                    "filter": {"type": "string", "const": "JOHN"},
                },
                {
                    "path": ["$.credentialSubject.familyName"],
                    "filter": {"type": "string", "const": "SMITH"},
                },
                {
                    "path": ["$.credentialSubject.type"],
                    "filter": {
                        "type": "string",
                        "enum": ["PermanentResident", "Person"],
                    },
                },
                {
                    "path": ["$.credentialSubject.gender"],
                    "filter": {"type": "string", "const": "Male"},
                },
            ],
        }

        test_constraint = Constraints.deserialize(test_constraint)
        tmp_reveal_doc = dif_pres_exch_handler.reveal_doc(
            credential_dict=BBS_SIGNED_VC_MATTR, constraints=test_constraint
        )
        assert tmp_reveal_doc

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_reveal_doc_b(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_credential = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://example.gov/credentials/3732",
            "issuer": "did:example:489398593",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuanceDate": "2020-03-10T04:24:12.164Z",
            "credentialSubject": {
                "id": "did:example:b34ca6cd37bbf23",
                "degree": {
                    "type": "BachelorDegree",
                    "name": "Bachelor of Science and Arts",
                    "degreeType": "Underwater Basket Weaving",
                },
                "college": "Contoso University",
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
                "created": "2021-04-14T15:56:26.427788",
                "proofPurpose": "assertionMethod",
                "proofValue": "q86pBug3pGMMXq0RE6jfQnk8HaIfM4lb9dQAnKM4aUkT64x/f/65tfnzooeVPf+vXR9a2TVParet6RKWVHVb1QB+GJMWglBy29iEz2tK8H8qYqLtRHMA3YCAQ/aynHKekSsURq+1c2RTEsX27G0hVA==",
            },
        }

        test_constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.degree.name"],
                    "filter": {
                        "type": "string",
                        "const": "Bachelor of Science and Arts",
                    },
                },
                {
                    "path": ["$.issuer"],
                    "filter": {
                        "type": "string",
                        "const": "did:example:489398593",
                    },
                },
                {
                    "path": ["$.issuanceDate"],
                    "filter": {
                        "type": "string",
                        "const": "2020-03-10T04:24:12.164Z",
                    },
                },
            ],
        }
        test_constraint = Constraints.deserialize(test_constraint)
        tmp_reveal_doc = dif_pres_exch_handler.reveal_doc(
            credential_dict=test_credential, constraints=test_constraint
        )
        expected_reveal_doc = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "issuer": {},
            "issuanceDate": {},
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "@explicit": True,
            "@requireAll": True,
            "credentialSubject": {
                "@explicit": True,
                "@requireAll": True,
                "degree": {"@explicit": True, "@requireAll": True, "name": {}},
            },
        }
        assert tmp_reveal_doc == expected_reveal_doc

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_reveal_doc_c(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.givenName"],
                    "filter": {"type": "string", "const": "Cai"},
                },
                {
                    "path": ["$.credentialSubject.familyName"],
                    "filter": {"type": "string", "const": "Leblanc"},
                },
                {
                    "path": ["$.credentialSubject.gender"],
                    "filter": {"type": "string", "const": "Male"},
                },
            ],
        }

        test_constraint = Constraints.deserialize(test_constraint)
        test_cred = cred_list[2].cred_value
        tmp_reveal_doc = dif_pres_exch_handler.reveal_doc(
            credential_dict=test_cred, constraints=test_constraint
        )
        assert tmp_reveal_doc

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_reveal_doc_wildcard(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Observation[*].effectiveDateTime"],
                    "id": "Observation_effectiveDateTime",
                    "purpose": "Време узимања узорка",
                }
            ],
        }

        test_constraint = Constraints.deserialize(test_constraint)
        tmp_reveal_doc = dif_pres_exch_handler.reveal_doc(
            credential_dict=TEST_CRED_WILDCARD, constraints=test_constraint
        )
        assert tmp_reveal_doc

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_filter_number_type_check(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd_min = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "maximum": 2
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_min)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_bls_number_filter_creds,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 2
        test_pd_max = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "minimum": 2
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_max)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_bls_number_filter_creds,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 3

        test_pd_excl_min = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints":{
                        "limit_disclosure": "preferred",
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "exclusiveMinimum": 1.5
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_excl_min)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_bls_number_filter_creds,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 3

        test_pd_excl_max = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "exclusiveMaximum": 2.5
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_excl_max)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_bls_number_filter_creds,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 2

        test_pd_const = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "const": 2
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_const)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_bls_number_filter_creds,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 2

        test_pd_enum = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "enum": [2, 2.0 , "test"]
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_enum)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_bls_number_filter_creds,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 2

        test_pd_missing = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "type": "number",
                                    "enum": [2.5]
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_missing)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_bls_number_filter_creds,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 0

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_filter_no_type_check(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.lprCategory",
                                    "$.vc.credentialSubject.lprCategory",
                                    "$.test"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{  
                                    "not": {
                                        "const": "C10"
                                    }
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_edd_limit_disclosure(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                    "name": "Citizenship Information",
                    "rule": "pick",
                    "min": 1,
                    "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "limit_disclosure": "required",
                            "fields":[
                                {
                                    "path":[
                                        "$.issuer.id",
                                        "$.issuer",
                                        "$.vc.issuer.id"
                                    ],
                                    "purpose":"The claim must be from one of the specified issuers",
                                    "filter":{
                                        "enum": ["did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa", "did:example:489398593"]
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd)
        assert tmp_pd.input_descriptors[0].constraint.limit_disclosure
        with pytest.raises(LinkedDataProofException):
            await dif_pres_exch_handler.create_vp(
                credentials=edd_jsonld_creds,
                pd=tmp_pd,
                challenge="1f44d55f-f161-4938-a659-f8026467f126",
            )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_edd_jsonld_creds(self, setup_tuple, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd_const_check = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.vc.issuer.id",
                                        "$.issuer",
                                        "$.issuer.id"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "const": "did:example:489398593"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_const_check)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=edd_jsonld_creds,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 3

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_filter_string(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd_min_length = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.vc.issuer.id",
                                        "$.issuer",
                                        "$.issuer.id"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "minLength": 5
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_min_length)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6

        test_pd_max_length = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.issuer.id",
                                        "$.issuer",
                                        "$.vc.issuer.id"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "maxLength": 150
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_max_length)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6

        test_pd_pattern_check = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.vc.issuer.id",
                                        "$.issuer",
                                        "$.issuer.id"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "pattern": "did:example:test"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_pattern_check)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 0

        test_pd_datetime_exclmax = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.issuanceDate",
                                        "$.vc.issuanceDate"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "format":"date",
                                        "exclusiveMaximum":"2011-5-16"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_datetime_exclmax)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6

        test_pd_datetime_exclmin = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.issuanceDate",
                                        "$.vc.issuanceDate"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "format":"date",
                                        "exclusiveMinimum":"2008-5-16"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_datetime_exclmin)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6

        test_pd_const_check = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.vc.issuer.id",
                                        "$.issuer",
                                        "$.issuer.id"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "const": "did:example:489398593"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_const_check)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 1

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_filter_schema(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        tmp_schema_list = SchemasInputDescriptorFilter(
            oneof_filter=True,
            uri_groups=[
                [
                    SchemaInputDescriptor(
                        uri="test123",
                        required=True,
                    ),
                    SchemaInputDescriptor(uri="test321"),
                ],
                [SchemaInputDescriptor(uri="test789")],
            ],
        )
        assert (
            len(await dif_pres_exch_handler.filter_schema(cred_list, tmp_schema_list))
            == 0
        )

    @pytest.mark.ursa_bbs_signatures
    def test_cred_schema_match_a(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        tmp_cred = deepcopy(cred_list[0])
        assert (
            dif_pres_exch_handler.credential_match_schema(
                tmp_cred, "https://www.w3.org/2018/credentials#VerifiableCredential"
            )
            is True
        )

    @pytest.mark.ursa_bbs_signatures
    @pytest.mark.asyncio
    async def test_merge_nested(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_nested_result = []
        test_dict_1 = {}
        test_dict_1["citizenship_input_1"] = [
            cred_list[0],
            cred_list[1],
            cred_list[2],
            cred_list[3],
            cred_list[4],
            cred_list[5],
        ]
        test_dict_2 = {}
        test_dict_2["citizenship_input_2"] = [
            cred_list[4],
            cred_list[5],
        ]
        test_dict_3 = {}
        test_dict_3["citizenship_input_2"] = [
            cred_list[3],
            cred_list[2],
        ]
        test_nested_result.append(test_dict_1)
        test_nested_result.append(test_dict_2)
        test_nested_result.append(test_dict_3)

        tmp_result = await dif_pres_exch_handler.merge_nested_results(
            test_nested_result, {}
        )

    @pytest.mark.asyncio
    async def test_merge_nested_cred_no_id(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        cred_list = deepcopy(creds_with_no_id)
        cred_list[0].record_id = str(uuid4())
        cred_list[1].record_id = str(uuid4())
        test_nested_result = []
        test_dict_1 = {}
        test_dict_1["citizenship_input_1"] = [
            cred_list[0],
            cred_list[1],
        ]
        test_dict_2 = {}
        test_dict_2["citizenship_input_2"] = [
            cred_list[0],
        ]
        test_dict_3 = {}
        test_dict_3["citizenship_input_2"] = [
            cred_list[0],
            cred_list[1],
        ]
        test_nested_result.append(test_dict_1)
        test_nested_result.append(test_dict_2)
        test_nested_result.append(test_dict_3)

        tmp_result = await dif_pres_exch_handler.merge_nested_results(
            test_nested_result, {}
        )

    @pytest.mark.ursa_bbs_signatures
    def test_subject_is_issuer(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        tmp_cred = deepcopy(cred_list[0])
        tmp_cred.issuer_id = "4fc82e63-f897-4dad-99cc-f698dff6c425"
        tmp_cred.subject_ids.add("4fc82e63-f897-4dad-99cc-f698dff6c425")
        assert tmp_cred.subject_ids is not None
        assert dif_pres_exch_handler.subject_is_issuer(tmp_cred) is True
        tmp_cred.issuer_id = "19b823fb-55ef-49f4-8caf-2a26b8b9286f"
        assert dif_pres_exch_handler.subject_is_issuer(tmp_cred) is False

    def test_is_numeric(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        with pytest.raises(DIFPresExchError):
            dif_pres_exch_handler.is_numeric("test")
        assert dif_pres_exch_handler.is_numeric(1) == 1
        assert dif_pres_exch_handler.is_numeric(2.20) == 2.20
        assert dif_pres_exch_handler.is_numeric("2.20") == 2.20
        assert dif_pres_exch_handler.is_numeric("2") == 2
        with pytest.raises(DIFPresExchError):
            dif_pres_exch_handler.is_numeric(2 + 3j)

    def test_filter_no_match(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        tmp_filter_excl_min = Filter(exclusive_min=7)
        assert (
            dif_pres_exch_handler.exclusive_minimum_check("test", tmp_filter_excl_min)
            is False
        )
        tmp_filter_excl_max = Filter(exclusive_max=10)
        assert (
            dif_pres_exch_handler.exclusive_maximum_check("test", tmp_filter_excl_max)
            is False
        )
        tmp_filter_min = Filter(minimum=10)
        assert dif_pres_exch_handler.minimum_check("test", tmp_filter_min) is False
        tmp_filter_max = Filter(maximum=10)
        assert dif_pres_exch_handler.maximum_check("test", tmp_filter_max) is False

    def test_filter_valueerror(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        tmp_filter_excl_min = Filter(exclusive_min=7, fmt="date")
        assert (
            dif_pres_exch_handler.exclusive_minimum_check("test", tmp_filter_excl_min)
            is False
        )
        tmp_filter_excl_max = Filter(exclusive_max=10, fmt="date")
        assert (
            dif_pres_exch_handler.exclusive_maximum_check("test", tmp_filter_excl_max)
            is False
        )
        tmp_filter_min = Filter(minimum=10, fmt="date")
        assert dif_pres_exch_handler.minimum_check("test", tmp_filter_min) is False
        tmp_filter_max = Filter(maximum=10, fmt="date")
        assert dif_pres_exch_handler.maximum_check("test", tmp_filter_max) is False

    def test_filter_length_check(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        tmp_filter_both = Filter(min_length=7, max_length=10)
        assert dif_pres_exch_handler.length_check("test12345", tmp_filter_both) is True
        tmp_filter_min = Filter(min_length=7)
        assert dif_pres_exch_handler.length_check("test123", tmp_filter_min) is True
        tmp_filter_max = Filter(max_length=10)
        assert dif_pres_exch_handler.length_check("test", tmp_filter_max) is True
        assert dif_pres_exch_handler.length_check("test12", tmp_filter_min) is False

    def test_filter_pattern_check(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        tmp_filter = Filter(pattern="test1|test2")
        assert dif_pres_exch_handler.pattern_check("test3", tmp_filter) is False
        tmp_filter = Filter(const="test3")
        assert dif_pres_exch_handler.pattern_check("test3", tmp_filter) is False

    def test_is_len_applicable(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        tmp_req_a = Requirement(count=1)
        tmp_req_b = Requirement(minimum=3)
        tmp_req_c = Requirement(maximum=5)

        assert dif_pres_exch_handler.is_len_applicable(tmp_req_a, 2) is False
        assert dif_pres_exch_handler.is_len_applicable(tmp_req_b, 2) is False
        assert dif_pres_exch_handler.is_len_applicable(tmp_req_c, 6) is False

    def test_create_vcrecord(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_cred_dict = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            "id": "http://example.edu/credentials/3732",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": {"id": "https://example.edu/issuers/14"},
            "issuanceDate": "2010-01-01T19:23:24Z",
            "credentialSubject": {
                "id": "did:example:b34ca6cd37bbf23",
                "degree": {
                    "type": "BachelorDegree",
                    "name": "Bachelor of Science and Arts",
                },
            },
            "credentialSchema": {
                "id": "https://example.org/examples/degree.json",
                "type": "JsonSchemaValidator2018",
            },
        }
        test_vcrecord = dif_pres_exch_handler.create_vcrecord(test_cred_dict)
        assert isinstance(test_vcrecord, VCRecord)

    @pytest.mark.asyncio
    async def test_reveal_doc_d(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, pres_signing_did="did:example:b34ca6cd37bbf23"
        )
        test_constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.accounts[*].accountnumber"],
                    "filter": {"type": "string", "const": "test"},
                }
            ],
        }
        test_cred_dict = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627465",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2019-12-03T12:19:52Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:example:b34ca6cd37bbf23",
                "accounts": [
                    {"accountnumber": "test"},
                    {"accountnumber": "test"},
                    {"accountnumber": "test"},
                ],
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "created": "2020-10-16T23:59:31Z",
                "proofPurpose": "assertionMethod",
                "proofValue": "kAkloZSlK79ARnlx54tPqmQyy6G7/36xU/LZgrdVmCqqI9M0muKLxkaHNsgVDBBvYp85VT3uouLFSXPMr7Stjgq62+OCunba7bNdGfhM/FUsx9zpfRtw7jeE182CN1cZakOoSVsQz61c16zQikXM3w==",
                "verificationMethod": "did:example:489398593#test",
            },
        }
        test_constraint = Constraints.deserialize(test_constraint)
        tmp_reveal_doc = dif_pres_exch_handler.reveal_doc(
            credential_dict=test_cred_dict, constraints=test_constraint
        )
        assert tmp_reveal_doc

    @pytest.mark.asyncio
    async def test_credential_subject_as_list(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        with async_mock.patch.object(
            dif_pres_exch_handler, "new_credential_builder", autospec=True
        ) as mock_cred_builder:
            mock_cred_builder.return_value = {}
            dif_pres_exch_handler.reveal_doc(
                {"credentialSubject": []}, Constraints(_fields=[])
            )

    def test_invalid_number_filter(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        assert not dif_pres_exch_handler.process_numeric_val(val=2, _filter=Filter())

    def test_invalid_string_filter(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        assert not dif_pres_exch_handler.process_string_val(
            val="test", _filter=Filter()
        )

    @pytest.mark.ursa_bbs_signatures
    def test_cred_schema_match_b(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        cred_list, pd_list = setup_tuple
        test_cred = deepcopy(cred_list[0])
        test_cred.schema_ids = ["https://example.org/examples/degree.json"]
        assert dif_pres_exch_handler.credential_match_schema(
            test_cred, "https://example.org/examples/degree.json"
        )

    def test_verification_method(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        assert (
            dif_pres_exch_handler._get_verification_method(
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            )
            == DIDKey.from_did(
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ).key_id
        )
        with pytest.raises(DIFPresExchError):
            dif_pres_exch_handler._get_verification_method("did:test:test")

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_sign_pres_no_cred_subject_id(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, pres_signing_did="did:sov:WgWxqztrNooG92RXvxSTWv"
        )
        cred_list, pd_list = setup_tuple
        tmp_pd = pd_list[3]
        tmp_creds = []
        for cred in deepcopy(cred_list):
            cred.subject_ids = []
            tmp_creds.append(cred)

        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=tmp_creds,
            pd=tmp_pd[0],
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_sign_pres_bbsbls(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_list, pd_list = setup_tuple
        tmp_pd = pd_list[3]
        tmp_creds = []
        for cred in deepcopy(cred_list):
            cred.subject_ids = []
            tmp_creds.append(cred)

        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=tmp_creds,
            pd=tmp_pd[0],
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6

    def test_create_vc_record_with_graph_struct(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_credential_dict_a = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "@graph": [
                {
                    "id": "did:key:zUC79Dfc18UM9HWQKmqonstuwcP4Fu3V9Zy7aNrcFU6K34WzkBesnm9LhaVxMtrqy2qrgkRyKVoFXsE1BJFAgrzhavrYBQ69AWTcgmBFQ1VauGGCJJKvDaaWfRqgtM3DQzx1TpM",
                    "type": "PermanentResident",
                    "https://www.w3.org/2018/credentials#credentialSubject": "",
                    "https://www.w3.org/2018/credentials#issuanceDate": "",
                    "https://www.w3.org/2018/credentials#issuer": "",
                },
                {
                    "id": "urn:bnid:_:c14n0",
                    "type": ["PermanentResident", "VerifiableCredential"],
                    "credentialSubject": {
                        "id": "did:key:zUC79Dfc18UM9HWQKmqonstuwcP4Fu3V9Zy7aNrcFU6K34WzkBesnm9LhaVxMtrqy2qrgkRyKVoFXsE1BJFAgrzhavrYBQ69AWTcgmBFQ1VauGGCJJKvDaaWfRqgtM3DQzx1TpM",
                        "type": "PermanentResident",
                        "familyName": "SMITH",
                    },
                    "issuanceDate": "2020-01-01T12:00:00Z",
                    "issuer": "did:key:zUC7GLSYyPCryDnWzBgrSu4x44NH7bqEvY8dVPdWii1zdi3GTT9wsmTavEUfgd6VZ6wuz6yx7EDvT23DcxRT5oPBjEt3LYYAi1ph63NWxoGLCjwcP8XAHWRTCR1TKyVak4eLsjD",
                },
            ],
            "proof": {
                "type": "BbsBlsSignatureProof2020",
                "nonce": "4xEz2oZQdiyDI5WE5snXQnvQQSfBZMyrmc9PtjDRTdnzV0GdT9tDgEJhFhseP5fJTeY=",
                "proofValue": "AA99L7TriEaSJ3iTDZJhrwHz/pkPLYPFFtJQuiUy/IHLIuhcdkSPhKtXGDfe6pmng+nE9pc969b6qghh/T1RjEBF7B+J9uBaWyEz0C57OV22ts+ejB/Cn4/I/jyqryzmpSzF8IvwhhtaRl31JVxnBd7bmfLZAX6FW+ZxopSepH/2sxZKpfV2Ntafx0qNfMRmt8sMrwAAAHSW5bC0H37sdQRCvwhuSwKm9xAq81saAPnUR393bspYzkC0OUNaRzsN4W/oF7db250AAAACXRj8cmq12t5N0iklCp7s2ujTP5Yemp0qERGsDaeNb0Fh6tGzhP5QJHbiNY8i/scBIMN4bN0nX2HM2grkRKMxErOO0sirH6MMz90XFOs2pxJxh33MZ0Qp0CTff6YT/Cjd0FO4SBs4ZuUzdeoRI6FSoAAAAAZIlySGrOeIFVheqXONHu9WcwNnGi48KjL/EjLcDqJgCymARUsEW5XjNJSysUqFiibm221yYMaAskdQDHdoh0q5CtV8UeDCunycGMiphhIhcP9xtWW1+WY0gif0qxRMxNs4IpcJ7TtXse7zOysQrU0iXMLwA96yzGk722QZKnXXPEZMSduj+YPfMJnDR67uxJYUGx+ci8dqmEmFfNEzeq/DTKpJwbbNbeLVnd4GKHQB2WZwRfYwNYt2U+c/xCuxvew=",
                "verificationMethod": "did:key:zUC7GLSYyPCryDnWzBgrSu4x44NH7bqEvY8dVPdWii1zdi3GTT9wsmTavEUfgd6VZ6wuz6yx7EDvT23DcxRT5oPBjEt3LYYAi1ph63NWxoGLCjwcP8XAHWRTCR1TKyVak4eLsjD#zUC7GLSYyPCryDnWzBgrSu4x44NH7bqEvY8dVPdWii1zdi3GTT9wsmTavEUfgd6VZ6wuz6yx7EDvT23DcxRT5oPBjEt3LYYAi1ph63NWxoGLCjwcP8XAHWRTCR1TKyVak4eLsjD",
                "proofPurpose": "assertionMethod",
                "created": "2021-06-01T08:32:11.935336",
            },
        }
        test_credential_dict_b = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "@graph": [
                {
                    "id": "urn:bnid:_:c14n1",
                    "type": "PermanentResident",
                    "https://www.w3.org/2018/credentials#credentialSubject": "",
                    "https://www.w3.org/2018/credentials#issuanceDate": "",
                    "https://www.w3.org/2018/credentials#issuer": "",
                },
                {
                    "id": "urn:bnid:_:c14n0",
                    "type": ["PermanentResident", "VerifiableCredential"],
                    "credentialSubject": None,
                    "issuanceDate": "2020-01-01T12:00:00Z",
                    "issuer": "did:key:zUC7GLSYyPCryDnWzBgrSu4x44NH7bqEvY8dVPdWii1zdi3GTT9wsmTavEUfgd6VZ6wuz6yx7EDvT23DcxRT5oPBjEt3LYYAi1ph63NWxoGLCjwcP8XAHWRTCR1TKyVak4eLsjD",
                },
            ],
            "proof": {
                "type": "BbsBlsSignatureProof2020",
                "nonce": "4xEz2oZQdiyDI5WE5snXQnvQQSfBZMyrmc9PtjDRTdnzV0GdT9tDgEJhFhseP5fJTeY=",
                "proofValue": "AA99L7TriEaSJ3iTDZJhrwHz/pkPLYPFFtJQuiUy/IHLIuhcdkSPhKtXGDfe6pmng+nE9pc969b6qghh/T1RjEBF7B+J9uBaWyEz0C57OV22ts+ejB/Cn4/I/jyqryzmpSzF8IvwhhtaRl31JVxnBd7bmfLZAX6FW+ZxopSepH/2sxZKpfV2Ntafx0qNfMRmt8sMrwAAAHSW5bC0H37sdQRCvwhuSwKm9xAq81saAPnUR393bspYzkC0OUNaRzsN4W/oF7db250AAAACXRj8cmq12t5N0iklCp7s2ujTP5Yemp0qERGsDaeNb0Fh6tGzhP5QJHbiNY8i/scBIMN4bN0nX2HM2grkRKMxErOO0sirH6MMz90XFOs2pxJxh33MZ0Qp0CTff6YT/Cjd0FO4SBs4ZuUzdeoRI6FSoAAAAAZIlySGrOeIFVheqXONHu9WcwNnGi48KjL/EjLcDqJgCymARUsEW5XjNJSysUqFiibm221yYMaAskdQDHdoh0q5CtV8UeDCunycGMiphhIhcP9xtWW1+WY0gif0qxRMxNs4IpcJ7TtXse7zOysQrU0iXMLwA96yzGk722QZKnXXPEZMSduj+YPfMJnDR67uxJYUGx+ci8dqmEmFfNEzeq/DTKpJwbbNbeLVnd4GKHQB2WZwRfYwNYt2U+c/xCuxvew=",
                "verificationMethod": "did:key:zUC7GLSYyPCryDnWzBgrSu4x44NH7bqEvY8dVPdWii1zdi3GTT9wsmTavEUfgd6VZ6wuz6yx7EDvT23DcxRT5oPBjEt3LYYAi1ph63NWxoGLCjwcP8XAHWRTCR1TKyVak4eLsjD#zUC7GLSYyPCryDnWzBgrSu4x44NH7bqEvY8dVPdWii1zdi3GTT9wsmTavEUfgd6VZ6wuz6yx7EDvT23DcxRT5oPBjEt3LYYAi1ph63NWxoGLCjwcP8XAHWRTCR1TKyVak4eLsjD",
                "proofPurpose": "assertionMethod",
                "created": "2021-06-01T08:32:11.935336",
            },
        }
        assert isinstance(
            dif_pres_exch_handler.create_vcrecord(test_credential_dict_a), VCRecord
        )
        assert isinstance(
            dif_pres_exch_handler.create_vcrecord(test_credential_dict_b), VCRecord
        )

    @pytest.mark.asyncio
    async def test_get_did_info_for_did(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_did_key = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        with pytest.raises(WalletNotFoundError):
            await dif_pres_exch_handler._did_info_for_did(test_did_key)

    @pytest.mark.asyncio
    async def test_get_sign_key_credential_subject_id(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)

        VC_RECORDS = [
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=["did:sov:LjgpST2rjsoxYegQDRm7EL"],
                proof_types=["Ed25519Signature2018"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
            ),
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=[
                    "did:example:ebfeb1f712ebc6f1c276e12ec31",
                    "did:sov:LjgpST2rjsoxYegQDRm7EL",
                ],
                proof_types=["Ed25519Signature2018"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
            ),
        ]
        with async_mock.patch.object(
            DIFPresExchHandler,
            "_did_info_for_did",
            async_mock.AsyncMock(),
        ) as mock_did_info:
            did_info = DIDInfo(
                did="did:sov:LjgpST2rjsoxYegQDRm7EL",
                verkey="verkey",
                metadata={},
                method=SOV,
                key_type=ED25519,
            )
            mock_did_info.return_value = did_info
            (
                issuer_id,
                filtered_creds,
            ) = await dif_pres_exch_handler.get_sign_key_credential_subject_id(
                VC_RECORDS
            )
            assert issuer_id == "did:sov:LjgpST2rjsoxYegQDRm7EL"
            assert len(filtered_creds) == 2

    @pytest.mark.asyncio
    async def test_get_sign_key_credential_subject_id_error(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)

        VC_RECORDS = [
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=["did:sov:LjgpST2rjsoxYegQDRm7EL"],
                proof_types=["Ed25519Signature2018"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
            ),
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=[
                    "did:example:ebfeb1f712ebc6f1c276e12ec31",
                    "did:example:ebfeb1f712ebc6f1c276e12ec21",
                ],
                proof_types=["Ed25519Signature2018"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
            ),
        ]
        with async_mock.patch.object(
            DIFPresExchHandler,
            "_did_info_for_did",
            async_mock.AsyncMock(),
        ) as mock_did_info:
            did_info = DIDInfo(
                did="did:sov:LjgpST2rjsoxYegQDRm7EL",
                verkey="verkey",
                metadata={},
                method=SOV,
                key_type=ED25519,
            )
            mock_did_info.return_value = did_info
            with pytest.raises(DIFPresExchError):
                (
                    issuer_id,
                    filtered_creds,
                ) = await dif_pres_exch_handler.get_sign_key_credential_subject_id(
                    VC_RECORDS
                )

    @pytest.mark.asyncio
    async def test_get_sign_key_credential_subject_id_bbsbls(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type="BbsBlsSignature2020"
        )

        VC_RECORDS = [
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=[
                    "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                ],
                proof_types=["BbsBlsSignature2020"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
            ),
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=[
                    "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                ],
                proof_types=["BbsBlsSignature2020"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
            ),
        ]
        with async_mock.patch.object(
            DIFPresExchHandler,
            "_did_info_for_did",
            async_mock.AsyncMock(),
        ) as mock_did_info:
            did_info = DIDInfo(
                did="did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                verkey="verkey",
                metadata={},
                method=KEY,
                key_type=BLS12381G2,
            )
            mock_did_info.return_value = did_info
            (
                issuer_id,
                filtered_creds,
            ) = await dif_pres_exch_handler.get_sign_key_credential_subject_id(
                VC_RECORDS
            )
            assert (
                issuer_id == "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            )
            assert len(filtered_creds) == 2

    @pytest.mark.ursa_bbs_signatures
    @pytest.mark.asyncio
    async def test_create_vp_no_issuer(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        cred_list, pd_list = setup_tuple
        VC_RECORDS = [
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=[
                    "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                ],
                proof_types=["BbsBlsSignature2020"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
            ),
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=[
                    "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                ],
                proof_types=["BbsBlsSignature2020"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
            ),
        ]
        with async_mock.patch.object(
            DIFPresExchHandler,
            "_did_info_for_did",
            async_mock.AsyncMock(),
        ) as mock_did_info, async_mock.patch.object(
            DIFPresExchHandler,
            "make_requirement",
            async_mock.AsyncMock(),
        ) as mock_make_req, async_mock.patch.object(
            DIFPresExchHandler,
            "apply_requirements",
            async_mock.AsyncMock(),
        ) as mock_apply_req, async_mock.patch.object(
            DIFPresExchHandler,
            "merge",
            async_mock.AsyncMock(),
        ) as mock_merge, async_mock.patch.object(
            test_module,
            "create_presentation",
            async_mock.AsyncMock(),
        ) as mock_create_vp:
            mock_make_req.return_value = async_mock.MagicMock()
            mock_apply_req.return_value = async_mock.MagicMock()
            mock_merge.return_value = (VC_RECORDS, {})
            dif_pres_exch_handler.is_holder = True
            mock_create_vp.return_value = {"test": "1"}
            did_info = DIDInfo(
                did="did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                verkey="verkey",
                metadata={},
                method=KEY,
                key_type=BLS12381G2,
            )
            mock_did_info.return_value = did_info
            vp = await dif_pres_exch_handler.create_vp(
                VC_RECORDS,
                pd=pd_list[0][0],
                challenge="3fa85f64-5717-4562-b3fc-2c963f66afa7",
            )
            for vp_single in vp:
                assert vp_single["test"] == "1"
                assert (
                    vp_single["presentation_submission"]["definition_id"]
                    == "32f54163-7166-48f1-93d8-ff217bdb0653"
                )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_create_vp_with_bbs_suite(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_list, pd_list = setup_tuple
        with async_mock.patch.object(
            DIFPresExchHandler,
            "_did_info_for_did",
            async_mock.AsyncMock(),
        ) as mock_did_info, async_mock.patch.object(
            DIFPresExchHandler,
            "make_requirement",
            async_mock.AsyncMock(),
        ) as mock_make_req, async_mock.patch.object(
            DIFPresExchHandler,
            "apply_requirements",
            async_mock.AsyncMock(),
        ) as mock_apply_req, async_mock.patch.object(
            DIFPresExchHandler,
            "merge",
            async_mock.AsyncMock(),
        ) as mock_merge, async_mock.patch.object(
            test_module,
            "create_presentation",
            async_mock.AsyncMock(),
        ) as mock_create_vp, async_mock.patch.object(
            test_module,
            "sign_presentation",
            async_mock.AsyncMock(),
        ) as mock_sign_vp:
            mock_make_req.return_value = async_mock.MagicMock()
            mock_apply_req.return_value = async_mock.MagicMock()
            mock_merge.return_value = (cred_list, {})
            dif_pres_exch_handler.is_holder = True
            mock_create_vp.return_value = {"test": "1", "@context": ["test"]}
            mock_sign_vp.return_value = {
                "test": "1",
                "@context": ["test", SECURITY_CONTEXT_BBS_URL],
            }
            did_info = DIDInfo(
                did="did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                verkey="verkey",
                metadata={},
                method=KEY,
                key_type=BLS12381G2,
            )
            mock_did_info.return_value = did_info
            vp = await dif_pres_exch_handler.create_vp(
                cred_list,
                pd=pd_list[0][0],
                challenge="3fa85f64-5717-4562-b3fc-2c963f66afa7",
            )
            for vp_single in vp:
                assert vp_single["test"] == "1"
                assert SECURITY_CONTEXT_BBS_URL in vp_single["@context"]

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_create_vp_no_issuer_with_bbs_suite(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_list, pd_list = setup_tuple
        with async_mock.patch.object(
            DIFPresExchHandler,
            "_did_info_for_did",
            async_mock.AsyncMock(),
        ) as mock_did_info, async_mock.patch.object(
            DIFPresExchHandler,
            "make_requirement",
            async_mock.AsyncMock(),
        ) as mock_make_req, async_mock.patch.object(
            DIFPresExchHandler,
            "apply_requirements",
            async_mock.AsyncMock(),
        ) as mock_apply_req, async_mock.patch.object(
            DIFPresExchHandler,
            "merge",
            async_mock.AsyncMock(),
        ) as mock_merge, async_mock.patch.object(
            test_module,
            "create_presentation",
            async_mock.AsyncMock(),
        ) as mock_create_vp, async_mock.patch.object(
            DIFPresExchHandler,
            "get_sign_key_credential_subject_id",
            async_mock.AsyncMock(),
        ) as mock_sign_key_cred_subject:
            mock_make_req.return_value = async_mock.MagicMock()
            mock_apply_req.return_value = async_mock.MagicMock()
            mock_merge.return_value = (cred_list, {})
            dif_pres_exch_handler.is_holder = True
            mock_create_vp.return_value = {"test": "1", "@context": ["test"]}
            mock_sign_key_cred_subject.return_value = (None, [])
            did_info = DIDInfo(
                did="did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                verkey="verkey",
                metadata={},
                method=KEY,
                key_type=BLS12381G2,
            )
            mock_did_info.return_value = did_info
            vp = await dif_pres_exch_handler.create_vp(
                cred_list,
                pd=pd_list[0][0],
                challenge="3fa85f64-5717-4562-b3fc-2c963f66afa7",
            )
            # 2 sub_reqs, vp is a sequence
            for vp_single in vp:
                assert vp_single["test"] == "1"
                assert SECURITY_CONTEXT_BBS_URL in vp_single["@context"]

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_no_filter(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd_no_filter = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.issuanceDate",
                                        "$.vc.issuanceDate"
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
        """
        tmp_pd = PresentationDefinition.deserialize(test_pd_no_filter)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_filter_with_only_string_type(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd_filter_with_only_string_type = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.issuanceDate",
                                        "$.vc.issuanceDate"
                                    ],
                                    "filter":{
                                        "type":"string"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """
        tmp_pd = PresentationDefinition.deserialize(
            test_pd_filter_with_only_string_type
        )
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_filter_with_only_num_type(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd_filter_with_only_num_type = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "filter":{  
                                    "type": "number"
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """

        tmp_pd = PresentationDefinition.deserialize(test_pd_filter_with_only_num_type)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_bls_number_filter_creds,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 3

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_filter_with_only_string_type_with_format(self, setup_tuple, profile):
        cred_list, pd_list = setup_tuple
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd_filter_with_only_string_type_with_format = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.issuanceDate",
                                        "$.vc.issuanceDate"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "format":"date"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """
        tmp_pd = PresentationDefinition.deserialize(
            test_pd_filter_with_only_string_type_with_format
        )
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6

    def test_validate_patch_catch_errors(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        _filter = Filter(_type="string", fmt="date")
        _to_check = "test123"
        assert not dif_pres_exch_handler.validate_patch(
            to_check=_to_check, _filter=_filter
        )
        _to_check = 123
        assert not dif_pres_exch_handler.validate_patch(
            to_check=_to_check, _filter=_filter
        )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_derive_cred_missing_credsubjectid(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd = """
        {
            "id":"32f54163-7166-48f1-93d8-ff217bdb0654",
            "input_descriptors":[
                {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        },
                        {
                            "uri":"https://w3id.org/citizenship#PermanentResidentCard"
                        }
                    ],
                    "constraints":{
                        "limit_disclosure": "required",
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.familyName"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{
                                    "const": "SMITH"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        """
        tmp_pd = PresentationDefinition.deserialize(test_pd)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_signed_cred_no_credsubjectid,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp["verifiableCredential"]) == 2
        for tmp_vc in tmp_vp.get("verifiableCredential"):
            assert tmp_vc.get("credentialSubject").get("id").startswith("urn:")
            assert tmp_vc.get("credentialSubject").get("familyName") == "SMITH"

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_derive_cred_credsubjectid(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd = """
        {
            "id":"32f54163-7166-48f1-93d8-ff217bdb0654",
            "input_descriptors":[
                {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        },
                        {
                            "uri":"https://w3id.org/citizenship#PermanentResidentCard"
                        }
                    ],
                    "constraints":{
                        "limit_disclosure": "required",
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.familyName"
                                ],
                                "purpose":"The claim must be from one of the specified issuers",
                                "filter":{
                                    "const": "SMITH"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        """
        tmp_pd = PresentationDefinition.deserialize(test_pd)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_signed_cred_credsubjectid,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp["verifiableCredential"]) == 1
        assert "givenName" not in tmp_vp.get("verifiableCredential")[0].get(
            "credentialSubject"
        )
        assert (
            tmp_vp.get("verifiableCredential")[0].get("credentialSubject").get("id")
            == "did:sov:WgWxqztrNooG92RXvxSTWv"
        )
        assert (
            tmp_vp.get("verifiableCredential")[0]
            .get("credentialSubject")
            .get("familyName")
            == "SMITH"
        )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_derive_nested_cred_missing_credsubjectid_a(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd = """
        {
            "id":"32f54163-7166-48f1-93d8-ff217bdb0654",
            "input_descriptors":[
                {
                    "id":"degree_input_1",
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        },
                        {
                            "uri":"https://example.org/examples#UniversityDegreeCredential"
                        }
                    ],
                    "constraints":{
                        "limit_disclosure": "required",
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.degree.name"
                                ],
                                "filter":{
                                    "const": "Bachelor of Science and Arts"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        """
        tmp_pd = PresentationDefinition.deserialize(test_pd)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_signed_cred_no_credsubjectid,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp["verifiableCredential"]) == 1
        assert (
            tmp_vp.get("verifiableCredential")[0]
            .get("credentialSubject")
            .get("id")
            .startswith("urn:")
        )
        assert (
            tmp_vp.get("verifiableCredential")[0]
            .get("credentialSubject")
            .get("degree")
            .get("name")
            == "Bachelor of Science and Arts"
        )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_derive_nested_cred_missing_credsubjectid_b(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd = """
        {
            "id":"32f54163-7166-48f1-93d8-ff217bdb0654",
            "input_descriptors":[
                {
                    "id":"degree_input_1",
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        },
                        {
                            "uri":"https://example.org/examples#UniversityDegreeCredential"
                        }
                    ],
                    "constraints":{
                        "limit_disclosure": "required",
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.college"
                                ],
                                "filter":{
                                    "const": "Contoso University"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        """
        tmp_pd = PresentationDefinition.deserialize(test_pd)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_signed_cred_no_credsubjectid,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp["verifiableCredential"]) == 1
        assert (
            tmp_vp.get("verifiableCredential")[0]
            .get("credentialSubject")
            .get("id")
            .startswith("urn:")
        )
        assert (
            tmp_vp.get("verifiableCredential")[0]
            .get("credentialSubject")
            .get("college")
            == "Contoso University"
        )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_derive_nested_cred_credsubjectid(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd = """
        {
            "id":"32f54163-7166-48f1-93d8-ff217bdb0654",
            "input_descriptors":[
                {
                    "id":"degree_input_1",
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        },
                        {
                            "uri":"https://example.org/examples#UniversityDegreeCredential"
                        }
                    ],
                    "constraints":{
                        "limit_disclosure": "required",
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.degree.name"
                                ],
                                "filter":{
                                    "const": "Bachelor of Science and Arts"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        """
        tmp_pd = PresentationDefinition.deserialize(test_pd)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=bbs_signed_cred_credsubjectid,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp["verifiableCredential"]) == 1
        assert (
            tmp_vp.get("verifiableCredential")[0].get("credentialSubject").get("id")
            == "did:sov:WgWxqztrNooG92RXvxSTWv"
        )
        assert (
            tmp_vp.get("verifiableCredential")[0]
            .get("credentialSubject")
            .get("degree")
            .get("name")
            == "Bachelor of Science and Arts"
        )

    @pytest.mark.asyncio
    async def test_filter_by_field_path_match_on_proof(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        field = DIFField(paths=["$.proof.proofPurpose"])
        cred = VCRecord(
            contexts=[
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            expanded_types=[
                "https://www.w3.org/2018/credentials#VerifiableCredential",
                "https://example.org/examples#UniversityDegreeCredential",
            ],
            issuer_id="https://example.edu/issuers/565049",
            subject_ids=[
                "did:sov:LjgpST2rjsoxYegQDRm7EL",
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
            ],
            proof_types=["BbsBlsSignature2020"],
            schema_ids=["https://example.org/examples/degree.json"],
            cred_value={"...": "..."},
            given_id="http://example.edu/credentials/3732",
            cred_tags={"some": "tag"},
            record_id="test1",
        )
        with pytest.raises(DIFPresExchError):
            await dif_pres_exch_handler.filter_by_field(field, cred)

    @pytest.mark.asyncio
    async def test_filter_creds_record_id(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        cred_list = [
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=[
                    "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                ],
                proof_types=["BbsBlsSignature2020"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
                record_id="test1",
            ),
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=[
                    "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                ],
                proof_types=["BbsBlsSignature2020"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
                record_id="test2",
            ),
            VCRecord(
                contexts=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                expanded_types=[
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://example.org/examples#UniversityDegreeCredential",
                ],
                issuer_id="https://example.edu/issuers/565049",
                subject_ids=[
                    "did:sov:LjgpST2rjsoxYegQDRm7EL",
                    "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                ],
                proof_types=["BbsBlsSignature2020"],
                schema_ids=["https://example.org/examples/degree.json"],
                cred_value={"...": "..."},
                given_id="http://example.edu/credentials/3732",
                cred_tags={"some": "tag"},
                record_id="test3",
            ),
        ]
        record_id_list = ["test1", "test2"]
        filtered_cred_list = await dif_pres_exch_handler.filter_creds_record_id(
            cred_list, record_id_list
        )
        assert len(filtered_cred_list) == 2
        assert filtered_cred_list[0].record_id in record_id_list
        assert filtered_cred_list[1].record_id in record_id_list

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_create_vp_record_ids(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd_filter_with_only_num_type = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "pick",
                        "min": 1,
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                    "id":"citizenship_input_1",
                    "name":"EU Driver's License",
                    "group":[
                        "A"
                    ],
                    "schema":[
                        {
                            "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                        }
                    ],
                    "constraints":{
                        "fields":[
                            {
                                "path":[
                                    "$.credentialSubject.test",
                                    "$.vc.credentialSubject.test",
                                    "$.test"
                                ],
                                "filter":{  
                                    "type": "number"
                                }
                            }
                        ]
                    }
                    }
                ]
            }
        """
        records_filter = {"citizenship_input_1": ["test1", "test2"]}
        cred_list = deepcopy(bbs_bls_number_filter_creds)
        cred_list[0].record_id = "test1"
        cred_list[1].record_id = "test2"
        cred_list[2].record_id = "test3"

        tmp_pd = PresentationDefinition.deserialize(test_pd_filter_with_only_num_type)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=tmp_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
            records_filter=records_filter,
        )
        assert len(tmp_vp.get("verifiableCredential")) == 2

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_multiple_applicable_creds_with_no_id(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_creds = deepcopy(creds_with_no_id)
        test_creds[0].record_id = str(uuid4())
        test_creds[1].record_id = str(uuid4())
        cred_list, pd_list = setup_tuple

        tmp_pd = pd_list[6]
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=test_creds,
            pd=tmp_pd[0],
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        # only 1 sub_req
        assert isinstance(tmp_vp, dict)
        assert len(tmp_vp["verifiableCredential"]) == 2
        assert (
            tmp_vp.get("verifiableCredential")[0]
            .get("credentialSubject")
            .get("givenName")
            == "TEST"
        )
        assert (
            tmp_vp.get("verifiableCredential")[1]
            .get("credentialSubject")
            .get("givenName")
            == "TEST"
        )

        tmp_pd = pd_list[2]
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=test_creds,
            pd=tmp_pd[0],
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert isinstance(tmp_vp, Sequence)
        # 1 for each submission requirement group
        assert len(tmp_vp) == 3
        for tmp_vp_single in tmp_vp:
            assert (
                tmp_vp_single.get("verifiableCredential")[0]
                .get("credentialSubject")
                .get("givenName")
                == "TEST"
            )
            assert (
                tmp_vp_single.get("verifiableCredential")[1]
                .get("credentialSubject")
                .get("givenName")
                == "TEST"
            )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_multiple_applicable_creds_with_no_auto_and_no_record_ids(
        self, profile, setup_tuple
    ):
        cred_list, pd_list = setup_tuple
        context = profile.context
        context.settings = {}
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        test_pd_max_length = """
            {
                "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
                "submission_requirements":[
                    {
                        "name": "European Union Citizenship Proofs",
                        "rule": "all",
                        "from": "A"
                    }
                ],
                "input_descriptors":[
                    {
                        "id":"citizenship_input_1",
                        "name":"EU Driver's License",
                        "group":[
                            "A"
                        ],
                        "schema":[
                            {
                                "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints":{
                            "fields":[
                                {
                                    "path":[
                                        "$.issuer.id",
                                        "$.issuer",
                                        "$.vc.issuer.id"
                                    ],
                                    "filter":{
                                        "type":"string",
                                        "maxLength": 150
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        """
        tmp_pd = PresentationDefinition.deserialize(test_pd_max_length)
        with pytest.raises(DIFPresExchError):
            tmp_vp = await dif_pres_exch_handler.create_vp(
                credentials=cred_list,
                pd=tmp_pd,
                challenge="1f44d55f-f161-4938-a659-f8026467f126",
            )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_is_holder_valid_a(self, profile, setup_tuple):
        context = profile.context
        context.update_settings({"debug.auto_respond_presentation_request": True})
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        cred_list, pd_list = setup_tuple
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=is_holder_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6
        assert tmp_vp.get("proof")

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_is_holder_valid_b(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        cred_list, pd_list = setup_tuple
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=is_holder_pd_multiple_fields_included,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6
        assert tmp_vp.get("proof")

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_is_holder_valid_c(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(profile)
        cred_list, pd_list = setup_tuple
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=is_holder_pd_multiple_fields_excluded,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6
        assert tmp_vp.get("proof")

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_is_holder_signature_suite_mismatch(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_list, pd_list = setup_tuple
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=cred_list,
            pd=is_holder_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 6
        assert not tmp_vp.get("proof")

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_is_holder_subject_mismatch(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_list, pd_list = setup_tuple
        updated_cred_list = []
        for tmp_cred in deepcopy(cred_list):
            tmp_cred.subject_ids = ["did:sov:test"]
            updated_cred_list.append(tmp_cred)
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=updated_cred_list,
            pd=is_holder_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 0
        assert not tmp_vp.get("proof")

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_is_holder_missing_subject(self, profile, setup_tuple):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_list, pd_list = setup_tuple
        tmp_cred = deepcopy(cred_list[0])
        tmp_cred.subject_ids = None
        tmp_vp = await dif_pres_exch_handler.create_vp(
            credentials=[tmp_cred],
            pd=is_holder_pd,
            challenge="1f44d55f-f161-4938-a659-f8026467f126",
        )
        assert len(tmp_vp.get("verifiableCredential")) == 0
        assert not tmp_vp.get("proof")

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_apply_constraint_received_cred_path_update(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_dict = deepcopy(TEST_CRED_DICT)
        cred_dict["credentialSubject"]["Patient"]["address"] = [
            {
                "@id": "urn:bnid:_:c14n1",
                "city": "Рума",
            },
            {
                "@id": "urn:bnid:_:c14n1",
                "city": "Рума",
            },
        ]
        constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient[0].address[*].city"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_1
            assert await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_apply_constraint_received_cred_invalid(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_dict = deepcopy(TEST_CRED_DICT)
        cred_dict["credentialSubject"]["Patient"]["address"] = [
            {
                "@id": "urn:bnid:_:c14n1",
                "city": "Рума",
                "country": "test",
            },
            {
                "@id": "urn:bnid:_:c14n1",
                "city": "Рума",
            },
        ]
        constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient[0].address[0].city[0]"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_1
            assert not await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

        constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient[0].address[*].city"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_1
            assert not await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_apply_constraint_received_cred_valid(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )

        cred_dict = deepcopy(TEST_CRED_DICT)
        constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient.address"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_1
            assert await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

        constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient.address[0].city"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_1
            assert await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

        cred_dict["credentialSubject"]["Patient"]["address"] = [
            {
                "@id": "urn:bnid:_:c14n1",
                "city": "Рума",
            },
            {
                "@id": "urn:bnid:_:c14n1",
                "city": "Рума",
            },
        ]
        constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient.address[0].city"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_1
            assert await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

        cred_dict["credentialSubject"]["Patient"] = [
            {
                "address": [
                    {
                        "@id": "urn:bnid:_:c14n1",
                        "city": "Рума",
                    },
                    {
                        "@id": "urn:bnid:_:c14n1",
                        "city": "Рума",
                    },
                ]
            },
            {
                "address": [
                    {
                        "@id": "urn:bnid:_:c14n1",
                        "city": "Рума",
                    },
                    {
                        "@id": "urn:bnid:_:c14n1",
                        "city": "Рума",
                    },
                ]
            },
        ]
        constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient[0].address[0].city"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_2
            assert await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

        constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient[*].address[*].city"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_2
            assert await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

        constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient[*].address[0].city"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_2
            assert await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

        constraint = {
            "limit_disclosure": "required",
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient[0].address[*].city"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_2
            assert await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

    @pytest.mark.asyncio
    @pytest.mark.ursa_bbs_signatures
    async def test_apply_constraint_received_cred_no_sel_disc(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_dict = deepcopy(TEST_CRED_DICT)
        constraint = {
            "fields": [
                {
                    "path": ["$.credentialSubject.Patient.address.country"],
                    "purpose": "Test",
                }
            ],
        }
        constraint = Constraints.deserialize(constraint)
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_1
            assert not await dif_pres_exch_handler.apply_constraint_received_cred(
                constraint=constraint, cred_dict=cred_dict
            )

    @pytest.mark.asyncio
    async def test_get_updated_path(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_dict = deepcopy(TEST_CRED_DICT)
        cred_dict["credentialSubject"]["Patient"]["address"] = [
            {
                "@id": "urn:bnid:_:c14n1",
                "city": "Рума",
            },
            {
                "@id": "urn:bnid:_:c14n1",
                "city": "Рума",
            },
        ]
        original_path = "$.credentialSubject.Patient[*].address[0].city"
        updated_path = await dif_pres_exch_handler.get_updated_path(
            cred_dict, original_path
        )
        assert updated_path == "$.credentialSubject.Patient[*].address[0].city"
        cred_dict["credentialSubject"]["Patient"]["address"] = {
            "@id": "urn:bnid:_:c14n1",
            "city": "Рума",
        }
        original_path = "$.credentialSubject.Patient[*].address[0].city"
        updated_path = await dif_pres_exch_handler.get_updated_path(
            cred_dict, original_path
        )
        assert updated_path == "$.credentialSubject.Patient[*].address.city"

    def test_get_dict_keys_from_path(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_dict = {
            "id": "urn:bnid:_:c14n14",
            "type": ["MedicalPass", "VerifiableCredential"],
            "issuanceDate": "2021-09-27T12:40:03+02:00",
            "issuer": "did:key:zUC7DVPRfshooBqmnT2LrMxabCUkRhyyUCu8xKvYRot5aeTLTpPxzZoMyFkMLgKHMPUzdEnJM1EqbxfQd466ed3QuEtUJr8iqKRVfJ4txBa3PRoASaup6fjVAkU9VdbDbs5et64",
        }
        assert dif_pres_exch_handler.get_dict_keys_from_path(cred_dict, "issuer") == []

        cred_dict = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "urn:bnid:_:c14n4",
            "type": ["MedicalPass", "VerifiableCredential"],
            "credentialSubject": {
                "id": "urn:bnid:_:c14n6",
                "Patient": {
                    "@id": "urn:bnid:_:c14n7",
                    "@type": "fhir:resource-types#Patient",
                    "address": [
                        {"@id": "urn:bnid:_:c14n1", "city": "Рума"},
                        {"@id": "urn:bnid:_:c14n1", "city": "Рума"},
                    ],
                },
            },
            "issuanceDate": "2021-10-01T20:16:40+02:00",
            "issuer": "did:key:test",
        }
        assert dif_pres_exch_handler.get_dict_keys_from_path(
            cred_dict, "credentialSubject.Patient.address"
        ) == ["@id"]

    @pytest.mark.asyncio
    async def test_filter_by_field_keyerror(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_dict = deepcopy(TEST_CRED_DICT)
        cred_dict["credentialSubject"]["Patient"] = {
            "@id": "urn:bnid:_:c14n7",
            "@type": "fhir:resource-types#Patient",
            "address": {"@id": "urn:bnid:_:c14n1", "city": "Рума"},
        }
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_1
            vc_record_cred = dif_pres_exch_handler.create_vcrecord(cred_dict)
            field = DIFField.deserialize(
                {
                    "path": ["$.credentialSubject.Patient[0].address[0].city"],
                }
            )
            assert not await dif_pres_exch_handler.filter_by_field(
                field, vc_record_cred
            )

    @pytest.mark.asyncio
    async def test_filter_by_field_xsd_parser(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        cred_dict = deepcopy(TEST_CRED_DICT)
        cred_dict["credentialSubject"] = {}
        cred_dict["credentialSubject"]["lprNumber"] = {
            "type": "xsd:integer",
            "@value": "10",
        }
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_2
            vc_record_cred = dif_pres_exch_handler.create_vcrecord(cred_dict)
            field = DIFField.deserialize(
                {
                    "path": ["$.credentialSubject.lprNumber"],
                    "filter": {
                        "minimum": 5,
                        "type": "number",
                    },
                }
            )
            assert await dif_pres_exch_handler.filter_by_field(field, vc_record_cred)
        cred_dict = deepcopy(TEST_CRED_DICT)
        cred_dict["credentialSubject"] = {}
        cred_dict["credentialSubject"]["testDate"] = {
            "type": "xsd:dateTime",
            "@value": "2020-09-28T11:00:00+00:00",
        }
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_2
            vc_record_cred = dif_pres_exch_handler.create_vcrecord(cred_dict)
            field = DIFField.deserialize(
                {
                    "path": ["$.credentialSubject.testDate"],
                    "filter": {
                        "type": "string",
                        "format": "date",
                        "minimum": "2005-5-16",
                    },
                }
            )
            assert await dif_pres_exch_handler.filter_by_field(field, vc_record_cred)
        cred_dict = deepcopy(TEST_CRED_DICT)
        cred_dict["credentialSubject"] = {}
        cred_dict["credentialSubject"]["testFlag"] = {
            "type": "xsd:boolean",
            "@value": "false",
        }
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_2
            vc_record_cred = dif_pres_exch_handler.create_vcrecord(cred_dict)
            field = DIFField.deserialize(
                {
                    "path": ["$.credentialSubject.testFlag"],
                }
            )
            assert await dif_pres_exch_handler.filter_by_field(field, vc_record_cred)
        cred_dict = deepcopy(TEST_CRED_DICT)
        cred_dict["credentialSubject"] = {}
        cred_dict["credentialSubject"]["testDouble"] = {
            "type": "xsd:double",
            "@value": "10.2",
        }
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_2
            vc_record_cred = dif_pres_exch_handler.create_vcrecord(cred_dict)
            field = DIFField.deserialize(
                {"path": ["$.credentialSubject.testDouble"], "filter": {"const": 10.2}}
            )
            assert await dif_pres_exch_handler.filter_by_field(field, vc_record_cred)
        cred_dict = deepcopy(TEST_CRED_DICT)
        cred_dict["credentialSubject"] = {}
        cred_dict["credentialSubject"]["test"] = {
            "type": ["test"],
            "@id": "test",
            "test": "val",
        }
        with async_mock.patch.object(
            test_module.jsonld, "expand", async_mock.MagicMock()
        ) as mock_jsonld_expand:
            mock_jsonld_expand.return_value = EXPANDED_CRED_FHIR_TYPE_2
            vc_record_cred = dif_pres_exch_handler.create_vcrecord(cred_dict)
            field = DIFField.deserialize({"path": ["$.credentialSubject.test"]})
            assert await dif_pres_exch_handler.filter_by_field(field, vc_record_cred)

    def test_string_to_timezone_aware_datetime(self, profile):
        dif_pres_exch_handler = DIFPresExchHandler(
            profile, proof_type=BbsBlsSignature2020.signature_type
        )
        test_datetime_str = "2021-09-28T16:09:00EUROPE/BELGRADE"
        assert isinstance(
            dif_pres_exch_handler.string_to_timezone_aware_datetime(test_datetime_str),
            datetime,
        )
        assert isinstance(
            dif_pres_exch_handler.string_to_timezone_aware_datetime(
                "2020-09-28T11:00:00+00:00"
            ),
            datetime,
        )
