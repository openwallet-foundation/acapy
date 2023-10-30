TEST_LD_DOCUMENT_SIGNED_BBS = {
    "@context": ["http://schema.org/", "https://w3id.org/security/bbs/v1"],
    "@type": "Person",
    "firstName": "Jane",
    "lastName": "Does",
    "jobTitle": "Professor",
    "telephone": "(425) 123-4567",
    "email": "jane.doe@example.com",
    "proof": {
        "type": "BbsBlsSignature2020",
        "created": "2020-10-30T04:34:10Z",
        "proofPurpose": "assertionMethod",
        "proofValue": "t+lSsiNnCYrVUzVsT1DoWMfZP5vHcXnrwo8kxSdsROv9+kTUjZWi5yEju4PZrHWwVPDP0AY2VYjDE5Y9QKYkxJ7PPg3CId2e/Wrk17Tjp31hEll7tBeMszRkTEUUb+gHSulYnYdN/Nvp/BWCekbuIg==",
        "verificationMethod": "did:example:489398593#test",
    },
}
