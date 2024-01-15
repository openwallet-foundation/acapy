from marshmallow import Schema, fields


class IssueCredentialRequest(Schema):
    credential = fields.Dict(
        metadata={
            "example": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "credentialSubject": {
                    "id": "did:key:z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH"
                },
                "issuanceDate": "2010-01-01T19:23:24Z",
                "issuer": "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i",
                "type": ["VerifiableCredential"],
            }
        }
    )
    options = fields.Dict(metadata={"example": {}})


class IssueCredentialResponse(Schema):
    verifiableCredential = fields.Dict(
        metadata={
            "example": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiableCredential"],
                "issuer": "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i",
                "issuanceDate": "2010-01-01T19:23:24Z",
                "credentialSubject": {
                    "id": "did:key:z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH"
                },
                "proof": {
                    "type": "Ed25519Signature2018",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i#z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i",
                    "created": "2024-01-14T20:04:36+00:00",
                    "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..Bzqa-eV0PfmTzWV0Gh0EMZwdpZ8w08TFKcVy0XD5HKvcPvkovL6bfERVgYEAnE72HQoVE3H7o3LxCGlJ4wQ5Dg",
                },
            }
        }
    )


VerifyCredentialRequest = IssueCredentialResponse()


class VerifyCredentialResponse(Schema):
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
    presentation = fields.Dict(
        metadata={
            "example": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiablePresentation"],
                "holder": "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i",
                "verifiableCredential": [
                    {
                        "@context": ["https://www.w3.org/2018/credentials/v1"],
                        "type": ["VerifiableCredential"],
                        "issuer": "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i",
                        "issuanceDate": "2010-01-01T19:23:24Z",
                        "credentialSubject": {
                            "id": "did:key:z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH"
                        },
                        "proof": {
                            "type": "Ed25519Signature2018",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i#z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i",
                            "created": "2024-01-14T20:04:36+00:00",
                            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..Bzqa-eV0PfmTzWV0Gh0EMZwdpZ8w08TFKcVy0XD5HKvcPvkovL6bfERVgYEAnE72HQoVE3H7o3LxCGlJ4wQ5Dg",
                        },
                    }
                ],
            }
        }
    )
    options = fields.Dict(metadata={"example": {}})


class ProvePresentationResponse(Schema):
    verifiablePresentation = fields.Dict(
        metadata={
            "example": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiablePresentation"],
                "holder": "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i",
                "verifiableCredential": [
                    {
                        "@context": ["https://www.w3.org/2018/credentials/v1"],
                        "credentialSubject": {
                            "id": "did:key:z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH"
                        },
                        "issuanceDate": "2010-01-01T19:23:24Z",
                        "issuer": "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i",
                        "type": ["VerifiableCredential"],
                        "proof": {
                            "type": "Ed25519Signature2018",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i#z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i",
                            "created": "2024-01-14T18:33:31+00:00",
                            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..6pZj4jcXbE4hCzdRYULsJO37A-19Od3ynLpZJsDB6tjDgYqrKhuOcbulE2yVCOwS8YSlpjO46F-c8a5NcVsXDQ",
                        },
                    }
                ],
                "proof": {
                    "type": "Ed25519Signature2018",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": "did:key:z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i#z6MkukGVb3mRvTu1msArDKY9UwxeZFGjmwnCKtdQttr4Fk6i",
                    "created": "2024-01-14T22:03:36+00:00",
                    "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..k55LG1o_-vcURKx8sSlAc7h_jtot3Zp18lukljF9B0esj1UL18hBBcunUoZxT9hT6zrFOGDPoQqpTHXj2a6QAw",
                },
            }
        }
    )


VerifyPresentationRequest = ProvePresentationResponse()


class VerifyPresentationResponse(Schema):
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
