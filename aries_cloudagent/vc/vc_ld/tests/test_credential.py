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
        "created": "2019-12-11T03:50:55",
        "proofPurpose": "assertionMethod",
        "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..lKJU0Df_keblRKhZAS9Qq6zybm-HqUXNVZ8vgEPNTAjQKBhQDxvXNo7nvtUBb_Eq1Ch6YBKY7UBAjg6iBX5qBQ",
    },
}

CREDENTIAL_VERIFIED = {
    "verified": True,
    "results": [
        {
            "proof": {
                "@context": "https://w3id.org/security/v2",
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "created": "2019-12-11T03:50:55",
                "proofPurpose": "assertionMethod",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..lKJU0Df_keblRKhZAS9Qq6zybm-HqUXNVZ8vgEPNTAjQKBhQDxvXNo7nvtUBb_Eq1Ch6YBKY7UBAjg6iBX5qBQ",
            },
            "verified": True,
            "purpose_result": {"valid": True},
        }
    ],
}
