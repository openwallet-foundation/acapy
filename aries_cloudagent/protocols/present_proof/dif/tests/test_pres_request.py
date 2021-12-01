from unittest import TestCase

from ..pres_request_schema import DIFProofRequestSchema


class TestPresRequestSchema(TestCase):
    """DIF Presentation Request Test"""

    def test_limit_disclosure(self):
        test_pd_a = {
            "options": {
                "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                "domain": "4jt78h47fh47",
            },
            "presentation_definition": {
                "id": "32f54163-7166-48f1-93d8-ff217bdb0654",
                "submission_requirements": [
                    {
                        "name": "Citizenship Information",
                        "rule": "pick",
                        "min": 1,
                        "from": "A",
                    }
                ],
                "input_descriptors": [
                    {
                        "id": "citizenship_input_1",
                        "name": "EU Driver's License",
                        "group": ["A"],
                        "schema": [
                            {
                                "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints": {
                            "limit_disclosure": "required",
                            "fields": [
                                {
                                    "path": ["$.credentialSubject.givenName"],
                                    "purpose": "The claim must be from one of the specified issuers",
                                    "filter": {
                                        "type": "string",
                                        "enum": ["JOHN", "CAI"],
                                    },
                                }
                            ],
                        },
                    }
                ],
            },
        }
        test_pd_b = {
            "options": {
                "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                "domain": "4jt78h47fh47",
            },
            "presentation_definition": {
                "id": "32f54163-7166-48f1-93d8-ff217bdb0654",
                "submission_requirements": [
                    {
                        "name": "Citizenship Information",
                        "rule": "pick",
                        "min": 1,
                        "from": "A",
                    }
                ],
                "input_descriptors": [
                    {
                        "id": "citizenship_input_1",
                        "name": "EU Driver's License",
                        "group": ["A"],
                        "schema": [
                            {
                                "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"
                            }
                        ],
                        "constraints": {
                            "limit_disclosure": "preferred",
                            "fields": [
                                {
                                    "path": ["$.credentialSubject.givenName"],
                                    "purpose": "The claim must be from one of the specified issuers",
                                    "filter": {
                                        "type": "string",
                                        "enum": ["JOHN", "CAI"],
                                    },
                                }
                            ],
                        },
                    }
                ],
            },
        }

        pres_request_a = DIFProofRequestSchema().load(test_pd_a)
        test_limit_disclosure_a = (
            pres_request_a.presentation_definition.input_descriptors[
                0
            ].constraint.limit_disclosure
        )
        assert test_limit_disclosure_a == "required"
        pres_request_b = DIFProofRequestSchema().load(test_pd_b)
        test_limit_disclosure_b = (
            pres_request_b.presentation_definition.input_descriptors[
                0
            ].constraint.limit_disclosure
        )
        assert test_limit_disclosure_b == "preferred"
