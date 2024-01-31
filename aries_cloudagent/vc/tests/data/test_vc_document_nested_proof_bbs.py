TEST_VC_DOCUMENT_NESTED_PROOF_BBS = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
        "https://w3id.org/security/bbs/v1",
    ],
    "id": "https://example.gov/credentials/3732",
    "type": ["UniversityDegreeCredential", "VerifiableCredential"],
    "credentialSubject": {
        "id": "did:example:489398593",
        "college": "Contoso University",
        "degree": {
            "id": "urn:bnid:_:c14n0",
            "type": "BachelorDegree",
            "name": "Bachelor of Science and Arts",
            "degreeType": "Underwater Basket Weaving",
        },
    },
    "issuanceDate": "2020-03-10T04:24:12.164Z",
    "issuer": "did:example:489398593",
    "proof": {
        "type": "BbsBlsSignatureProof2020",
        "created": "2021-04-26T17:55:05Z",
        "nonce": "Vy7Mup3vFgTcs0NxggmHYMfIf7+ykk/M1a0+wRNjcGukpe/C2Rl7WvN1DVxCg8gvhng=",
        "proofPurpose": "assertionMethod",
        "proofValue": "AA4//7SYcnewiCvH+CG/CwNY4rXdpfZ/9j79GASJFWa6C9jwBzQenfeXtuMBvHCDvmpTqI5Dtf/7O938CV0qEtUTquPrT6stNxnCfJSPYmM78d48LJidPoLhdRjT+QNfj5sM647odR5b9JOMmW43yMUAxkb+A9bGNdixG5OqK3xLSuRHDkTIi1Lu6/x4xgOeR5KALAAAAHSYATbHEjd2sdxY9n7lzdWkta25moSE1UNZBO+B+nSysYlQYO9H9jX0zRrzUaKDnSAAAAACX8oBf2PCWC3U6jtaoRqO2pAmc4nXO2tqsnVm6zNBUmEQlWf32/Cl3VvyB2q9XBGagPDLiyxuDcSkoQRJX4D/M4IRx8LVMhIYPT4O4mDejKuFqFQN1PiVN4W+eR0I8KZ0Jq8QP97CM8/6YFg+fyuxdQAAAAJJotlRjal+sxbNpyVHU70FDv1icZyEFJwGm7HnFFh/iAqjP69KB37eou5Xt1TkM6fgK65gu0e4jTTALpk5tie3",
        "verificationMethod": "did:example:489398593#test",
    },
}
