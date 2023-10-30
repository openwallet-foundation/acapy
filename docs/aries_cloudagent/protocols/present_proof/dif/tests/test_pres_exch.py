"""Test for DIF PresExch Schemas."""
import json

from unittest import TestCase

from .....messaging.models.base import BaseModelError

from ..pres_exch import (
    ClaimFormat,
    SubmissionRequirements,
    DIFHolder,
    Filter,
    Constraints,
    VerifiablePresentation,
    SchemasInputDescriptorFilter,
)


class TestPresExchSchemas(TestCase):
    """Presentation predicate specification tests"""

    def test_claim_format_a(self):
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

    def test_claim_format_b(self):
        submission_req_json = """
            {
                "ldp_vp": {
                "proof_type": ["Ed25519Signature2018"]
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

    def test_submission_requirements_from_nested_of_nested(self):
        nested_submission_req_json = """
            {
                "name": "Лабораторијски резултати",
                "purpose": "Morbilli virus критеријум",
                "rule": "pick",
                "count": 1,
                "from_nested": [
                    {
                        "name": "Лични подаци",
                        "purpose": "Морамо идентификовати субјекта акредитива",
                        "rule": "pick",
                        "count": 1,
                        "from": "Patient"
                    },
                    {
                        "name": "Лабораторијски резултати",
                        "purpose": "Morbilli virus критеријум",
                        "rule": "pick",
                        "count": 1,
                        "from_nested": [
                            {
                                "name": "Негативан тест у последња 24 сата",
                                "purpose": "Незаразност",
                                "rule": "pick",
                                "count": 1,
                                "from": "PCR"
                            },
                            {
                                "name": "Тест атнитела",
                                "purpose": "Имуност",
                                "rule": "pick",
                                "count": 1,
                                "from": "IgG"
                            }
                        ]
                    }
                ]
            }
        """
        expected_result = json.loads(nested_submission_req_json)
        assert SubmissionRequirements.deserialize(nested_submission_req_json)
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

    def test_submission_requirements_from_both_missing(self):
        test_json = """
            {
                "name": "Citizenship Information",
                "rule": "pick",
                "count": 1
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
        actual_result = (DIFHolder.deserialize(test_json)).serialize()
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

    def test_verifiable_presentation_wrapper(self):
        test_vp_dict = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiablePresentation"],
            "verifiableCredential": [
                {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://w3id.org/citizenship/v1",
                        "https://w3id.org/security/bbs/v1",
                    ],
                    "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
                    "type": ["PermanentResidentCard", "VerifiableCredential"],
                    "credentialSubject": {
                        "id": "did:example:b34ca6cd37bbf23",
                        "type": ["Person", "PermanentResident"],
                        "givenName": "JOHN",
                    },
                    "issuanceDate": "2010-01-01T19:53:24Z",
                    "issuer": "did:key:zUC74bgefTdc43KS1psXgXf4jLaHyaj2qCQqQTXrtmSYGf1PxiJhrH6LGpaBMyj6tqAKmjGyMaS4RfNo2an77vT1HfzJUNPk4H7TCuJvSp4vet4Cu67kn2JSegoQNFSA1tbwU8v",
                    "proof": {
                        "type": "BbsBlsSignatureProof2020",
                        "nonce": "3AuruhJQrXtEgiagiJ+FwVf2S0SnzUDJvnO61YecQsJ7ImR1mPcoVjJJ0HOhfkFpoYI=",
                        "proofValue": "ABkBuAaPlP5A7JWY78Xf69oBnsMLcD1RXbIFYhcLoXPXW12CG9glnnqnPLsGri5xsA3LcP0kg74X+sAjKXGRGy3uvp412Dm0FuohYNboQcLne5KOAa5AxU4bjmwQsxdfduVqhriro1N+YTkuB4SMmO/5ooL0N3OHsYdExg7nSzWqmZoqgp+3CwIxF0a/oyKTcxJORuIqAAAAdInlL9teSIX49NJGEZfBO7IrdjT2iggH/G0AlPWoEvrWIbuCRQ69K83n5o7oJVjqhAAAAAIaVmlAD6+FEKA4eg0OaWOKPrd5Kq8rv0vIwjJ71egxll0Fqq4zDWQ/+yl3Pteh0Wyuyvpm19/sj6tiCWj4PkA+rpxtR2bXpnrCTKUffFFNBjVvVziXDS0KWkGUB7XU9mjUa4USC7Iub3bZZCnFjQA5AAAADzkGwGD837r33e7OTrGEti8eAkvFDcyCgA4ck/X+5HJjAJclHWbl4SNQR8CiNZyzJpvxW+jbNBcwmEvocYArddk3F78Ki0Qnp6aU9eDgfOOx1iW2BXLUjrhq5I2hP5/WQF3CEDYRjczGjzM9T8/coeC36YAp0zJunIXUKb8SPDSOISafibYRYFB4xhlWKXWloDelafyujOBST8KZNM8FmF4DSbXrO8vmZbjuR/8ntUcUK7X2rNbuZ3M5eWZDF8pL+SA9gQitKfPHEocoYAdhgEAM7ZNAJ+TgOcx9gtZIhDWKDNnFxIeoOAylbD1xZd9xbWtq3Bk3R79xqsKxFRJRNxk/9b6fJruP292+qM5lxcZ1jUz/dJUYFI93hH4Mso75CjGRN78MAY9SNifl6H8qcxTpBn4332LlFhRznLbtnc4YSWA/fvVqaN9h2zCH/6AdbLKXGffV34EF7DadwJsi9jsc+YlSMn6qaIUIDTdGLwh4KKpSH5bVbg/mVCcXPTJplFgYwRsOdiQbZY/740dJyo1lPjQ0Lvdio8W2M8c73ujeJU70CNLkgjJAMUPGrCFtGxBH2eeLBQ0P95qRZAIcJ7U0MibZLaRjoUOuTla5BIt2038PJ6XhcY6BEJaLyJOPEQ==",
                        "verificationMethod": "did:key:zUC74bgefTdc43KS1psXgXf4jLaHyaj2qCQqQTXrtmSYGf1PxiJhrH6LGpaBMyj6tqAKmjGyMaS4RfNo2an77vT1HfzJUNPk4H7TCuJvSp4vet4Cu67kn2JSegoQNFSA1tbwU8v#zUC74bgefTdc43KS1psXgXf4jLaHyaj2qCQqQTXrtmSYGf1PxiJhrH6LGpaBMyj6tqAKmjGyMaS4RfNo2an77vT1HfzJUNPk4H7TCuJvSp4vet4Cu67kn2JSegoQNFSA1tbwU8v",
                        "proofPurpose": "assertionMethod",
                        "created": "2021-05-05T15:22:30.523465",
                    },
                }
            ],
            "presentation_submission": {
                "id": "a5fcfe44-2c30-497d-af02-98e539da9a0f",
                "definition_id": "32f54163-7166-48f1-93d8-ff217bdb0653",
                "descriptor_map": [
                    {
                        "id": "citizenship_input_1",
                        "format": "ldp_vc",
                        "path": "$.verifiableCredential[0]",
                    }
                ],
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:sov:4QxzWk3ajdnEA37NdNU5Kt#key-1",
                "created": "2021-05-05T15:23:03.023971",
                "proofPurpose": "authentication",
                "challenge": "40429d49-5e8f-4ffc-baf8-e332412f1247",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..2uBYmg7muE9ZPVeAGo_ibVfLkCjf2hGshr2o5i8pAwFyNBM-kDHXofuq1MzJgb19wzb01VIu91hY_ajjt9KFAA",
            },
        }
        vp = VerifiablePresentation.deserialize(test_vp_dict)
        assert isinstance(vp, VerifiablePresentation)

    def test_schemas_input_desc_filter(self):
        test_schema_list = [
            [
                {"uri": "https://www.w3.org/2018/VC"},
                {"uri": "https://w3id.org/citizenship#PermanentResidentCard"},
            ],
            [{"uri": "https://www.w3.org/Test#Test"}],
        ]
        test_schemas_filter = {
            "oneof_filter": test_schema_list,
        }

        deser_schema_filter = SchemasInputDescriptorFilter.deserialize(
            test_schemas_filter
        )
        ser_schema_filter = deser_schema_filter.serialize()
        deser_schema_filter = SchemasInputDescriptorFilter.deserialize(
            ser_schema_filter
        )
        assert deser_schema_filter.oneof_filter
        assert deser_schema_filter.uri_groups[0][0].uri == test_schema_list[0][0].get(
            "uri"
        )
        assert deser_schema_filter.uri_groups[0][1].uri == test_schema_list[0][1].get(
            "uri"
        )
        assert deser_schema_filter.uri_groups[1][0].uri == test_schema_list[1][0].get(
            "uri"
        )
        assert isinstance(deser_schema_filter, SchemasInputDescriptorFilter)

        test_schema_list = [
            {"uri": "https://www.w3.org/Test#Test"},
            {"uri": "https://w3id.org/citizenship#PermanentResidentCard"},
        ]
        test_schemas_filter = {
            "oneof_filter": test_schema_list,
        }

        deser_schema_filter = SchemasInputDescriptorFilter.deserialize(
            test_schemas_filter
        )
        ser_schema_filter = deser_schema_filter.serialize()
        deser_schema_filter = SchemasInputDescriptorFilter.deserialize(
            ser_schema_filter
        )
        assert deser_schema_filter.oneof_filter
        assert deser_schema_filter.uri_groups[0][0].uri == test_schema_list[0].get(
            "uri"
        )
        assert deser_schema_filter.uri_groups[1][0].uri == test_schema_list[1].get(
            "uri"
        )
        assert isinstance(deser_schema_filter, SchemasInputDescriptorFilter)

        deser_schema_filter = SchemasInputDescriptorFilter.deserialize(test_schema_list)
        ser_schema_filter = deser_schema_filter.serialize()
        deser_schema_filter = SchemasInputDescriptorFilter.deserialize(
            ser_schema_filter
        )
        assert not deser_schema_filter.oneof_filter
        assert deser_schema_filter.uri_groups[0][0].uri == test_schema_list[0].get(
            "uri"
        )
        assert deser_schema_filter.uri_groups[0][1].uri == test_schema_list[1].get(
            "uri"
        )
        assert isinstance(deser_schema_filter, SchemasInputDescriptorFilter)
