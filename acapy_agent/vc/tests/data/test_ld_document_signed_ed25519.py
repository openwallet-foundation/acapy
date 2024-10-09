TEST_LD_DOCUMENT_SIGNED_ED25519 = {
    "@context": ["http://schema.org/", "https://w3id.org/security/bbs/v1"],
    "@type": "Person",
    "firstName": "Jane",
    "lastName": "Does",
    "jobTitle": "Professor",
    "telephone": "(425) 123-4567",
    "email": "jane.doe@example.com",
    "proof": {
        "type": "Ed25519Signature2018",
        "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
        "created": "2021-04-26T20:21:49.045302",
        "proofPurpose": "assertionMethod",
        "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..UnUUc0S8ww-3fhX40IFfz9Ud_fqHurW4b4uovzBK3vQ8sVG-TMcXGNpC_v9QGZmWiOBOLNdOQOXUzLj2G88VCw",
    },
}
