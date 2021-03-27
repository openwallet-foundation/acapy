from ..validation_result import DocumentVerificationResult, ProofResult, PurposeResult

DOC_TEMPLATE = {
    "@context": [
        "https://w3id.org/security/v2",
        {
            "schema": "http://schema.org/",
            "name": "schema:name",
            "homepage": "schema:url",
            "image": "schema:image",
        },
    ],
    "name": "Manu Sporny",
    "homepage": "https://manu.sporny.org/",
    "image": "https://manu.sporny.org/images/manu.png",
}

DOC_SIGNED = {
    "@context": [
        "https://w3id.org/security/v2",
        {
            "schema": "http://schema.org/",
            "name": "schema:name",
            "homepage": "schema:url",
            "image": "schema:image",
        },
    ],
    "name": "Manu Sporny",
    "homepage": "https://manu.sporny.org/",
    "image": "https://manu.sporny.org/images/manu.png",
    "proof": {
        "proofPurpose": "assertionMethod",
        "created": "2019-12-11T03:50:55",
        "type": "Ed25519Signature2018",
        "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
        "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..Q6amIrxGiSbM7Ce6DxlfwLCjVcYyclas8fMxaecspXFUcFW9DAAxKzgHx93FWktnlZjM_biitkMgZdStgvivAQ",
    },
}

DOC_VERIFIED = DocumentVerificationResult(
    verified=True,
    document={
        "@context": [
            "https://w3id.org/security/v2",
            {
                "schema": "http://schema.org/",
                "name": "schema:name",
                "homepage": "schema:url",
                "image": "schema:image",
            },
        ],
        "name": "Manu Sporny",
        "homepage": "https://manu.sporny.org/",
        "image": "https://manu.sporny.org/images/manu.png",
        "proof": {
            "proofPurpose": "assertionMethod",
            "created": "2019-12-11T03:50:55",
            "type": "Ed25519Signature2018",
            "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..Q6amIrxGiSbM7Ce6DxlfwLCjVcYyclas8fMxaecspXFUcFW9DAAxKzgHx93FWktnlZjM_biitkMgZdStgvivAQ",
        },
    },
    results=[
        ProofResult(
            verified=True,
            proof={
                "@context": [
                    "https://w3id.org/security/v2",
                    {
                        "schema": "http://schema.org/",
                        "name": "schema:name",
                        "homepage": "schema:url",
                        "image": "schema:image",
                    },
                ],
                "proofPurpose": "assertionMethod",
                "created": "2019-12-11T03:50:55",
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..Q6amIrxGiSbM7Ce6DxlfwLCjVcYyclas8fMxaecspXFUcFW9DAAxKzgHx93FWktnlZjM_biitkMgZdStgvivAQ",
            },
            purpose_result=PurposeResult(
                valid=True,
                controller={
                    "@context": "https://w3id.org/security/v2",
                    "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "assertionMethod": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "authentication": [
                        {
                            "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "publicKeyBase58": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
                        }
                    ],
                    "capabilityDelegation": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "capabilityInvocation": [
                        "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
                    ],
                    "keyAgreement": [
                        {
                            "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6LSbkodSr6SU2trs8VUgnrnWtSm7BAPG245ggrBmSrxbv1R",
                            "type": "X25519KeyAgreementKey2019",
                            "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                            "publicKeyBase58": "5dTvYHaNaB7mk7iA9LqCJEHG2dGZQsvoi8WGzDRtYEf",
                        }
                    ],
                    "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                },
            ),
        )
    ],
)
