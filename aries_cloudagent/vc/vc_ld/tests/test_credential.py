from ...ld_proofs import (
    DocumentVerificationResult,
    ProofResult,
    PurposeResult,
)

# All signed documents manually tested for validity on https://univerifier.io

CREDENTIAL_TEMPLATE = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
    ],
    "id": "http://example.gov/credentials/3732",
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
    "issuer": {"id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"},
    "issuanceDate": "2020-03-10T04:24:12.164Z",
    "credentialSubject": {
        "id": "did:example:456",
        "degree": {"type": "BachelorDegree", "name": "Bachelor of Science and Arts"},
    },
}

CREDENTIAL_ISSUED = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
    ],
    "id": "http://example.gov/credentials/3732",
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
    "issuer": {"id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"},
    "issuanceDate": "2020-03-10T04:24:12.164Z",
    "credentialSubject": {
        "id": "did:example:456",
        "degree": {"type": "BachelorDegree", "name": "Bachelor of Science and Arts"},
    },
    "proof": {
        "type": "Ed25519Signature2018",
        "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
        "created": "2019-12-11T03:50:55+00:00",
        "proofPurpose": "assertionMethod",
        "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..tELgWSCo0jSOKLpHWLOe2ZWj6WxLFc6FcqBZzgQFdcaawC5mARYmdr0XA37TMUp2Q9jUwriNP4gQm3GFIHV9BQ",
    },
}

CREDENTIAL_TEMPLATE_2020 = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
        "https://w3id.org/security/suites/ed25519-2020/v1",
    ],
    "id": "http://example.gov/credentials/3732",
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
    "issuer": {"id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"},
    "issuanceDate": "2020-03-10T04:24:12.164Z",
    "credentialSubject": {
        "id": "did:example:456",
        "degree": {"type": "BachelorDegree", "name": "Bachelor of Science and Arts"},
    },
}

CREDENTIAL_ISSUED_2020 = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
        "https://w3id.org/security/suites/ed25519-2020/v1",
    ],
    "id": "http://example.gov/credentials/3732",
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
    "issuer": {"id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"},
    "issuanceDate": "2020-03-10T04:24:12.164Z",
    "credentialSubject": {
        "id": "did:example:456",
        "degree": {"type": "BachelorDegree", "name": "Bachelor of Science and Arts"},
    },
    "proof": {
        "type": "Ed25519Signature2020",
        "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
        "created": "2019-12-11T03:50:55+00:00",
        "proofPurpose": "assertionMethod",
        "proofValue": "z3AkzFbAERyy7KwTDbafaMjoeYejfnzMfjV1eG93j1yhsPGGTJWeyxcWVexxg84AsnRDmMFeVN6SN2dbxCsTsn2eY",
    },
}

CREDENTIAL_TEMPLATE_BBS = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/security/bbs/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
    ],
    "id": "http://example.gov/credentials/3732",
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
    "issuer": {
        "id": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa"
    },
    "issuanceDate": "2020-03-10T04:24:12.164Z",
    "credentialSubject": {
        "id": "did:example:456",
        "degree": {"type": "BachelorDegree", "name": "Bachelor of Science and Arts"},
    },
}

CREDENTIAL_ISSUED_BBS = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/security/bbs/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
    ],
    "id": "http://example.gov/credentials/3732",
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
    "issuer": {
        "id": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa"
    },
    "issuanceDate": "2020-03-10T04:24:12.164Z",
    "credentialSubject": {
        "id": "did:example:456",
        "degree": {"type": "BachelorDegree", "name": "Bachelor of Science and Arts"},
    },
    "proof": {
        "type": "BbsBlsSignature2020",
        "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
        "created": "2019-12-11T03:50:55+00:00",
        "proofPurpose": "assertionMethod",
        "proofValue": "ke/4UsKMbYyFQP2WAsQs0QGJ0PCfvN3tWMoD8oBjroY3mrgXA7FmUqVy0HaZIoKvFHl1FnE1jqh0OnqErooFBMTu0a4qe3klziRSuRuLdUhgbgzOJeJiWPlrs6Y5/D5d0CRp8ifPj7xZBIy3Iuoz4g==",
    },
}

