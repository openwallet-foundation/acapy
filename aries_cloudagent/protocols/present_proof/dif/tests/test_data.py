"""Data for DIFPresExchHandler."""
import json
from pyld import jsonld
from pyld.jsonld import JsonLdProcessor

from .....storage.vc_holder.vc_record import VCRecord

from ..pres_exch import PresentationDefinition


def create_vcrecord(cred_dict: dict, expanded_types: list):
    given_id = cred_dict.get("id")
    contexts = [ctx for ctx in cred_dict.get("@context") if type(ctx) is str]

    # issuer
    issuer = cred_dict.get("issuer")
    if type(issuer) is dict:
        issuer = issuer.get("id")

    # subjects
    subjects = cred_dict.get("credentialSubject")
    if type(subjects) is dict:
        subjects = [subjects]
    subject_ids = [subject.get("id") for subject in subjects if subject.get("id")]

    # Schemas
    schemas = cred_dict.get("credentialSchema", [])
    if type(schemas) is dict:
        schemas = [schemas]
    schema_ids = [schema.get("id") for schema in schemas]

    # Proofs (this can be done easier if we use the expanded version)
    proofs = cred_dict.get("proof") or []
    proof_types = None
    if type(proofs) is dict:
        proofs = [proofs]
    if proofs:
        proof_types = [proof.get("type") for proof in proofs]

    return VCRecord(
        contexts=contexts,
        expanded_types=expanded_types,
        issuer_id=issuer,
        subject_ids=subject_ids,
        proof_types=proof_types,
        given_id=given_id,
        cred_value=cred_dict,
        schema_ids=schema_ids,
    )


EXPANDED_CRED_FHIR_TYPE_1 = [
    {
        "https://www.w3.org/2018/credentials#credentialSubject": [
            {
                "http://hl7.org/fhir/Patient": [
                    {
                        "@id": "urn:bnid:_:c14n7",
                        "@type": ["http://hl7.org/fhir/resource-types#Patient"],
                        "http://hl7.org/fhir/Patient.address": [
                            {
                                "@id": "urn:bnid:_:c14n1",
                                "http://hl7.org/fhir/Address.city": [
                                    {"@value": "Рума"}
                                ],
                                "http://hl7.org/fhir/Address.country": [
                                    {"@value": "test"}
                                ],
                            },
                            {
                                "@id": "urn:bnid:_:c14n1",
                                "http://hl7.org/fhir/Address.city": [
                                    {"@value": "Рума"}
                                ],
                            },
                        ],
                    }
                ],
                "@id": "urn:bnid:_:c14n6",
            }
        ],
        "@id": "urn:bnid:_:c14n4",
        "https://www.w3.org/2018/credentials#issuanceDate": [
            {
                "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                "@value": "2021-10-01T20:16:40+02:00",
            }
        ],
        "https://www.w3.org/2018/credentials#issuer": [{"@id": "did:key:test"}],
        "https://w3id.org/security#proof": [
            {
                "@graph": [
                    {
                        "http://purl.org/dc/terms/created": [
                            {
                                "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                                "@value": "2021-10-01T18:16:41.072975+00:00",
                            }
                        ],
                        "https://w3id.org/security#nonce": [
                            {
                                "@value": "M9yQx0eKIAI3Zs0sLF1kQsO7/hV1ZKEnqX9f0V/SzwRMKEixa0tJgqbGwviMA04XoL0="
                            }
                        ],
                        "https://w3id.org/security#proofPurpose": [
                            {"@id": "https://w3id.org/security#assertionMethod"}
                        ],
                        "https://w3id.org/security#proofValue": [
                            {
                                "@value": "ACYgFHwPj5TxR9H+k+V+rBsfZ3SgOEvoKrYCcvAl4HhaKNR039r5UWE89tnHaVOx22k604EWibf0s7BTezijjYv1VWSVkZar4wtOslplXv6g7dVc8/0IWXQWOfn2hTE2N65Wv8xz2qw5dWwEzSXTx44o15wE2ubimgGFMM7Mv++SAoHC1dQGotGqKqOB2PS8yI+ToiWmswAAAHSD5NRIZHKeiWP8hK/e9xUYy5gSPBivDVAORybl62B/F3eaUC/pRdfsORAWRHLjmfcAAAACcOe6yrLqI3OmxkKUfsCGgIl83LLcQ9pLjaigdc/5XRs6KYo533Q/7cGryn2IvLFAJiHgZJ8Ovwi9xkDy1USKjZfjgRMil4PEiwZ2Gqu4g+HlJ11JemUX2HDAjJYgJHSFguZp/l/5y//0pQegHOi9hwAAABcp9nblpM/ALrFpdenGn23x5kdYC4gMyTV6a6RPuMwryVZcmTP50XDVHiY2t4JLvULdJcGDcOCpetMPhqyAf3VeNtorYjr1+YWSgjApfqZ594rMyohWGwkNu0zqv19qDkQ+aBibGhhsCBHe+jFy/BXQv2TlIMgX7YdUgVtUuO4YJT4cz4xrDlK58sJPpmJqraasoA0E+ciPOtGX5J7e4n+dGlPwkQjcD79cjBGs7hXmljeqbe2a82YQw/Q+L/yVKqxl8+ucLoqQ2QzREKslQ7ljchX8RsHQURflZTgPxGjNyCqHtEIcT6d7COcpmqGYSo5ge0pIXab97H97NBnk9mmdcCOCETWOJ8shuS7n4R4GdnRDjB5ArbBnpIMYUGEsdD0ZR87nVBbAfWFhQWJgsJvpPOGq2p6VPImfwhIoh7LIYkpwVogRLrSQGl5IZcHexlHwjZoogafCD5OSyEAO3au3UUoVde4S98v2233QuOwXvz3ptYOO+aJIbqmgdmGs41YfbyT830/H+248+Zbkob7T1FBWbYtEW+k8omat87tc3RfU9LYgNrXWUpJ/TZ+4Cqg7VljkPhCIEZYNUoKQxG1pP11HsmLvzhtnoNVLwjvJA7IrcinAr2pnWSBzjm/wBx8mANrCAHW4f4yyvSXCWZJOfnf/N8dt01Di0QaNbYs8Hlo6yjjjqkrvgLpZtAuuca8nQPPNZWrj3Oids/Z0nZsgKGwZxHo5negKE1JKEEz7zJQUd14JhRYiwfzWYprHcJ9szp5Tgmskksv3NIyKQ7XfLwnOY29zLOpTm51c99Ru6CVvAvIGckB+oE8cwPRjfE9fajJtQEODZ1ljbzYNACzLZ52iSsL+rSKq9LL79TgmN2lE0SkmgrwkOBAjmSwzrBc9DdQrkpWlSZzOWyL/QuNfHfEiNn43nwhaJpbvQ6zr/XHbspH7oqe0eexfvzowzkKc9noWqQnU0IaMrtRgyOma"
                            }
                        ],
                        "@type": ["https://w3id.org/security#BbsBlsSignatureProof2020"],
                        "https://w3id.org/security#verificationMethod": [
                            {"@id": "did:key:test"}
                        ],
                    }
                ]
            }
        ],
        "@type": [
            "https://www.vdel.com/MedicalPass",
            "https://www.w3.org/2018/credentials#VerifiableCredential",
        ],
    }
]

