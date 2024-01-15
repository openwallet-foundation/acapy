from marshmallow import Schema, fields

SUBJECT_DID = 'did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i'
ISSUER_DID = 'did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i'

class IssueCredentialRequest(Schema):
    """Issue credential request.

    Based on https://w3c-ccg.github.io/vc-api/#issue-credential

    """

    credential = fields.Dict(
        metadata={
            "example": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "credentialSubject": {
                    "id": SUBJECT_DID
                },
                "issuanceDate": "2010-01-01T19:23:24Z",
                "issuer": ISSUER_DID,
                "type": ["VerifiableCredential"],
            }
        }
    )
    options = fields.Dict(metadata={"example": {}})


class IssueCredentialResponse(Schema):
    """Issue credential response.

    Based on https://w3c-ccg.github.io/vc-api/#issue-credential

    """

    verifiableCredential = fields.Dict(
        metadata={
            "example": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiableCredential"],
                "issuer": ISSUER_DID,
                "issuanceDate": "2010-01-01T19:23:24Z",
                "credentialSubject": {
                    "id": SUBJECT_DID
                },
                "proof": {
                    "type": "Ed25519Signature2018",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": f'{ISSUER_DID}#{ISSUER_DID.split(":")[-1]}',
                    "created": "2024-01-14T20:04:36+00:00",
                    "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..\
                        Bzqa-eV0PfmTzWV0Gh0EMZwdpZ8w08TFKcVy0XD5HKvcPvkovL6bfERVgYEAnE72HQoVE3H7o3LxCGlJ4wQ5Dg",
                },
            }
        }
    )


VerifyCredentialRequest = IssueCredentialResponse()


class VerifyCredentialResponse(Schema):
    """Verify credential response.

    Based on https://w3c-ccg.github.io/vc-api/#verify-credential

    """

    verified = fields.Bool(metadata={"example": True})
    document = fields.Dict(metadata={"example": {}})
    # results = fields.List(
    #     metadata={
    #         "example": [{
    #             "verified": True,
    #             "proof": {},
    #             "purpose_result": {
    #                 "valid": True,
    #                 "controller": {}
    #             }
    #         }]
    #     }
    # )


class ProvePresentationRequest(Schema):
    """Prove presentation request.

    Based on https://w3c-ccg.github.io/vc-api/#prove-presentation

    """

    presentation = fields.Dict(
        metadata={
            "example": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiablePresentation"],
                "holder": ISSUER_DID,
                "verifiableCredential": [
                    {
                        "@context": ["https://www.w3.org/2018/credentials/v1"],
                        "type": ["VerifiableCredential"],
                        "issuer": ISSUER_DID,
                        "issuanceDate": "2010-01-01T19:23:24Z",
                        "credentialSubject": {
                            "id": SUBJECT_DID
                        },
                        "proof": {
                            "type": "Ed25519Signature2018",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": f'{ISSUER_DID}#{ISSUER_DID.split(":")[-1]}',
                            "created": "2024-01-14T20:04:36+00:00",
                            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..\
                                Bzqa-eV0PfmTzWV0Gh0EMZwdpZ8w08TFKcVy0XD5HKvcPvkovL6bfERVgYEAnE72HQoVE3H7o3LxCGlJ4wQ5Dg",
                        },
                    }
                ],
            }
        }
    )
    options = fields.Dict(metadata={"example": {}})


class ProvePresentationResponse(Schema):
    """Prove presentation response.

    Based on https://w3c-ccg.github.io/vc-api/#prove-presentation

    """

    verifiablePresentation = fields.Dict(
        metadata={
            "example": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiablePresentation"],
                "holder": ISSUER_DID,
                "verifiableCredential": [
                    {
                        "@context": ["https://www.w3.org/2018/credentials/v1"],
                        "credentialSubject": {
                            "id": SUBJECT_DID
                        },
                        "issuanceDate": "2010-01-01T19:23:24Z",
                        "issuer": ISSUER_DID,
                        "type": ["VerifiableCredential"],
                        "proof": {
                            "type": "Ed25519Signature2018",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": f'{ISSUER_DID}#{ISSUER_DID.split(":")[-1]}',
                            "created": "2024-01-14T18:33:31+00:00",
                            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..\
                                6pZj4jcXbE4hCzdRYULsJO37A-19Od3ynLpZJsDB6tjDgYqrKhuOcbulE2yVCOwS8YSlpjO46F-c8a5NcVsXDQ",
                        },
                    }
                ],
                "proof": {
                    "type": "Ed25519Signature2018",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": f'{ISSUER_DID}#{ISSUER_DID.split(":")[-1]}',
                    "created": "2024-01-14T22:03:36+00:00",
                    "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..\
                        k55LG1o_-vcURKx8sSlAc7h_jtot3Zp18lukljF9B0esj1UL18hBBcunUoZxT9hT6zrFOGDPoQqpTHXj2a6QAw",
                },
            }
        }
    )


VerifyPresentationRequest = ProvePresentationResponse()


class VerifyPresentationResponse(Schema):
    """Verify presentation response.

    Based on https://w3c-ccg.github.io/vc-api/#verify-presentation

    """

    verified = fields.Bool(metadata={"example": True})
    presentation_result = fields.Dict(
        metadata={
            "example": {
                "verified": True,
                "document": {},
            }
        }
    )
    # credential_results = fields.List(
    #     metadata={
    #         "example": [{
    #             "verified": True,
    #             "document": {},
    #         }]
    #     }
    # )