CREDENTIAL_VERIFIED = DocumentVerificationResult(
    verified=True,
    document={
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "id": "http://example.gov/credentials/3732",
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": {"id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"},
        "issuanceDate": "2020-03-10T04:24:12.164Z",
        "credentialSubject": {
            "id": "did:example:456",
            "degree": {
                "type": "BachelorDegree",
                "name": "Bachelor of Science and Arts",
            },
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
            "created": "2019-12-11T03:50:55+00:00",
            "proofPurpose": "assertionMethod",
            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..tELgWSCo0jSOKLpHWLOe2ZWj6WxLFc6FcqBZzgQFdcaawC5mARYmdr0XA37TMUp2Q9jUwriNP4gQm3GFIHV9BQ",
        },
    },
    results=[
        ProofResult(
            verified=True,
            proof={
                "@context": [
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2019-12-11T03:50:55+00:00",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..tELgWSCo0jSOKLpHWLOe2ZWj6WxLFc6FcqBZzgQFdcaawC5mARYmdr0XA37TMUp2Q9jUwriNP4gQm3GFIHV9BQ",
            },
            purpose_result=PurposeResult(
                valid=True,
                controller={
                    "@context": "https://w3id.org/security/v2",
                    "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "assertionMethod": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "authentication": [
                        {
                            "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "publicKeyBase58": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
                        }
                    ],
                    "capabilityDelegation": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "capabilityInvocation": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "keyAgreement": [
                        {
                            "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6LSbkodSr6SU2trs8VUgnrnWtSm7BAPG245ggrBmSrxbv1R",
                            "type": "X25519KeyAgreementKey2019",
                            "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "publicKeyBase58": "5dTvYHaNaB7mk7iA9LqCJEHG2dGZQsvoi8WGzDRtYEf",
                        }
                    ],
                    "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                },
            ),
        )
    ],
)

CREDENTIAL_VERIFIED_2020 = DocumentVerificationResult(
    verified=True,
    document={
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
            "https://w3id.org/security/suites/ed25519-2020/v1",
        ],
        "id": "http://example.gov/credentials/3732",
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": {"id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"},
        "issuanceDate": "2020-03-10T04:24:12.164Z",
        "credentialSubject": {
            "id": "did:example:456",
            "degree": {
                "type": "BachelorDegree",
                "name": "Bachelor of Science and Arts",
            },
        },
        "proof": {
            "type": "Ed25519Signature2020",
            "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
            "created": "2019-12-11T03:50:55+00:00",
            "proofPurpose": "assertionMethod",
            "proofValue": "z3AkzFbAERyy7KwTDbafaMjoeYejfnzMfjV1eG93j1yhsPGGTJWeyxcWVexxg84AsnRDmMFeVN6SN2dbxCsTsn2eY",
        },
    },
    results=[
        ProofResult(
            verified=True,
            proof={
                "@context": [
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                    "https://w3id.org/security/suites/ed25519-2020/v1",
                ],
                "type": "Ed25519Signature2020",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2019-12-11T03:50:55+00:00",
                "proofPurpose": "assertionMethod",
                "proofValue": "z3AkzFbAERyy7KwTDbafaMjoeYejfnzMfjV1eG93j1yhsPGGTJWeyxcWVexxg84AsnRDmMFeVN6SN2dbxCsTsn2eY",
            },
            purpose_result=PurposeResult(
                valid=True,
                controller={
                    "@context": "https://w3id.org/security/v2",
                    "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "assertionMethod": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "authentication": [
                        {
                            "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "publicKeyBase58": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
                        }
                    ],
                    "capabilityDelegation": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "capabilityInvocation": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "keyAgreement": [
                        {
                            "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6LSbkodSr6SU2trs8VUgnrnWtSm7BAPG245ggrBmSrxbv1R",
                            "type": "X25519KeyAgreementKey2019",
                            "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "publicKeyBase58": "5dTvYHaNaB7mk7iA9LqCJEHG2dGZQsvoi8WGzDRtYEf",
                        }
                    ],
                    "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                },
            ),
        )
    ],
)

PRESENTATION_UNSIGNED = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "type": ["VerifiablePresentation"],
    "verifiableCredential": [
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            "id": "http://example.gov/credentials/3732",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": {
                "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            },
            "issuanceDate": "2020-03-10T04:24:12.164Z",
            "credentialSubject": {
                "id": "did:example:456",
                "degree": {
                    "type": "BachelorDegree",
                    "name": "Bachelor of Science and Arts",
                },
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2019-12-11T03:50:55+00:00",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..tELgWSCo0jSOKLpHWLOe2ZWj6WxLFc6FcqBZzgQFdcaawC5mARYmdr0XA37TMUp2Q9jUwriNP4gQm3GFIHV9BQ",
            },
        }
    ],
}

PRESENTATION_SIGNED = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "type": ["VerifiablePresentation"],
    "verifiableCredential": [
        {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            "id": "http://example.gov/credentials/3732",
            "type": ["VerifiableCredential", "UniversityDegreeCredential"],
            "issuer": {
                "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            },
            "issuanceDate": "2020-03-10T04:24:12.164Z",
            "credentialSubject": {
                "id": "did:example:456",
                "degree": {
                    "type": "BachelorDegree",
                    "name": "Bachelor of Science and Arts",
                },
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2019-12-11T03:50:55+00:00",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..tELgWSCo0jSOKLpHWLOe2ZWj6WxLFc6FcqBZzgQFdcaawC5mARYmdr0XA37TMUp2Q9jUwriNP4gQm3GFIHV9BQ",
            },
        }
    ],
    "proof": {
        "type": "Ed25519Signature2018",
        "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
        "created": "2020-12-11T03:50:55+00:00",
        "proofPurpose": "authentication",
        "challenge": "2b1bbff6-e608-4368-bf84-67471b27e41c",
        "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..vLk6iXrPxdt4xWq_Lwnd85cy17Npol1ALxYoMhZrKpmkaWDOoz_exP1ggurPik7Rhpa7a82AfrT0OnigJnJsAQ",
    },
}
