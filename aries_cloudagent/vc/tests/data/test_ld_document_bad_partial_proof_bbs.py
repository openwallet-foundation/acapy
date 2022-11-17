TEST_LD_DOCUMENT_BAD_PARTIAL_PROOF_BBS = {
    "@context": [
        {
            "schema": "http://schema.org/",
            "firstName": "schema:firstName",
            "lastName": "schema:lastName",
            "jobTitle": "schema:jobTitle",
            "telephone": "schema:telephone",
            "email": "schema:email",
        },
        "https://w3id.org/security/v3-unstable",
    ],
    "@type": "Person",
    "lastName": "Does",
    "firstName": "Jane",
    "id": "urn:bnid:_:c14n0",
    "proof": {
        "type": "BbsBlsSignatureProof2020",
        "created": "2020-04-25T00:26:11Z",
        "verificationMethod": "did:example:489398593#test",
        "proofPurpose": "assertionMethod",
        "proofValue": "badNRdmxY/v6kFMJ49Y4tNtCmQK1ycU/GFqEsJSydeu3z0icyRnR7Up7kG/YBjJrgUUnDOBc4Bm8gBoOFfzu1rY1jwDWI5flVl3K+s7v5h+VSlQdWeHZPA8q7Y1mpCJLksmiigW6+ZAl/I9pol6xpNMq4oecqJmz3ZbXk4MX6WSj1oIDEQ+RgjE6gHB24ogAAAAAdI2rgDj2S93z0TLxPO3mpFR76H7srVmoncs4uH1Bl3INTK4aPdbS1GRoq9R9YgX2kgAAAAJhmY6QEDMqtDVKI90Ks6P3GLZG245Puvo5USUHumMxFw+hL4SERE3m6qtwdBBDD4H+gfVll3ha/1va6CuKOxtvC8HuSAyXmhGFPq8z91iPr5BdWSCSvIcz65bbN9R8KOSPdkJpJSePtiGNem6drQ8zAAAABSM+WfXNVDIK+HURPfFeM8ZHWrdxR//0u/NCuodBvSFfcFXEluMXXwfwKBHzPiC+dhKHLQ3pGgASk5xYVXfOAIkxB4kGGxSOfdJ+BaBM96TkEw2hrFBrXnjEKP/uMbUPzFEfJusTUINaNkMjLkqDftQKEAXCsUI0HPzGunMhvCvfJ+QzNfKEfernU12Hg+bblW8ZFIrWVyveQCn3MagxaEg=",
        "nonce": "U6PA9o5iHMWHcnud1KfzPzjCNpFs+dy60CU7201yWQLmcSL5XDiiMJ6j9z81eGoLm/I=",
    },
}