EXPANDED_CRED_FHIR_TYPE_2 = [
    {
        "https://www.w3.org/2018/credentials#credentialSubject": [{}],
        "@id": "urn:bnid:_:c14n4",
        "https://www.w3.org/2018/credentials#issuanceDate": [
            {
                "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                "@value": "2021-10-01T20:16:40+02:00",
            }
        ],
        "https://www.w3.org/2018/credentials#issuer": [{"@id": "did:key:test"}],
        "https://w3id.org/security#proof": [
            {
                "@graph": [
                    {
                        "http://purl.org/dc/terms/created": [
                            {
                                "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                                "@value": "2021-10-01T18:16:41.072975+00:00",
                            }
                        ],
                        "https://w3id.org/security#nonce": [
                            {
                                "@value": "M9yQx0eKIAI3Zs0sLF1kQsO7/hV1ZKEnqX9f0V/SzwRMKEixa0tJgqbGwviMA04XoL0="
                            }
                        ],
                        "https://w3id.org/security#proofPurpose": [
                            {"@id": "https://w3id.org/security#assertionMethod"}
                        ],
                        "https://w3id.org/security#proofValue": [
                            {
                                "@value": "ACYgFHwPj5TxR9H+k+V+rBsfZ3SgOEvoKrYCcvAl4HhaKNR039r5UWE89tnHaVOx22k604EWibf0s7BTezijjYv1VWSVkZar4wtOslplXv6g7dVc8/0IWXQWOfn2hTE2N65Wv8xz2qw5dWwEzSXTx44o15wE2ubimgGFMM7Mv++SAoHC1dQGotGqKqOB2PS8yI+ToiWmswAAAHSD5NRIZHKeiWP8hK/e9xUYy5gSPBivDVAORybl62B/F3eaUC/pRdfsORAWRHLjmfcAAAACcOe6yrLqI3OmxkKUfsCGgIl83LLcQ9pLjaigdc/5XRs6KYo533Q/7cGryn2IvLFAJiHgZJ8Ovwi9xkDy1USKjZfjgRMil4PEiwZ2Gqu4g+HlJ11JemUX2HDAjJYgJHSFguZp/l/5y//0pQegHOi9hwAAABcp9nblpM/ALrFpdenGn23x5kdYC4gMyTV6a6RPuMwryVZcmTP50XDVHiY2t4JLvULdJcGDcOCpetMPhqyAf3VeNtorYjr1+YWSgjApfqZ594rMyohWGwkNu0zqv19qDkQ+aBibGhhsCBHe+jFy/BXQv2TlIMgX7YdUgVtUuO4YJT4cz4xrDlK58sJPpmJqraasoA0E+ciPOtGX5J7e4n+dGlPwkQjcD79cjBGs7hXmljeqbe2a82YQw/Q+L/yVKqxl8+ucLoqQ2QzREKslQ7ljchX8RsHQURflZTgPxGjNyCqHtEIcT6d7COcpmqGYSo5ge0pIXab97H97NBnk9mmdcCOCETWOJ8shuS7n4R4GdnRDjB5ArbBnpIMYUGEsdD0ZR87nVBbAfWFhQWJgsJvpPOGq2p6VPImfwhIoh7LIYkpwVogRLrSQGl5IZcHexlHwjZoogafCD5OSyEAO3au3UUoVde4S98v2233QuOwXvz3ptYOO+aJIbqmgdmGs41YfbyT830/H+248+Zbkob7T1FBWbYtEW+k8omat87tc3RfU9LYgNrXWUpJ/TZ+4Cqg7VljkPhCIEZYNUoKQxG1pP11HsmLvzhtnoNVLwjvJA7IrcinAr2pnWSBzjm/wBx8mANrCAHW4f4yyvSXCWZJOfnf/N8dt01Di0QaNbYs8Hlo6yjjjqkrvgLpZtAuuca8nQPPNZWrj3Oids/Z0nZsgKGwZxHo5negKE1JKEEz7zJQUd14JhRYiwfzWYprHcJ9szp5Tgmskksv3NIyKQ7XfLwnOY29zLOpTm51c99Ru6CVvAvIGckB+oE8cwPRjfE9fajJtQEODZ1ljbzYNACzLZ52iSsL+rSKq9LL79TgmN2lE0SkmgrwkOBAjmSwzrBc9DdQrkpWlSZzOWyL/QuNfHfEiNn43nwhaJpbvQ6zr/XHbspH7oqe0eexfvzowzkKc9noWqQnU0IaMrtRgyOma"
                            }
                        ],
                        "@type": ["https://w3id.org/security#BbsBlsSignatureProof2020"],
                        "https://w3id.org/security#verificationMethod": [
                            {"@id": "did:key:test"}
                        ],
                    }
                ]
            }
        ],
        "@type": [
            "https://www.vdel.com/MedicalPass",
            "https://www.w3.org/2018/credentials#VerifiableCredential",
        ],
    }
]

is_holder_pd = PresentationDefinition.deserialize(
    {
        "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
        "submission_requirements": [
            {
                "name": "European Union Citizenship Proofs",
                "rule": "all",
                "from": "A",
            }
        ],
        "input_descriptors": [
            {
                "id": "citizenship_input_1",
                "group": ["A"],
                "schema": [
                    {"uri": "https://www.w3.org/2018/credentials#VerifiableCredential"},
                    {"uri": "https://w3id.org/citizenship#PermanentResidentCard"},
                ],
                "constraints": {
                    "is_holder": [
                        {
                            "directive": "required",
                            "field_id": ["1f44d55f-f161-4938-a659-f8026467f126"],
                        }
                    ],
                    "fields": [
                        {
                            "id": "1f44d55f-f161-4938-a659-f8026467f126",
                            "path": ["$.issuanceDate", "$.vc.issuanceDate"],
                            "filter": {
                                "type": "string",
                                "format": "date",
                                "maximum": "2014-5-16",
                            },
                        }
                    ],
                },
            }
        ],
    }
)

is_holder_pd_multiple_fields_included = PresentationDefinition.deserialize(
    {
        "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
        "submission_requirements": [
            {
                "name": "European Union Citizenship Proofs",
                "rule": "all",
                "from": "A",
            }
        ],
        "input_descriptors": [
            {
                "id": "citizenship_input_1",
                "group": ["A"],
                "schema": [
                    {"uri": "https://www.w3.org/2018/credentials#VerifiableCredential"},
                    {"uri": "https://w3id.org/citizenship#PermanentResidentCard"},
                ],
                "constraints": {
                    "is_holder": [
                        {
                            "directive": "required",
                            "field_id": [
                                "1f44d55f-f161-4938-a659-f8026467f126",
                                "1f44d55f-f161-4938-a659-f8026467f127",
                            ],
                        }
                    ],
                    "fields": [
                        {
                            "id": "1f44d55f-f161-4938-a659-f8026467f126",
                            "path": ["$.issuanceDate", "$.vc.issuanceDate"],
                            "filter": {
                                "type": "string",
                                "format": "date",
                                "maximum": "2014-5-16",
                            },
                        },
                        {
                            "id": "1f44d55f-f161-4938-a659-f8026467f127",
                            "path": ["$.issuanceDate", "$.vc.issuanceDate"],
                            "filter": {
                                "type": "string",
                                "format": "date",
                                "minimum": "2005-5-16",
                            },
                        },
                    ],
                },
            }
        ],
    }
)

