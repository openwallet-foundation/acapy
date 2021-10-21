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
        "created": "2019-12-11T03:50:55+00:00",
        "type": "Ed25519Signature2018",
        "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
        "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..FX3xSAN3BxpHnclqtiCKsHa3f6O1pi_fulEoCNs2YQplYBU7lYSdnIm1BoPo_YCw8AS25pOQo1ufW05mXJlxAw",
    },
}

DOC_TEMPLATE_BBS = {
    "@context": [
        "https://w3id.org/security/v2",
        "https://w3id.org/security/bbs/v1",
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

DOC_FRAME_BBS = {
    "@context": [
        "https://w3id.org/security/v2",
        "https://w3id.org/security/bbs/v1",
        {
            "schema": "http://schema.org/",
            "name": "schema:name",
            "homepage": "schema:url",
            "image": "schema:image",
        },
    ],
    "@explicit": True,
    "name": {},
}

DOC_SIGNED_BBS = {
    "@context": [
        "https://w3id.org/security/v2",
        "https://w3id.org/security/bbs/v1",
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
        "type": "BbsBlsSignature2020",
        "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
        "created": "2019-12-11T03:50:55",
        "proofPurpose": "assertionMethod",
        "proofValue": "jYdVXtAFahqd9Zp09EEQuALXFDhKTz/GfbfvjksFEzOl4zrk4xprdJo5eRcpKr2URlpAFRZ9Civr4h3++a2/Vk9sLZ5cm4/LWeY2H0PQEIcizdIX83n0LvNZoS1+jeCI2b2C6UDva3CzFyVHHKOZfw==",
    },
}

DOC_DERIVED_BBS = {
    "@context": [
        "https://w3id.org/security/v2",
        "https://w3id.org/security/bbs/v1",
        {
            "schema": "http://schema.org/",
            "name": "schema:name",
            "homepage": "schema:url",
            "image": "schema:image",
        },
    ],
    "id": "urn:bnid:_:c14n0",
    "name": "Manu Sporny",
    "proof": {
        "type": "BbsBlsSignatureProof2020",
        "nonce": "801XIat4aOz6K0VKiZoNml5X1/6g7dprU1fOyhDvGaZz5bOcmlws3SN4+ac7KfDoD0w=",
        "proofValue": "AAcvk/vII8D39ei+76WGZB0HIv8ZBwyyN3A7gE9ziOKgTfdLH+icCrk1AuqIX0wgRjHMgqtsRb9jtO76JK8NcPeBQAVA0PFrf3I3BRKssVkWhg+hgTUOxbTd1lGcqaiHLDlOqFuPSazkT2n8YZ+GgqooLImaGNLOuUuHxQo+jS0bSCXeeOWvarQyYRoehUEyjNd2AAAAdIl2Qtkgcty4dZPrxK7+VpKkkqtrfLMh/ioJlLVp2/n1hfvaljeeekXEmSIoSDII4gAAAAIQRfaHQzTH4OYd2Jk85iMNGiMzPBpWtjfovn+3j0kTkw3Bv6Vh5PZRJtZI4G32c4k/sxFyTlRvmToIF8VUg9OkmJNIeHJ9Re8BA1kcQBM88YgfTDndKjQg8mmV0LU8mvJxD1RM2yKaYJ5dNJDMouEFAAAABCRy/HyI8YYfcV2opKNCz5jzMmQkCIjJNbDYzvf8/6RuVgljJeb7o3MLKWfxE8hyuaa/SQ/sqV+cGsBtM00iL+lbuDByo0s5RE+i71ZBHPGwCQtmAqkvnDdtPwl0HuA9IUqckIe0OVVvxydVzhU37pf4mG6yCaFHOaHQ02jeYqLT",
        "verificationMethod": "did:key:zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa#zUC72Q7XD4PE4CrMiDVXuvZng3sBvMmaGgNeTUJuzavH2BS7ThbHL9FhsZM9QYY5fqAQ4MB8M9oudz3tfuaX36Ajr97QRW7LBt6WWmrtESe6Bs5NYzFtLWEmeVtvRYVAgjFcJSa",
        "proofPurpose": "assertionMethod",
        "created": "2019-12-11T03:50:55",
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
            "created": "2019-12-11T03:50:55+00:00",
            "type": "Ed25519Signature2018",
            "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..FX3xSAN3BxpHnclqtiCKsHa3f6O1pi_fulEoCNs2YQplYBU7lYSdnIm1BoPo_YCw8AS25pOQo1ufW05mXJlxAw",
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
                "created": "2019-12-11T03:50:55+00:00",
                "type": "Ed25519Signature2018",
                "verificationMethod": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..FX3xSAN3BxpHnclqtiCKsHa3f6O1pi_fulEoCNs2YQplYBU7lYSdnIm1BoPo_YCw8AS25pOQo1ufW05mXJlxAw",
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
