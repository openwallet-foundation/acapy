"""VC-API requests and responses examples"""

from marshmallow import Schema, fields

EXAMPLE_DID = "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i"
EXAMPLE_CRED_PROOF = "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..\
SCPQDsbwaEo7aZ28hrpWOPa8vu3CHqM0do6UkVNVM8hM0__1rryDnzeU-V7_lvjxrhqs998rhnojE4UuOLZTDw"
EXAMPLE_PRES_PROOF = "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..\
eqWrb_JcMPM1m1tBotnI01WPaV5_cQLUJslkT2oPD00MBb5xUZqIIzxCWdkYHhBo4IVDYCL3RkG5WDWdQ8AyBw"


class IssueCredentialRequest(Schema):
    """Issue credential request.

    Based on https://w3c-ccg.github.io/vc-api/#issue-credential

    """

    credential = fields.Dict(
        metadata={
            "example": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "credentialSubject": {"id": EXAMPLE_DID},
                "issuanceDate": "2010-01-01T19:23:24Z",
                "issuer": EXAMPLE_DID,
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
                "issuer": EXAMPLE_DID,
                "issuanceDate": "2010-01-01T19:23:24Z",
                "credentialSubject": {"id": EXAMPLE_DID},
                "proof": {
                    "type": "Ed25519Signature2018",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": f"{EXAMPLE_DID}#{EXAMPLE_DID.split(':')[-1]}",
                    "created": "2024-01-14T20:04:36+00:00",
                    "jws": EXAMPLE_CRED_PROOF,
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
                "holder": EXAMPLE_DID,
                "verifiableCredential": [
                    {
                        "@context": ["https://www.w3.org/2018/credentials/v1"],
                        "type": ["VerifiableCredential"],
                        "issuer": EXAMPLE_DID,
                        "issuanceDate": "2010-01-01T19:23:24Z",
                        "credentialSubject": {"id": EXAMPLE_DID},
                        "proof": {
                            "type": "Ed25519Signature2018",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": f"{EXAMPLE_DID}#{EXAMPLE_DID.split(':')[-1]}",
                            "created": "2024-01-14T20:04:36+00:00",
                            "jws": EXAMPLE_CRED_PROOF,
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
                "holder": EXAMPLE_DID,
                "verifiableCredential": [
                    {
                        "@context": ["https://www.w3.org/2018/credentials/v1"],
                        "credentialSubject": {"id": EXAMPLE_DID},
                        "issuanceDate": "2010-01-01T19:23:24Z",
                        "issuer": EXAMPLE_DID,
                        "type": ["VerifiableCredential"],
                        "proof": {
                            "type": "Ed25519Signature2018",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": f"{EXAMPLE_DID}#{EXAMPLE_DID.split(':')[-1]}",
                            "created": "2024-01-14T18:33:31+00:00",
                            "jws": EXAMPLE_CRED_PROOF,
                        },
                    }
                ],
                "proof": {
                    "type": "Ed25519Signature2018",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": f"{EXAMPLE_DID}#{EXAMPLE_DID.split(':')[-1]}",
                    "created": "2024-01-14T22:03:36+00:00",
                    "jws": EXAMPLE_PRES_PROOF,
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