is_holder_pd_multiple_fields_excluded = PresentationDefinition.deserialize(
    {
        "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
        "submission_requirements": [
            {
                "name": "European Union Citizenship Proofs",
                "rule": "all",
                "from": "A",
            }
        ],
        "input_descriptors": [
            {
                "id": "citizenship_input_1",
                "group": ["A"],
                "schema": [
                    {"uri": "https://www.w3.org/2018/credentials#VerifiableCredential"},
                    {"uri": "https://w3id.org/citizenship#PermanentResidentCard"},
                ],
                "constraints": {
                    "is_holder": [
                        {
                            "directive": "required",
                            "field_id": ["1f44d55f-f161-4938-a659-f8026467f126"],
                        }
                    ],
                    "fields": [
                        {
                            "id": "1f44d55f-f161-4938-a659-f8026467f126",
                            "path": ["$.issuanceDate", "$.vc.issuanceDate"],
                            "filter": {
                                "type": "string",
                                "format": "date",
                                "maximum": "2014-5-16",
                            },
                        },
                        {
                            "id": "1f44d55f-f161-4938-a659-f8026467f127",
                            "path": ["$.issuanceDate", "$.vc.issuanceDate"],
                            "filter": {
                                "type": "string",
                                "format": "date",
                                "minimum": "2005-5-16",
                            },
                        },
                    ],
                },
            }
        ],
    }
)

creds_with_no_id = [
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "type": ["PermanentResident", "Person"],
                "givenName": "TEST",
                "familyName": "SMITH",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Bahamas",
                "birthDate": "1958-07-17",
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "mMEjznbr4lN5xQT0OuLJ94pKSSBEwBxKNHBPxfjwhRq2NnDaTH/mb+PdPnmfUgKvA8h5hI9Ho3qfY8TWmJtLsYSmJFZoG/FARQuwJJbTW/tVZoA2FVVKZGEsGt2MHsr1z/W30cXnmRyQzgqh4lnhQg==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "type": ["PermanentResident", "Person"],
                "givenName": "TEST",
                "familyName": "SMITH",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Bahamas",
                "birthDate": "1958-07-17",
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "rf5LlOFiB5oAl/hSEeaN/H3vx+3AXVpL4O4abtLmYb1aUF+WBOX3HBx5SrTkcwUgJBAPNoFX9l2PVDjTGy/eCjDerDG0DN5ZR+YwjebcZeclzE3Yv2hsnan1M/OTAc9GTNWE3p9lXbRxHNvwTXX6ug==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
]

bbs_signed_cred_no_credsubjectid = [
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "identifier": "83627465",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2019-12-03T12:19:52Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "type": ["PermanentResident", "Person"],
                "givenName": "JOHN",
                "familyName": "SMITH",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Bahamas",
                "birthDate": "1958-07-17",
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "hG9cNGyjjAgPkDmtNv/+28ciBZFUVcAG2gfvLBlTWeFyYJu6DARo16RwQAoSnrgVRQn3n7KCSdnSrPb3op1+vSTu2vo+LF3GfSfqlei44bwA+c2FBIRk7S3FKY6Lm5mqOtC2Q4LStC9HtaOj8vQhgA==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "credentialSubject": {
                "birthCountry": "Bahamas",
                "birthDate": "1958-07-17",
                "familyName": "SMITH",
                "gender": "Female",
                "givenName": "ALICE",
                "type": ["PermanentResident", "Person"],
            },
            "issuanceDate": "2020-01-01T12:00:00Z",
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "haUMgpZE4hPiIEvzdEWyGsvXh1enQvhsOq2cMf3q80u29ybRDi74zU0O+fug1bWiMxeFOboxsfuEKXGC4Ldw0sCsIs+90Jn4EuTqhY4ml8YWsKY9Kjpxvtpc0e24SOl++oo48EICfUxb24HYlQ35pw==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://example.gov/credentials/3732",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "issuanceDate": "2020-03-10T04:24:12.164Z",
            "credentialSubject": {
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
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "iRArJRSvmIwx5YH2HXg5OJD+0v5sD1HoqhBsiJiw59t3Eb6nSntyOnENEnqnpzQwCjtbvOsU18eBlVi2/ign1u1ysz0iOLxSRHvIKtDDpr1dTDwQCbuZo2gUnY+8Dy+xEst8MDtcXwzNQW8Y3l1XzA==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://example.org/examples#UniversityDegreeCredential",
        ],
    ),
]

bbs_signed_cred_credsubjectid = [
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "identifier": "83627465",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2019-12-03T12:19:52Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "JOHN",
                "familyName": "SMITH",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Bahamas",
                "birthDate": "1958-07-17",
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "s++A89p+SvIHvY9pnIKIPsLjrLGGk2cs+LfpTWCsE0S1Y5Rg1h9OA5c84Vzqlc3kGfM3zdYpHrO9v0/vBFLQ3HV9wH7xgmD9MPVN+klsaQJdobRpJMjlBni7/QA2/+0szT2P1FJ537lGjyuRboVWng==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://example.gov/credentials/3732",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "issuanceDate": "2020-03-10T04:24:12.164Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
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
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "proofValue": "iGAQ4bOxuqkoCbX3RoxTqFkJsoqPcEeRN2vqIzd/zWLS+VHCwYkQHu/TeMOrit4eb6eugbJFUBaoenZyy2VU/7Rsj614sNzumJFuJ6ZaDTlv0k70CkO9GheQTc+Gwv749Y3JzPJ0dwYGUzzcyytFCQ==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://example.org/examples#UniversityDegreeCredential",
        ],
    ),
]

