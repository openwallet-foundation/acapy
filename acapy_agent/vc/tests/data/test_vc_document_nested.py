TEST_VC_DOCUMENT_NESTED = {
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
}
