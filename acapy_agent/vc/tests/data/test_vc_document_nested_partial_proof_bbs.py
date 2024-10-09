TEST_VC_DOCUMENT_NESTED_PARTIAL_PROOF_BBS = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
        "https://w3id.org/security/bbs/v1",
    ],
    "id": "https://example.gov/credentials/3732",
    "type": ["UniversityDegreeCredential", "VerifiableCredential"],
    "credentialSubject": {
        "id": "did:example:489398593",
        "degree": {
            "id": "urn:bnid:_:c14n0",
            "type": "BachelorDegree",
            "name": "Bachelor of Science and Arts",
        },
    },
    "issuanceDate": "2020-03-10T04:24:12.164Z",
    "issuer": "did:example:489398593",
    "proof": {
        "type": "BbsBlsSignatureProof2020",
        "created": "2021-04-26T17:55:05Z",
        "nonce": "58pQbOsBR7l+FwAGs1bDWiCyQXJFkmSNBHC0BDzX4BU6khM6VbJZBqb5RGONkGFJBNQ=",
        "proofPurpose": "assertionMethod",
        "proofValue": "AA4f74GNgyGujm0aHzKd2xuUpetxhpFaXhW6twInMfmFNZYW2/RlShvRGE6Ios/dgr5e+qyGGOGkBWSdSOaFGsseo6Ne/0429iKAZpWo/abD6r8kIszn8L5UL43NxCia/UtQB5HjqBPYelAsepN3aNryZNUc0h7UcyjTqgp9wGfPADW4KJIBXv4SvwqwRZgcDzdKxwAAAHSStf9LAUTsKXnlWL7hE0x86/4wzpDFRWCE/WgkCz/mqQlt+vlWDwm9k7PlwiPoLhYAAAACBLS2axWssG0oNnqk02If5qm6ToalAP/TGB/cORH00KNrKMvhMMwI54odGP5qy4qJmQp+cYcj4bffIfaXbRGNqJdHYKbeHk5ZV/A91vnI3mxQfhtKp1YmNC2DpUfw/hSTAubh5Iv2UMFWc1Gl+hYuDAAAAARiA7M07jBRe+QGbPgLg1nFgiD26GDBD+wYm93qM+HfwBKYqEbeXVveTsx589OTilT5HP2b6cOfSwCJyU8xU/uKPNYhNGqkGZgPXjIVfvRWFblSX822hnMBOYzdCroarsdUCom4NMlFvAQeZAQ6CtZUkXSKAizYCdx5yeHjjkveAg==",
        "verificationMethod": "did:example:489398593#test",
    },
}
