BBS_SIGNED_NESTED_VC_MATTR = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
        "https://w3id.org/security/bbs/v1",
    ],
    "id": "https://example.gov/credentials/3732",
    "type": ["VerifiableCredential", "UniversityDegreeCredential"],
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
        "created": "2020-12-14T03:11:30Z",
        "proofPurpose": "assertionMethod",
        "proofValue": "sd8eqx9NWOOVXl7MBLmIOUg0GlOvrP2a+sRPHdcKuapZ7r2K6nNNJ//MOmj9ffRqax6THf0TbvmnXiOo1c4kA29aUsGpZSBbIKPsaNhnJ94KzP5e9+Bm4/FIPjn4magC8b8S8+SMjTrAqXuxMg+BEQ==",
        "verificationMethod": "did:example:489398593#test",
    },
}
