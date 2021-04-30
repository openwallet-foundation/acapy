BBS_SIGNED_NESTED_VC_MATTR = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
        "https://w3id.org/security/bbs/v1",
    ],
    "id": "https://example.gov/credentials/3732",
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
    "issuer": "did:example:489398593",
    "issuanceDate": "2020-03-10T04:24:12.164Z",
    "credentialSubject": {
        "id": "did:example:489398593",
        "degree": {
            "type": "BachelorDegree",
            "name": "Bachelor of Science and Arts",
            "degreeType": "Underwater Basket Weaving",
        },
        "college": "Contoso University",
    },
    "proof": {
        "type": "BbsBlsSignature2020",
        "created": "2021-04-26T17:55:05Z",
        "proofPurpose": "assertionMethod",
        "proofValue": "t63mgQTFa5eMU0iIpCKtqyuJxC0S7nRE7fJ1g+/YhGnQqTZjAVzdB6mz+B/rEbJFRjoLnV8aJoyX0SXKEZQCZDinxaWksRnSqsDIGz/MVn4ovSqC5zGcApcCidsEO4S77RANaXba6hRHWrjhJGoMPg==",
        "verificationMethod": "did:example:489398593#test",
    },
}
