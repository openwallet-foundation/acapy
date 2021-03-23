import pytest
import json

from asynctest import mock as async_mock
from asynctest import TestCase as AsyncTestCase
from copy import deepcopy
from time import time
from unittest import TestCase
from uuid import uuid4

from .....messaging.models.base import BaseModelError
from .....storage.vc_holder.vc_record import VCRecord

from ..pres_exch import (
    VerifiablePresentation,
    ClaimFormat,
    SubmissionRequirements,
    Holder,
    Filter,
    Constraints,
)
from ..pres_exch_handler import create_vp


class TestPresExchSchemas(TestCase):
    """Presentation predicate specification tests"""

    def test_claim_format(self):
        submission_req_json = """
            {
                "jwt": {
                "alg": ["EdDSA", "ES256K", "ES384"]
                },
                "jwt_vc": {
                "alg": ["ES256K", "ES384"]
                },
                "jwt_vp": {
                "alg": ["EdDSA", "ES256K"]
                },
                "ldp_vc": {
                "proof_type": [
                    "JsonWebSignature2020",
                    "Ed25519Signature2018",
                    "EcdsaSecp256k1Signature2019",
                    "RsaSignature2018"
                ]
                },
                "ldp_vp": {
                "proof_type": ["Ed25519Signature2018"]
                },
                "ldp": {
                "proof_type": ["RsaSignature2018"]
                }
            }
        """
        expected_result = json.loads(submission_req_json)
        actual_result = (ClaimFormat.deserialize(submission_req_json)).serialize()
        assert expected_result == actual_result

    def test_submission_requirements_from(self):
        claim_format_json = """
            {
                "name": "European Union Citizenship Proofs",
                "rule": "pick",
                "min": 1,
                "from": "A"
            }
        """
        expected_result = json.loads(claim_format_json)
        actual_result = (
            SubmissionRequirements.deserialize(claim_format_json)
        ).serialize()
        assert expected_result == actual_result

    def test_submission_requirements_from_nested(self):
        nested_submission_req_json = """
            {
                "name": "Citizenship Information",
                "rule": "pick",
                "count": 1,
                "from_nested": [
                    {
                    "name": "United States Citizenship Proofs",
                    "purpose": "We need you to prove you are a US citizen.",
                    "rule": "all",
                    "from": "A"
                    },
                    {
                    "name": "European Union Citizenship Proofs",
                    "purpose": "We need you to prove you are a citizen of a EU country.",
                    "rule": "all",
                    "from": "B"
                    }
                ]
            }
        """
        expected_result = json.loads(nested_submission_req_json)
        actual_result = (
            SubmissionRequirements.deserialize(nested_submission_req_json)
        ).serialize()
        assert expected_result == actual_result

    def test_submission_requirements_from_missing(self):
        test_json = """
            {
                "name": "Citizenship Information",
                "rule": "pick",
                "count": 1
            }
        """
        with self.assertRaises(BaseModelError) as cm:
            (SubmissionRequirements.deserialize(test_json)).serialize()

    def test_submission_requirements_from_both_present(self):
        test_json = """
            {
                "name": "Citizenship Information",
                "rule": "pick",
                "count": 1,
                "from": "A",
                "from_nested": [
                    {
                    "name": "United States Citizenship Proofs",
                    "purpose": "We need you to prove you are a US citizen.",
                    "rule": "all",
                    "from": "A"
                    },
                    {
                    "name": "European Union Citizenship Proofs",
                    "purpose": "We need you to prove you are a citizen of a EU country.",
                    "rule": "all",
                    "from": "B"
                    }
                ]
            }
        """
        with self.assertRaises(BaseModelError) as cm:
            (SubmissionRequirements.deserialize(test_json)).serialize()

    def test_is_holder(self):
        test_json = """
            {
                "field_id": [
                    "ce66380c-1990-4aec-b8b4-5d532e92a616",
                    "dd69e8a4-4cc0-4540-b34a-b4aa0e0d2214",
                    "d15802b4-eec8-45ef-b78f-e35125ac1bb8",
                    "765f3e09-600c-467f-99eb-ea549c350121"
                ],
                "directive": "required"
            }
        """
        expected_result = json.loads(test_json)
        actual_result = (Holder.deserialize(test_json)).serialize()
        assert expected_result == actual_result

    def test_filter(self):
        test_json_list = []
        test_json_string_enum = """
            {
              "type":"string",
              "enum": ["testa1", "testa2", "testa3"]
            }
        """
        test_json_list.append(test_json_string_enum)
        test_json_number_enum = """
            {
              "type":"string",
              "enum": ["testb1", "testb2", "testb3"]
            }
        """
        test_json_list.append(test_json_number_enum)
        test_json_not_enum = """
            {
                "not": {
                    "enum": ["testc1", "testc2", "testc3"]
                }
            }
        """
        test_json_list.append(test_json_not_enum)
        test_json_format_min = """
            {
                "type":"string",
                "format": "date",
                "minimum": "1980/07/04" 
            }
        """
        test_json_list.append(test_json_format_min)
        test_json_exclmax = """
            {
                "type":"number",
                "exclusiveMaximum": 2
            }
        """
        test_json_list.append(test_json_exclmax)
        test_json_exclmin = """
            {
                "exclusiveMinimum": 2
            }
        """
        test_json_list.append(test_json_exclmin)
        test_json_const = """
            {
                "const": 2.0
            }
        """
        test_json_list.append(test_json_const)
        test_json_enum_error = """
            {
                "enum": 2
            }
        """
        test_json_custom_field_error = """
            {
                "minimum": [
                    "not_valid"
                ]
            }
        """

        for tmp_test_item in test_json_list:
            expected_result = json.loads(tmp_test_item)
            actual_result = (Filter.deserialize(tmp_test_item)).serialize()
            assert expected_result == actual_result

        with self.assertRaises(BaseModelError) as cm:
            (Filter.deserialize(test_json_enum_error)).serialize()

        with self.assertRaises(BaseModelError) as cm:
            (Filter.deserialize(test_json_custom_field_error)).serialize()

    def test_constraints(self):
        test_json = """
            {
                "fields":[
                    {
                        "path":[
                            "$.credentialSubject.dob",
                            "$.vc.credentialSubject.dob",
                            "$.credentialSubject.license.dob"
                        ],
                        "filter":{
                        "type":"string",
                        "format":"date",
                        "minimum":"1999-5-16"
                        }
                    }
                ],
                "statuses": {
                    "active": {
                        "directive": "required"
                    },
                    "suspended": {
                        "directive": "allowed"
                    },
                    "revoked": {
                        "directive": "disallowed"
                    }
                }
            }
        """

        expected_result = json.loads(test_json)
        actual_result = (Constraints.deserialize(test_json)).serialize()
        assert expected_result == actual_result

    def test_vp(self):
        test_json_valid = """
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                {
                    "test": "test"
                }
            ], "type": [
                "VerifiablePresentation",
                "PresentationSubmission"
            ], 
            "verifiableCredential": [
                {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://www.w3.org/2018/credentials/examples/v1"
                    ], 
                    "id": "http://example.edu/credentials/1872",
                    "type": ["VerifiableCredential", "AlumniCredential"],
                    "issuer": "https://example.edu/issuers/565049",
                    "issuanceDate": "2010-01-01T19:73:24Z",
                    "credentialSubject": {
                        "id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                        "alumniOf": {"id": "did:example:c276e12ec21ebfeb1f712ebc6f1",
                        "name": [
                            {"value": "Example University", "lang": "en"},
                            {"value": "Exemple d\'Universit\\u00e9", "lang": "fr"}
                        ]}
                    },
                    "credentialSchema": {
                        "id": "https://eu.com/claims/DriversLicense.json",
                        "type": "JsonSchemaValidator2018"
                    }, 
                    "proof": {
                        "type": "RsaSignature2018",
                        "created": "2017-06-18T21:19:10Z",
                        "proofPurpose": "assertionMethod",
                        "verificationMethod": "https://example.edu/issuers/keys/1",
                        "jws": "eyJhbGciOiJSUzI1NiIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..TCYt5XsITJX1CxPCT8yAV-TVkIEq_PbChOMqsLfRoPsnsgw5WEuts01mq-pQy7UJiN5mgRxD-WUcX16dUEMGlv50aqzpqh4Qktb3rk-BuQy72IFLOqV0G_zS245-kronKb78cPN25DGlcTwLtjPAYuNzVBAh4vGHSrQyHUdBBPM"
                    }
                }, {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://www.w3.org/2018/credentials/examples/v1"
                    ],
                    "id": "http://example.edu/credentials/1873",
                    "type": [
                        "VerifiableCredential",
                        "AlumniCredential"
                    ],
                    "issuer": "https://example.edu/issuers/565050",
                    "issuanceDate": "2010-01-01T19:73:24Z",
                    "credentialSubject": {
                        "id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                        "alumniOf": {
                            "id": "did:example:c276e12ec21ebfeb1f712ebc6f1",
                            "name": [
                                {"value": "Example University", "lang": "en"},
                                {"value": "Exemple d\'Universit\\u00e9", "lang": "fr"}
                            ]
                        }
                    }, "credentialSchema": {
                        "id": "https://eu.com/claims/DriversLicense.json",
                        "type": "JsonSchemaValidator2018"
                    }, "proof": {
                        "type": "RsaSignature2018",
                        "created": "2017-06-18T21:19:10Z",
                        "proofPurpose": "assertionMethod",
                        "verificationMethod": "https://example.edu/issuers/keys/1",
                        "jws": "eyJhbGciOiJSUzI1NiIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..TCYt5XsITJX1CxPCT8yAV-TVkIEq_PbChOMqsLfRoPsnsgw5WEuts01mq-pQy7UJiN5mgRxD-WUcX16dUEMGlv50aqzpqh4Qktb3rk-BuQy72IFLOqV0G_zS245-kronKb78cPN25DGlcTwLtjPAYuNzVBAh4vGHSrQyHUdBBPM"
                    }
                }
            ], "presentation_submission": {
                "id": "083d9ac9-3e5f-4d46-a19d-358b8d661124",
                "definition_id": "32f54163-7166-48f1-93d8-ff217bdb0653",
                "descriptor_map": [
                    {"id": "citizenship_input_1", "format": "ldp_vp", "path": "$.verifiableCredential[0]"},
                    {"id": "citizenship_input_1", "format": "ldp_vp", "path": "$.verifiableCredential[1]"}
                ]
            }
        }
        """

        test_json_context_invalid = """
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                2
            ], "type": [
                "VerifiablePresentation",
                "PresentationSubmission"
            ], 
            "verifiableCredential": [
                {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://www.w3.org/2018/credentials/examples/v1"
                    ], 
                    "id": "http://example.edu/credentials/1872",
                    "type": ["VerifiableCredential", "AlumniCredential"],
                    "issuer": "https://example.edu/issuers/565049",
                    "issuanceDate": "2010-01-01T19:73:24Z",
                    "credentialSubject": {
                        "id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                        "alumniOf": {"id": "did:example:c276e12ec21ebfeb1f712ebc6f1",
                        "name": [
                            {"value": "Example University", "lang": "en"},
                            {"value": "Exemple d\'Universit\\u00e9", "lang": "fr"}
                        ]}
                    },
                    "credentialSchema": {
                        "id": "https://eu.com/claims/DriversLicense.json",
                        "type": "JsonSchemaValidator2018"
                    }, 
                    "proof": {
                        "type": "RsaSignature2018",
                        "created": "2017-06-18T21:19:10Z",
                        "proofPurpose": "assertionMethod",
                        "verificationMethod": "https://example.edu/issuers/keys/1",
                        "jws": "eyJhbGciOiJSUzI1NiIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..TCYt5XsITJX1CxPCT8yAV-TVkIEq_PbChOMqsLfRoPsnsgw5WEuts01mq-pQy7UJiN5mgRxD-WUcX16dUEMGlv50aqzpqh4Qktb3rk-BuQy72IFLOqV0G_zS245-kronKb78cPN25DGlcTwLtjPAYuNzVBAh4vGHSrQyHUdBBPM"
                    }
                }, {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://www.w3.org/2018/credentials/examples/v1"
                    ],
                    "id": "http://example.edu/credentials/1873",
                    "type": [
                        "VerifiableCredential",
                        "AlumniCredential"
                    ],
                    "issuer": "https://example.edu/issuers/565050",
                    "issuanceDate": "2010-01-01T19:73:24Z",
                    "credentialSubject": {
                        "id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                        "alumniOf": {
                            "id": "did:example:c276e12ec21ebfeb1f712ebc6f1",
                            "name": [
                                {"value": "Example University", "lang": "en"},
                                {"value": "Exemple d\'Universit\\u00e9", "lang": "fr"}
                            ]
                        }
                    }, "credentialSchema": {
                        "id": "https://eu.com/claims/DriversLicense.json",
                        "type": "JsonSchemaValidator2018"
                    }, "proof": {
                        "type": "RsaSignature2018",
                        "created": "2017-06-18T21:19:10Z",
                        "proofPurpose": "assertionMethod",
                        "verificationMethod": "https://example.edu/issuers/keys/1",
                        "jws": "eyJhbGciOiJSUzI1NiIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..TCYt5XsITJX1CxPCT8yAV-TVkIEq_PbChOMqsLfRoPsnsgw5WEuts01mq-pQy7UJiN5mgRxD-WUcX16dUEMGlv50aqzpqh4Qktb3rk-BuQy72IFLOqV0G_zS245-kronKb78cPN25DGlcTwLtjPAYuNzVBAh4vGHSrQyHUdBBPM"
                    }
                }
            ], "presentation_submission": {
                "id": "083d9ac9-3e5f-4d46-a19d-358b8d661124",
                "definition_id": "32f54163-7166-48f1-93d8-ff217bdb0653",
                "descriptor_map": [
                    {"id": "citizenship_input_1", "format": "ldp_vp", "path": "$.verifiableCredential[0]"},
                    {"id": "citizenship_input_1", "format": "ldp_vp", "path": "$.verifiableCredential[1]"}
                ]
            }
        }
        """

        test_vp_json_with_proof = """
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://identity.foundation/presentation-exchange/submission/v1"
            ],
            "type": [
                "VerifiablePresentation",
                "PresentationSubmission"
            ],
            "presentation_submission": {
                "id": "a30e3b91-fb77-4d22-95fa-871689c322e2",
                "definition_id": "32f54163-7166-48f1-93d8-ff217bdb0653",
                "descriptor_map": [
                {
                    "id": "banking_input_2",
                    "format": "jwt_vc",
                    "path": "$.verifiableCredential[0]"
                },
                {
                    "id": "employment_input",
                    "format": "ldp_vc",
                    "path": "$.verifiableCredential[1]"
                },
                {
                    "id": "citizenship_input_1",
                    "format": "ldp_vc",
                    "path": "$.verifiableCredential[2]"
                }
                ]
            },
            "verifiableCredential": [
                {
                "comment": "IN REALWORLD VPs, THIS WILL BE A BIG UGLY OBJECT INSTEAD OF THE DECODED JWT PAYLOAD THAT FOLLOWS",
                "vc": {
                    "@context": "https://www.w3.org/2018/credentials/v1",
                    "id": "https://eu.com/claims/DriversLicense",
                    "type": ["EUDriversLicense"],
                    "issuer": "did:example:123",
                    "issuanceDate": "2010-01-01T19:73:24Z",
                    "credentialSubject": {
                    "id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                    "accounts": [
                        {
                        "id": "1234567890",
                        "route": "DE-9876543210"
                        },
                        {
                        "id": "2457913570",
                        "route": "DE-0753197542"
                        }
                    ]
                    }
                }
                },
                {
                "@context": "https://www.w3.org/2018/credentials/v1",
                "id": "https://business-standards.org/schemas/employment-history.json",
                "type": ["VerifiableCredential", "GenericEmploymentCredential"],
                "issuer": "did:foo:123",
                "issuanceDate": "2010-01-01T19:73:24Z",
                "credentialSubject": {
                    "id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                    "active": true
                },
                "proof": {
                    "type": "EcdsaSecp256k1VerificationKey2019",
                    "created": "2017-06-18T21:19:10Z",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": "https://example.edu/issuers/keys/1",
                    "jws": "..."
                }
                },
                {
                "@context": "https://www.w3.org/2018/credentials/v1",
                "id": "https://eu.com/claims/DriversLicense",
                "type": ["EUDriversLicense"],
                "issuer": "did:foo:123",
                "issuanceDate": "2010-01-01T19:73:24Z",
                "credentialSubject": {
                    "id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
                    "license": {
                    "number": "34DGE352",
                    "dob": "07/13/80"
                    }
                },
                "proof": {
                    "type": "RsaSignature2018",
                    "created": "2017-06-18T21:19:10Z",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": "https://example.edu/issuers/keys/1",
                    "jws": "..."
                }
                }
            ],
            "proof": {
                "type": "RsaSignature2018",
                "created": "2018-09-14T21:19:10Z",
                "proofPurpose": "authentication",
                "verificationMethod": "did:example:ebfeb1f712ebc6f1c276e12ec21#keys-1",
                "challenge": "1f44d55f-f161-4938-a659-f8026467f126",
                "domain": "4jt78h47fh47",
                "jws": "..."
            }
        }
        """

        expected_result = json.loads(test_json_valid)
        actual_result = (
            VerifiablePresentation.deserialize(test_json_valid)
        ).serialize()
        assert expected_result == actual_result

        with self.assertRaises(BaseModelError) as cm:
            (VerifiablePresentation.deserialize(test_json_context_invalid)).serialize()

        vp_with_proof_dict = (
            VerifiablePresentation.deserialize(test_vp_json_with_proof)
        ).serialize()
        assert vp_with_proof_dict["proof"][0] == (
            json.loads(test_vp_json_with_proof)
        ).get("proof")