bbs_bls_number_filter_creds = [
    create_vcrecord(
        {
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
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "JOHN",
                "familyName": "SMITH",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Bahamas",
                "birthDate": "1958-07-17",
                "test": 2,
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:example:489398593#test",
                "created": "2021-04-13T23:23:56.045014",
                "proofPurpose": "assertionMethod",
                "proofValue": "rhD+4HOhPfLywBuhLYMi1i0kWa/L2Qipt+sqTRiebjoo4OF3ESoGnm+L4Movz128Mjns60H0Bz7W+aqN1dPP9uhU/FGBKW/LEIGJX1rrrYgn17CkWp46z/hwQy+8c9ulOCn0Yq3BDqB37euoBTZbOQ==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627466",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627466",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "Theodor",
                "familyName": "Major",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2017-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Canada",
                "birthDate": "1968-07-17",
                "test": 2,
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:example:489398593#test",
                "created": "2021-04-13T23:33:05.798834",
                "proofPurpose": "assertionMethod",
                "proofValue": "jp8ahSYYFhRAk+1ahfG8qu7iEjQnEXp3P3fWgTrc4khxmw9/9mGACq67YW9r917/aKYTQcVyojelN3cBHrjBvaOzb7bZ6Ps0Wf6WFq1gc0QFUrdiN0mJRl5YAz8R16sLxrPsoS/8ji1MoabjqmlnWQ==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
                "https://w3id.org/security/bbs/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627467",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627467",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "Cai",
                "familyName": "Leblanc",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-9989",
                "commuterClassification": "C1",
                "birthCountry": "Canada",
                "birthDate": "1975-07-17",
                "test": 3,
            },
            "proof": {
                "type": "BbsBlsSignature2020",
                "verificationMethod": "did:example:489398593#test",
                "created": "2021-04-13T23:40:44.835154",
                "proofPurpose": "assertionMethod",
                "proofValue": "t8+TPbYqF/dGlEn+qNnEFL1L0QeUjgXlYfJ7AelzOhb7cr2CjP/MIcG5bAQ5l6F2OZKNyE8RsPY14xedrkxpyv1oyWPmXzOwr0gt6ElLJm9jAUwFoZ7xAYHSedcR3Lh4FFuqmxfBHYF3A6VgSlMSfA==",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
]

edd_jsonld_creds = [
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627465",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "JOHN",
                "familyName": "SMITH",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Bahamas",
                "birthDate": "1958-07-17",
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2021-05-07T08:47:13.090322",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..HHEpbiQp781YtXdxmYr3xO9a8OtHSePjySbgwGaSqiHGjd9hO0AnhkFxlBlrGukp5rkiJccr4p9KV3uKDzkqDA",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627466",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627466",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "Theodor",
                "familyName": "Major",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2017-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-999",
                "commuterClassification": "C1",
                "birthCountry": "Canada",
                "birthDate": "1968-07-17",
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2021-05-07T08:48:49.702706",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..r88-rSvqp_JLr2fnGr8nKEU--Hu6UhzjXOmdWpt082Wc6ojWpOANvv2wbgKrs5kXF5ATb8-AZ01VPpHdv4m9CQ",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
    create_vcrecord(
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/citizenship/v1",
            ],
            "id": "https://issuer.oidp.uscis.gov/credentials/83627467",
            "type": ["VerifiableCredential", "PermanentResidentCard"],
            "issuer": "did:example:489398593",
            "identifier": "83627467",
            "name": "Permanent Resident Card",
            "description": "Government of Example Permanent Resident Card.",
            "issuanceDate": "2010-01-01T19:53:24Z",
            "expirationDate": "2029-12-03T12:19:52Z",
            "credentialSubject": {
                "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
                "type": ["PermanentResident", "Person"],
                "givenName": "Cai",
                "familyName": "Leblanc",
                "gender": "Male",
                "image": "data:image/png;base64,iVBORw0KGgokJggg==",
                "residentSince": "2015-01-01",
                "lprCategory": "C09",
                "lprNumber": "999-999-9989",
                "commuterClassification": "C1",
                "birthCountry": "Canada",
                "birthDate": "1975-07-17",
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2021-05-07T08:50:17.626625",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..rubQvgig7cN-F6cYn_AJF1BCSaMpkoR517Ot_4pqwdJnQ-JwKXq6d6cNos5JR73E9WkwYISXapY0fYTIG9-fBA",
            },
        },
        [
            "https://www.w3.org/2018/credentials#VerifiableCredential",
            "https://w3id.org/citizenship#PermanentResidentCard",
        ],
    ),
]

CRED_LIST = [
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627465",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
        "identifier": "83627465",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "JOHN",
            "familyName": "SMITH",
            "gender": "Male",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2015-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-999",
            "commuterClassification": "C1",
            "birthCountry": "Bahamas",
            "birthDate": "1958-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "ssut7SPH6KiY44z5w9N/dD+L8KxS7pXF5irVyty0IlafX7hn5AZNd1rb7fhzVz6wZo9nK/nu/bYs9zhuJggTbuQNPWyOWiFmd3uSxr+CrTYUZ/u31s7gaqEYv4pUBoKgMx6WKkOApELtOI4e0PFddA==",
        },
    },
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627466",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
        "identifier": "83627466",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "Theodor",
            "familyName": "Major",
            "gender": "Male",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2017-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-999",
            "commuterClassification": "C1",
            "birthCountry": "Canada",
            "birthDate": "1968-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "tnRgimJXy8mP7Amk8dPiJnJc+WhAFiYPF8hpRlqOPsSom4cF1VAxaiAN2o3io1kYajUtmXAJLxNNLOZkXDBblcqZAu5mHKEPWc/nctu3vNs4gs5f7tWZX7lm6JK71pLJq8lWbyIufIm/BnCjeIll5g==",
        },
    },
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627467",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:sov:2wJPyULfLLnYTEFYzByfUR",
        "identifier": "83627467",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "Cai",
            "familyName": "Leblanc",
            "gender": "Male",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2015-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-9989",
            "commuterClassification": "C1",
            "birthCountry": "Canada",
            "birthDate": "1975-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "l1sdjvIhlkAPb+Y1vUYgIVH9YhiWSFjJFOL1ntzN9jXvOqv7/RMFhoAxg0BTYU1ITHK5l/6Q5lwmtkKxJMt/Z+QPZ8yWDIwqX8kVXFxKo9st8T45ChYiizc75E+Rd7Z5qIidmuulyPvpHlpgHYLZsQ==",
        },
    },
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627468",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:example:489398593",
        "identifier": "83627468",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "Jamel",
            "familyName": "Huber",
            "gender": "Female",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2012-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-000",
            "commuterClassification": "C1",
            "birthCountry": "United States",
            "birthDate": "1959-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "rtG10rBsv8zXHBGWqHTeGyH9Y3oMa6xHjBvsJ5YHeocUBxOCge2WEs1tr60hjI4SEpi3JHSJOfd1wJEvfvMg/x6YnTZoA2UXiHBu/6vANx43EfTgbq4YDrrf1aTtQgpZDp/J4GaKoeUshuPXyf8LyA==",
        },
    },
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627469",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:sov:2wJPyULfLLnYTEFYzByfUR",
        "identifier": "83627469",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "Vivek",
            "familyName": "Easton",
            "gender": "Male",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2019-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-888",
            "commuterClassification": "C1",
            "birthCountry": "India",
            "birthDate": "1990-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "pvo7gqDgu9mMjcZafvS8gRz0mIRfFnRCNmp39cZ/92R3UDG5bmxPhh4nG2k1kjaza8wFfaqjaBxsonV+FkQUMzUWbZkn2vstEcGCJllDHFBQiDcf8MVCiCcbGBLpU9MXjnyzhwA5AteG9a2YcvRh/w==",
        },
    },
    {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://w3id.org/citizenship/v1",
            "https://w3id.org/security/bbs/v1",
        ],
        "id": "https://issuer.oidp.uscis.gov/credentials/83627470",
        "type": ["VerifiableCredential", "PermanentResidentCard"],
        "issuer": "did:sov:2wJPyULfLLnYTEFYzByfUR",
        "identifier": "83627470",
        "name": "Permanent Resident Card",
        "description": "Government of Example Permanent Resident Card.",
        "issuanceDate": "2010-01-01T19:53:24Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "credentialSubject": {
            "id": "did:sov:WgWxqztrNooG92RXvxSTWv",
            "type": ["PermanentResident", "Person"],
            "givenName": "Ralphie",
            "familyName": "Jennings",
            "gender": "Female",
            "image": "data:image/png;base64,iVBORw0KGgokJggg==",
            "residentSince": "2010-01-01",
            "lprCategory": "C09",
            "lprNumber": "999-999-777",
            "commuterClassification": "C1",
            "birthCountry": "Canada",
            "birthDate": "1980-07-17",
        },
        "proof": {
            "type": "BbsBlsSignature2020",
            "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
            "created": "2019-12-11T03:50:55",
            "proofPurpose": "assertionMethod",
            "proofValue": "pVuvbBfGnVbwwht1s4qZSCoLlZ8nwqvsmNKR+1VTesA+7tXPriJCdlnNFDL0Gkh5TV5E0NOS8WNttE5Uhhqakmjcs7L4hIr4PoVtCLFAF1tce8n4Z/5PKD7IuGIdCDbn77fjQffu2Cs+JDBVVcQRBA==",
        },
    },
]

