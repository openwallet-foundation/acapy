TEST_LD_DOCUMENT_BAD_SIGNED_BBS = {
    "@context": [
        {
            "schema": "http://schema.org/",
            "name": "schema:name",
            "homepage": "schema:url",
            "image": "schema:image",
        },
        "https://w3id.org/security/bbs/v1",
    ],
    "name": "John Doe",
    "homepage": "https://domain.com/profile",
    "proof": {
        "type": "BbsBlsSignature2020",
        "created": "2020-04-18T02:41:11Z",
        "verificationMethod": "did:example:489398593#test",
        "proofPurpose": "assertionMethod",
        "signature": "cBJG+AYOEuLd3MwsOC1xyPRcmspso687W24zSvduShKbL0xCJk7f0rrEpKkBpYPHThU3f3gP0d4amCQ9QLkGT5Z9mw2r2MakfdliAhnVt/CvV1IEEyouFAqzCiEyfxhU1wAAAAAAAAAAAAAAAAAAAABT3s/8eZfUJrJNLFxMiMnIhYWQvkqA80eRpwTZKWjRUwAAAAAAAAAAAAAAAAAAAAADp+HUtElIe+t1Pb0tiqrodTEb+pU4i9tDihJBY0xODA==",
    },
}
