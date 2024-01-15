from marshmallow import Schema, fields


class IssueCredentialRequest(Schema):
    """Issue credential request.

    Based on https://w3c-ccg.github.io/vc-api/#issue-credential

    """

    credential = fields.Dict(
        metadata={
            "example": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "credentialSubject": {"id": "did:key:..."},
                "issuanceDate": "2010-01-01T19:23:24Z",
                "issuer": "did:key:...",
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
                "issuer": "did:key:...",
                "issuanceDate": "2010-01-01T19:23:24Z",
                "credentialSubject": {"id": "did:key:..."},
                "proof": {
                    "type": "Ed25519Signature2018",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": "did:key:...#...",
                    "created": "2024-01-14T20:04:36+00:00",
                    "jws": "ey...",
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
                "holder": "did:key:...",
                "verifiableCredential": [
                    {
                        "@context": ["https://www.w3.org/2018/credentials/v1"],
                        "type": ["VerifiableCredential"],
                        "issuer": "did:key:...",
                        "issuanceDate": "2010-01-01T19:23:24Z",
                        "credentialSubject": {"id": "did:key:..."},
                        "proof": {
                            "type": "Ed25519Signature2018",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": "did:key:...#...",
                            "created": "2024-01-14T20:04:36+00:00",
                            "jws": "ey...",
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
                "holder": "did:key:...",
                "verifiableCredential": [
                    {
                        "@context": ["https://www.w3.org/2018/credentials/v1"],
                        "credentialSubject": {"id": "did:key:..."},
                        "issuanceDate": "2010-01-01T19:23:24Z",
                        "issuer": "did:key:...",
                        "type": ["VerifiableCredential"],
                        "proof": {
                            "type": "Ed25519Signature2018",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": "did:key:...#...",
                            "created": "2024-01-14T18:33:31+00:00",
                            "jws": "ey...",
                        },
                    }
                ],
                "proof": {
                    "type": "Ed25519Signature2018",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": "did:key:...#...",
                    "created": "2024-01-14T22:03:36+00:00",
                    "jws": "ey...",
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