# [Nested_From] Either or case
# Exclusive Disjunction
# -----------------------
# |_x_|_y_|_output_|
# | T | T |   F    |
# | T | F |   T    |
# | F | T |   T    |
# | F | F |   F    |
# -----------------------
pres_exch_nested_srs_a = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
            "purpose":"The claim must be from one of the specified issuers",
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593", "did:sov:2wJPyULfLLnYTEFYzByfUR"]
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
              "maximum":"2005-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_nested_srs_b = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
            "purpose":"The claim must be from one of the specified issuers",
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593"]
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
              "maximum":"2012-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_nested_srs_c = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
            "purpose":"The claim must be from one of the specified issuers",
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593", "did:sov:2wJPyULfLLnYTEFYzByfUR"]
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
              "minimum":"2005-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_multiple_srs_not_met = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
    {
      "name": "Citizenship Information",
      "rule": "pick",
      "count": 2,
      "from": "A"
    },
    {
      "name": "European Union Citizenship Proofs",
      "purpose": "We need you to prove you are a citizen of a EU country.",
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuer.id",
              "$.vc.issuer.id",
              "$.issuer"
            ],
            "purpose":"The claim must be from one of the specified issuers",
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593", "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa", "did:sov:2wJPyULfLLnYTEFYzByfUR"]
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
              "exclusiveMinimum":"2009-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_multiple_srs_met_one_of_filter_invalid = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
    {
      "name": "Citizenship Information",
      "rule": "all",
      "from": "A"
    },
    {
      "name": "European Union Citizenship Proofs",
      "rule": "all",
      "from": "B"
    },
    {
      "name": "Date Test",
      "rule": "all",
      "from": "C"
    }
  ],
  "input_descriptors":[
    {
      "id":"citizenship_input_1",
      "name":"EU Driver's License",
      "group":[
        "A"
      ],
      "schema": [
            {
                "uri":"https://www.w3.org/Test#Test"
            }
      ],
      "constraints":{
        "fields":[
          {
           "path":[
              "$.issuer.id",
              "$.vc.issuer.id",
              "$.issuer"
            ],
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593", "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa", "did:sov:2wJPyULfLLnYTEFYzByfUR"]
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.credentialSubject.gender"
            ],
            "filter":{
              "const":"Male"
            }
          }
        ]
      }
    },
    {
      "id":"citizenship_input_3",
      "name":"US Passport",
      "group":[
        "C"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuanceDate"
            ],
            "filter":{
              "type":"string",
              "format":"date",
              "minimum":"2005-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_multiple_srs_met_one_of_valid = """
{
  "id":"32f54163-7166-48f1-93d8-ff217bdb0653",
  "submission_requirements":[
    {
      "name": "Citizenship Information",
      "rule": "all",
      "from": "A"
    },
    {
      "name": "European Union Citizenship Proofs",
      "rule": "all",
      "from": "B"
    },
    {
      "name": "Date Test",
      "rule": "all",
      "from": "C"
    }
  ],
  "input_descriptors":[
    {
      "id":"citizenship_input_1",
      "name":"EU Driver's License",
      "group":[
        "A"
      ],
      "schema": {
        "oneof_filter": [
            [
                {
                    "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                },
                {
                    "uri":"https://w3id.org/citizenship#PermanentResidentCard"
                }
            ]
        ]
      },
      "constraints":{
        "fields":[
          {
           "path":[
              "$.issuer.id",
              "$.vc.issuer.id",
              "$.issuer"
            ],
            "filter":{
              "type":"string",
              "enum": ["did:example:489398593", "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa", "did:sov:2wJPyULfLLnYTEFYzByfUR"]
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
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.credentialSubject.gender"
            ],
            "filter":{
              "const":"Male"
            }
          }
        ]
      }
    },
    {
      "id":"citizenship_input_3",
      "name":"US Passport",
      "group":[
        "C"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
        }
      ],
      "constraints":{
        "fields":[
          {
            "path":[
              "$.issuanceDate"
            ],
            "filter":{
              "type":"string",
              "format":"date",
              "minimum":"2005-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_datetime_minimum_met = """
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
      "group":[
        "A"
      ],
      "schema":[
        {
          "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
        },
        {
          "uri":"https://w3id.org/citizenship#PermanentResidentCard"
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
              "minimum":"2005-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

pres_exch_datetime_maximum_met = """
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
      "group":[
        "A"
      ],
      "schema": {
        "oneof_filter": [
            [
                {
                    "uri":"https://www.w3.org/2018/credentials#VerifiableCredential"
                },
                {
                    "uri":"https://w3id.org/citizenship#PermanentResidentCard"
                }
            ],
            [
                {
                    "uri":"https://w3id.org/Test#Test"
                }
            ]
        ]
      },
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
              "maximum":"2014-5-16"
            }
          }
        ]
      }
    }
  ]
}
"""

TEST_CRED_DICT = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/security/bbs/v1",
        {
            "MedicalPass": {
                "@id": "https://www.vdel.com/MedicalPass",
                "@context": {
                    "description": "http://schema.org/description",
                    "identifier": "http://schema.org/identifier",
                    "name": "http://schema.org/name",
                    "image": "http://schema.org/image",
                },
            }
        },
        {
            "Patient": {
                "@id": "http://hl7.org/fhir/Patient",
                "@context": [
                    "https://fhircat.org/fhir-r5/rdf-r5/contexts/patient.context.jsonld"
                ],
            }
        },
    ],
    "id": "urn:bnid:_:c14n4",
    "type": ["MedicalPass", "VerifiableCredential"],
    "credentialSubject": {
        "id": "urn:bnid:_:c14n6",
        "Patient": {
            "@id": "urn:bnid:_:c14n7",
            "@type": "fhir:resource-types#Patient",
            "address": {
                "@id": "urn:bnid:_:c14n1",
                "city": "Рума",
            },
        },
    },
    "issuanceDate": "2021-10-01T20:16:40+02:00",
    "issuer": "did:key:test",
    "proof": {
        "type": "BbsBlsSignatureProof2020",
        "nonce": "M9yQx0eKIAI3Zs0sLF1kQsO7/hV1ZKEnqX9f0V/SzwRMKEixa0tJgqbGwviMA04XoL0=",
        "proofValue": "ACYgFHwPj5TxR9H+k+V+rBsfZ3SgOEvoKrYCcvAl4HhaKNR039r5UWE89tnHaVOx22k604EWibf0s7BTezijjYv1VWSVkZar4wtOslplXv6g7dVc8/0IWXQWOfn2hTE2N65Wv8xz2qw5dWwEzSXTx44o15wE2ubimgGFMM7Mv++SAoHC1dQGotGqKqOB2PS8yI+ToiWmswAAAHSD5NRIZHKeiWP8hK/e9xUYy5gSPBivDVAORybl62B/F3eaUC/pRdfsORAWRHLjmfcAAAACcOe6yrLqI3OmxkKUfsCGgIl83LLcQ9pLjaigdc/5XRs6KYo533Q/7cGryn2IvLFAJiHgZJ8Ovwi9xkDy1USKjZfjgRMil4PEiwZ2Gqu4g+HlJ11JemUX2HDAjJYgJHSFguZp/l/5y//0pQegHOi9hwAAABcp9nblpM/ALrFpdenGn23x5kdYC4gMyTV6a6RPuMwryVZcmTP50XDVHiY2t4JLvULdJcGDcOCpetMPhqyAf3VeNtorYjr1+YWSgjApfqZ594rMyohWGwkNu0zqv19qDkQ+aBibGhhsCBHe+jFy/BXQv2TlIMgX7YdUgVtUuO4YJT4cz4xrDlK58sJPpmJqraasoA0E+ciPOtGX5J7e4n+dGlPwkQjcD79cjBGs7hXmljeqbe2a82YQw/Q+L/yVKqxl8+ucLoqQ2QzREKslQ7ljchX8RsHQURflZTgPxGjNyCqHtEIcT6d7COcpmqGYSo5ge0pIXab97H97NBnk9mmdcCOCETWOJ8shuS7n4R4GdnRDjB5ArbBnpIMYUGEsdD0ZR87nVBbAfWFhQWJgsJvpPOGq2p6VPImfwhIoh7LIYkpwVogRLrSQGl5IZcHexlHwjZoogafCD5OSyEAO3au3UUoVde4S98v2233QuOwXvz3ptYOO+aJIbqmgdmGs41YfbyT830/H+248+Zbkob7T1FBWbYtEW+k8omat87tc3RfU9LYgNrXWUpJ/TZ+4Cqg7VljkPhCIEZYNUoKQxG1pP11HsmLvzhtnoNVLwjvJA7IrcinAr2pnWSBzjm/wBx8mANrCAHW4f4yyvSXCWZJOfnf/N8dt01Di0QaNbYs8Hlo6yjjjqkrvgLpZtAuuca8nQPPNZWrj3Oids/Z0nZsgKGwZxHo5negKE1JKEEz7zJQUd14JhRYiwfzWYprHcJ9szp5Tgmskksv3NIyKQ7XfLwnOY29zLOpTm51c99Ru6CVvAvIGckB+oE8cwPRjfE9fajJtQEODZ1ljbzYNACzLZ52iSsL+rSKq9LL79TgmN2lE0SkmgrwkOBAjmSwzrBc9DdQrkpWlSZzOWyL/QuNfHfEiNn43nwhaJpbvQ6zr/XHbspH7oqe0eexfvzowzkKc9noWqQnU0IaMrtRgyOma",
        "verificationMethod": "did:key:test",
        "proofPurpose": "assertionMethod",
        "created": "2021-10-01T18:16:41.072975+00:00",
    },
}

TEST_CRED_WILDCARD = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/security/bbs/v1",
        {
            "LabReport": {
                "@id": "https://www.vdel.com/LabReport",
                "@context": {
                    "description": "http://schema.org/description",
                    "identifier": "http://schema.org/identifier",
                    "name": "http://schema.org/name",
                    "image": "http://schema.org/image",
                },
            }
        },
        {
            "Specimen": {
                "@id": "http://hl7.org/fhir/Specimen",
                "@context": [
                    None,
                    "https://fhircat.org/fhir-r5/rdf-r5/contexts/specimen.context.jsonld",
                ],
            }
        },
        {
            "Observation": {
                "@id": "http://hl7.org/fhir/Observation",
                "@context": [
                    None,
                    "https://fhircat.org/fhir-r5/rdf-r5/contexts/observation.context.jsonld",
                ],
            }
        },
        {
            "Organization": {
                "@id": "http://hl7.org/fhir/Organization",
                "@context": [
                    None,
                    "https://fhircat.org/fhir-r5/rdf-r5/contexts/organization.context.jsonld",
                ],
            }
        },
        {
            "Practitioner": {
                "@id": "http://hl7.org/fhir/Practitioner",
                "@context": [
                    None,
                    "https://fhircat.org/fhir-r5/rdf-r5/contexts/practitioner.context.jsonld",
                ],
            }
        },
        {
            "DiagnosticReport": {
                "@id": "http://hl7.org/fhir/DiagnosticReport",
                "@context": [
                    None,
                    "https://fhircat.org/fhir-r5/rdf-r5/contexts/diagnosticreport.context.jsonld",
                ],
            }
        },
        {
            "PractitionerRole": {
                "@id": "http://hl7.org/fhir/PractitionerRole",
                "@context": [
                    None,
                    "https://fhircat.org/fhir-r5/rdf-r5/contexts/practitionerrole.context.jsonld",
                ],
            }
        },
    ],
    "type": ["VerifiableCredential", "LabReport"],
    "issuer": "did:key:zUC74FYQCzCbDpbVm9v1LVCc2RkxJY3XMdxV9UpsVaerTgEAAjpdWfE8WemccfdNhski3kHiXfLzPZW2wgsvSCkZFWV3zSNxQEqZoV8kVpwLtLzzpskRcskBB3M3DxaeBnDvK4H",
    "issuanceDate": "2021-10-01T20:17:12+02:00",
    "credentialSubject": {
        "DiagnosticReport": {
            "resourceType": "http://hl7.org/fhir/resource-types#DiagnosticReport",
            "id": "ca66dd0a-6ad5-db5e-e053-5a18000aa066",
            "language": "sr-Cyrl-RS",
            "basedOn": [
                {"reference": "ServiceRequest/ca66a8f6-1b0e-2881-e053-5a18000acec9"}
            ],
            "status": "final",
            "category": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "LAB",
                    }
                ]
            },
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "11502-2",
                        "display": "Laboratory report",
                    }
                ]
            },
            "subject": {"reference": "Patient/ca66572a-0a1b-0d53-e053-5a18000ad0b7"},
            "effectiveDateTime": "2021-08-25T19:47:00EUROPE/BELGRADE",
            "issued": "2021-08-25T19:47:00EUROPE/BELGRADE",
            "performer": [
                {"reference": "PractitionerRole/ca6632d5-a447-6306-e053-5a18000a3953"}
            ],
            "specimen": [
                {"reference": "Specimen/ca666dfb-5a85-614a-e053-5a18000af20b"}
            ],
            "result": [
                {"reference": "Observation/ca708651-e8eb-3513-e053-5a18000ae79b"},
                {"reference": "Observation/ca708651-e8ec-3513-e053-5a18000ae79b"},
                {"reference": "Observation/ca708651-e8ed-3513-e053-5a18000ae79b"},
                {"reference": "Observation/ca708651-e8e9-3513-e053-5a18000ae79b"},
                {"reference": "Observation/ca708651-e8ea-3513-e053-5a18000ae79b"},
                {"reference": "Observation/ca708651-e8e7-3513-e053-5a18000ae79b"},
                {"reference": "Observation/ca708651-e8e8-3513-e053-5a18000ae79b"},
            ],
        },
        "Specimen": {
            "resourceType": "http://hl7.org/fhir/resource-types#Specimen",
            "id": "ca666dfb-5a85-614a-e053-5a18000af20b",
            "language": "sr-Cyrl-RS",
            "accessionIdentifier": {
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "ACSN",
                        }
                    ],
                    "text": "Broj protokola",
                },
                "value": "124",
            },
            "status": "available",
            "type": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "122592007",
                        "display": "Acellular blood (serum or plasma) specimen",
                    }
                ]
            },
            "subject": {"reference": "Patient/ca66572a-0a1b-0d53-e053-5a18000ad0b7"},
            "receivedTime": "2021-08-25T19:16:00EUROPE/BELGRADE",
        },
        "PractitionerRole": {
            "resourceType": "http://hl7.org/fhir/resource-types#PractitionerRole",
            "id": "ca6632d5-a447-6306-e053-5a18000a3953",
            "active": True,
            "practitioner": {
                "reference": "Practitioner/ca5ed67e-5780-0136-e053-5a18000ae501"
            },
            "organization": {
                "reference": "Organization/ca661f4d-ffc6-6111-e053-5a18000a3dea"
            },
            "code": [
                {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/uv/ips/ValueSet/healthcare-professional-roles-uv-ips",
                            "code": "2212",
                            "display": "Специјалисти лекари",
                        }
                    ]
                }
            ],
            "specialty": [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "408454008",
                            "display": "Клиничка микробиологија",
                        }
                    ]
                }
            ],
        },
        "Practitioner": {
            "resourceType": "http://hl7.org/fhir/resource-types#Practitioner",
            "id": "ca5ed67e-5780-0136-e053-5a18000ae501",
            "language": "sr-Cyrl-RS",
            "text": "специјалиста медицинске микробиологије",
            "active": True,
            "name": [{"family": "Банчевић", "given": ["Маја"], "suffix": ["др"]}],
            "gender": "female",
            "qualification": [{"code": {"coding": [{"code": "MD"}]}}],
        },
        "Observation": [
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Observation",
                "id": "ca708651-e8eb-3513-e053-5a18000ae79b",
                "language": "sr-Cyrl-RS",
                "text": {"status": "generated", "div": "Negativan"},
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/uv/ips/ValueSet/results-laboratory-observations-uv-ips",
                            "code": "24115-8",
                            "display": "Epstein Barr virus (EBV) IgM",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "40168006",
                            "display": "Epstein Barr virus (EBV)",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "74889000",
                            "display": "IgM",
                        },
                    ]
                },
                "subject": {
                    "reference": "Patient/ca66572a-0a1b-0d53-e053-5a18000ad0b7"
                },
                "effectiveDateTime": "2021-08-26T07:09:00EUROPE/BELGRADE",
                "method": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/ValueSet/observation-methods",
                            "code": "76978006",
                            "display": "ELISA",
                        }
                    ]
                },
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "2667000",
                            "display": "Odsutno",
                        }
                    ]
                },
                "interpretation": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "NEG",
                                "display": "Negativan",
                            }
                        ]
                    }
                ],
            },
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Observation",
                "id": "ca708651-e8e8-3513-e053-5a18000ae79b",
                "language": "sr-Cyrl-RS",
                "text": {"status": "generated", "div": "Pozitivan"},
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/uv/ips/ValueSet/results-laboratory-observations-uv-ips",
                            "code": "35275-7",
                            "display": "Morbille virus IgG",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "52584002",
                            "display": "Morbilli virus",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "29246005",
                            "display": "IgG",
                        },
                    ]
                },
                "subject": {
                    "reference": "Patient/ca66572a-0a1b-0d53-e053-5a18000ad0b7"
                },
                "effectiveDateTime": "2021-08-26T07:09:00EUROPE/BELGRADE",
                "method": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/ValueSet/observation-methods",
                            "code": "76978006",
                            "display": "ELISA",
                        }
                    ]
                },
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "52101004",
                            "display": "Prisutno",
                        }
                    ]
                },
                "interpretation": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "POS",
                                "display": "Pozitivan",
                            }
                        ]
                    }
                ],
            },
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Observation",
                "id": "ca708651-e8e7-3513-e053-5a18000ae79b",
                "language": "sr-Cyrl-RS",
                "text": {"status": "generated", "div": "Negativan"},
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/uv/ips/ValueSet/results-laboratory-observations-uv-ips",
                            "code": "35276-5",
                            "display": "Morbille virus IgM",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "52584002",
                            "display": "Morbilli virus",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "74889000",
                            "display": "IgM",
                        },
                    ]
                },
                "subject": {
                    "reference": "Patient/ca66572a-0a1b-0d53-e053-5a18000ad0b7"
                },
                "effectiveDateTime": "2021-08-26T07:09:00EUROPE/BELGRADE",
                "method": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/ValueSet/observation-methods",
                            "code": "76978006",
                            "display": "ELISA",
                        }
                    ]
                },
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "2667000",
                            "display": "Odsutno",
                        }
                    ]
                },
                "interpretation": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "NEG",
                                "display": "Negativan",
                            }
                        ]
                    }
                ],
            },
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Observation",
                "id": "ca708651-e8ea-3513-e053-5a18000ae79b",
                "language": "sr-Cyrl-RS",
                "text": {"status": "generated", "div": "Pozitivan"},
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/uv/ips/ValueSet/results-laboratory-observations-uv-ips",
                            "code": "29660-8",
                            "display": "Humani Parvo virus B19 IgG",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "63603005",
                            "display": "Humani Parvo virus B19",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "29246005",
                            "display": "IgG",
                        },
                    ]
                },
                "subject": {
                    "reference": "Patient/ca66572a-0a1b-0d53-e053-5a18000ad0b7"
                },
                "effectiveDateTime": "2021-08-26T07:09:00EUROPE/BELGRADE",
                "method": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/ValueSet/observation-methods",
                            "code": "76978006",
                            "display": "ELISA",
                        }
                    ]
                },
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "52101004",
                            "display": "Prisutno",
                        }
                    ]
                },
                "interpretation": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "POS",
                                "display": "Pozitivan",
                            }
                        ]
                    }
                ],
            },
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Observation",
                "id": "ca708651-e8e9-3513-e053-5a18000ae79b",
                "language": "sr-Cyrl-RS",
                "text": {"status": "generated", "div": "Negativan"},
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/uv/ips/ValueSet/results-laboratory-observations-uv-ips",
                            "code": "40658-7",
                            "display": "Humani Parvo virus B19 IgM",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "63603005",
                            "display": "Humani Parvo virus B19",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "74889000",
                            "display": "IgM",
                        },
                    ]
                },
                "subject": {
                    "reference": "Patient/ca66572a-0a1b-0d53-e053-5a18000ad0b7"
                },
                "effectiveDateTime": "2021-08-26T07:09:00EUROPE/BELGRADE",
                "method": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/ValueSet/observation-methods",
                            "code": "76978006",
                            "display": "ELISA",
                        }
                    ]
                },
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "2667000",
                            "display": "Odsutno",
                        }
                    ]
                },
                "interpretation": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "NEG",
                                "display": "Negativan",
                            }
                        ]
                    }
                ],
            },
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Observation",
                "id": "ca708651-e8ed-3513-e053-5a18000ae79b",
                "language": "sr-Cyrl-RS",
                "text": {"status": "generated", "div": "Negativan"},
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/uv/ips/ValueSet/results-laboratory-observations-uv-ips",
                            "code": "40729-6",
                            "display": "Herpes Simplex virus (HSV) IgM",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "19965007",
                            "display": "Herpes Simplex virus (HSV)",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "74889000",
                            "display": "IgM",
                        },
                    ]
                },
                "subject": {
                    "reference": "Patient/ca66572a-0a1b-0d53-e053-5a18000ad0b7"
                },
                "effectiveDateTime": "2021-08-26T07:09:00EUROPE/BELGRADE",
                "method": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/ValueSet/observation-methods",
                            "code": "76978006",
                            "display": "ELISA",
                        }
                    ]
                },
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "2667000",
                            "display": "Odsutno",
                        }
                    ]
                },
                "interpretation": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "NEG",
                                "display": "Negativan",
                            }
                        ]
                    }
                ],
            },
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Observation",
                "id": "ca708651-e8ec-3513-e053-5a18000ae79b",
                "language": "sr-Cyrl-RS",
                "text": {"status": "generated", "div": "Pozitivan"},
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/uv/ips/ValueSet/results-laboratory-observations-uv-ips",
                            "code": "24114-1",
                            "display": "Epstein Barr virus (EBV) IgG",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "40168006",
                            "display": "Epstein Barr virus (EBV)",
                        },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "29246005",
                            "display": "IgG",
                        },
                    ]
                },
                "subject": {
                    "reference": "Patient/ca66572a-0a1b-0d53-e053-5a18000ad0b7"
                },
                "effectiveDateTime": "2021-08-26T07:09:00EUROPE/BELGRADE",
                "method": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/ValueSet/observation-methods",
                            "code": "76978006",
                            "display": "ELISA",
                        }
                    ]
                },
                "valueCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "52101004",
                            "display": "Prisutno",
                        }
                    ]
                },
                "interpretation": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "POS",
                                "display": "Pozitivan",
                            }
                        ]
                    }
                ],
            },
        ],
        "Organization": [
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Organization",
                "id": "ca661f4d-ffc6-6111-e053-5a18000a3dea",
                "language": "sr-Cyrl-RS",
                "active": True,
                "type": ["team"],
                "name": "Национална лабораторија за полиомијелитис и ентеровирусе",
                "partOf": {
                    "reference": "Organization/ca661f4d-ffc5-6111-e053-5a18000a3dea",
                    "type": "Organization",
                },
                "address": [{"type": "both", "country": "RS"}],
            },
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Organization",
                "id": "ca661f4d-ffc5-6111-e053-5a18000a3dea",
                "language": "sr-Cyrl-RS",
                "active": True,
                "type": ["team"],
                "name": "Одсек за серодијагностику и молекуларну дијагностику",
                "partOf": {
                    "reference": "Organization/ca661c1e-cab1-611d-e053-5a18000af938",
                    "type": "Organization",
                },
                "address": [{"type": "both", "country": "RS"}],
            },
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Organization",
                "id": "ca661c1e-cab1-611d-e053-5a18000af938",
                "language": "sr-Cyrl-RS",
                "active": True,
                "type": ["team"],
                "name": "Служба за лабораторијску дијагностику",
                "partOf": {
                    "reference": "Organization/ca65fdc3-3516-4830-e053-5a18000af96e",
                    "type": "Organization",
                },
                "address": [{"type": "both", "country": "RS"}],
            },
            {
                "resourceType": "http://hl7.org/fhir/resource-types#Organization",
                "id": "ca65fdc3-3516-4830-e053-5a18000af96e",
                "language": "sr-Cyrl-RS",
                "identifier": [
                    {
                        "use": "official",
                        "type": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                                    "code": "XX",
                                }
                            ],
                            "text": "Matični broj",
                        },
                        "system": "http://www.apr.gov.rs/регистри/здравствене-установе",
                        "value": "17078712",
                    },
                    {
                        "use": "official",
                        "type": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                                    "code": "TAX",
                                }
                            ],
                            "text": "PIB",
                        },
                        "system": "http://www.purs.gov.rs/pib.html",
                        "value": "101739057",
                    },
                ],
                "active": True,
                "type": ["prov"],
                "name": 'ИНСТИТУТ ЗА ВИРУСОЛОГИЈУ, ВАКЦИНЕ И СЕРУМЕ "ТОРЛАК"',
                "telecom": [
                    {"system": "email", "value": "office@torlak.rs", "rank": 1},
                    {"system": "phone", "value": "+381113953700", "rank": 3},
                ],
                "address": [
                    {
                        "type": "both",
                        "line": ["Војводе Степе 458"],
                        "city": "Београд",
                        "country": "RS",
                    }
                ],
            },
        ],
    },
    "name": "VDEL Lab Report",
}


def get_test_data():
    vc_record_list = []
    for cred in CRED_LIST:
        vc_record_list.append(
            create_vcrecord(
                cred,
                [
                    "https://www.w3.org/2018/credentials#VerifiableCredential",
                    "https://w3id.org/citizenship#PermanentResidentCard",
                ],
            )
        )
    pd_json_list = [
        (pres_exch_multiple_srs_not_met, 0),
        (pres_exch_multiple_srs_met_one_of_filter_invalid, 0),
        (pres_exch_multiple_srs_met_one_of_valid, 4),
        (pres_exch_datetime_minimum_met, 6),
        (pres_exch_datetime_maximum_met, 6),
        (pres_exch_nested_srs_a, 4),
        (pres_exch_nested_srs_b, 5),
        (pres_exch_nested_srs_c, 2),
    ]

    pd_list = []
    for pd in pd_json_list:
        pd_list.append(
            (
                PresentationDefinition.deserialize(json.loads(pd[0])),
                pd[1],
            )
        )
    return (vc_record_list, pd_list)
