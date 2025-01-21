from ...ld_proofs import DocumentVerificationResult, ProofResult, PurposeResult

# All signed documents manually tested for validity on https://univerifier.io
DID = "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY"
CREDENTIAL_V2_TEMPLATE = {
    "@context": [
        "https://www.w3.org/ns/credentials/v2",
        "https://w3id.org/security/suites/ed25519-2020/v1",
    ],
    "type": ["VerifiableCredential"],
    "issuer": {"id": DID},
    "credentialSubject": {
        "id": "did:example:alice",
        "name": "Alice",
    },
}

CREDENTIAL_V2_ISSUED = {
    "@context": [
        "https://www.w3.org/ns/credentials/v2",
        "https://w3id.org/security/suites/ed25519-2020/v1",
    ],
    "type": ["VerifiableCredential"],
    "issuer": {"id": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY"},
    "credentialSubject": {"id": "did:example:alice", "name": "Alice"},
    "proof": {
        "type": "Ed25519Signature2020",
        "proofPurpose": "assertionMethod",
        "verificationMethod": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
        "created": "2025-01-21T01:35:19+00:00",
        "proofValue": "z5H6wcxVZrqyvxRaUFZaV86DYGqQPGuZqxhrL1LcqyQkY5Qk3CMbrnDNgFQkHyhRJgs8KuxcoBntnqNWsXGx17Y8C",
    },
}

CREDENTIAL_V2_VERIFIED = DocumentVerificationResult(
    verified=True,
    document={
        "@context": [
            "https://www.w3.org/ns/credentials/v2",
            "https://w3id.org/security/suites/ed25519-2020/v1",
        ],
        "type": ["VerifiableCredential"],
        "issuer": {"id": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY"},
        "credentialSubject": {"id": "did:example:alice", "name": "Alice"},
        "proof": {
            "type": "Ed25519Signature2020",
            "proofPurpose": "assertionMethod",
            "verificationMethod": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
            "created": "2025-01-21T01:35:19+00:00",
            "proofValue": "z5H6wcxVZrqyvxRaUFZaV86DYGqQPGuZqxhrL1LcqyQkY5Qk3CMbrnDNgFQkHyhRJgs8KuxcoBntnqNWsXGx17Y8C",
        },
    },
    results=[
        ProofResult(
            verified=True,
            proof={
                "@context": [
                    "https://www.w3.org/ns/credentials/v2",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ],
                "type": "Ed25519Signature2020",
                "proofPurpose": "assertionMethod",
                "verificationMethod": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
                "created": "2025-01-21T01:35:19+00:00",
                "proofValue": "z5H6wcxVZrqyvxRaUFZaV86DYGqQPGuZqxhrL1LcqyQkY5Qk3CMbrnDNgFQkHyhRJgs8KuxcoBntnqNWsXGx17Y8C",
            },
            purpose_result=PurposeResult(
                valid=True,
                controller={
                    "@context": "https://w3id.org/security/v2",
                    "id": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
                    "assertionMethod": [
                        "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY"
                    ],
                    "authentication": [
                        {
                            "id": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
                            "publicKeyBase58": "PJqejWkb8KrkZaWxBkMUQGwcWEzUEg4GcCWyrrBaFXA",
                        }
                    ],
                    "capabilityDelegation": [
                        "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY"
                    ],
                    "capabilityInvocation": [
                        "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY"
                    ],
                    "keyAgreement": [
                        {
                            "id": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6LSpHZPMMLSRe4XwbNfQoqj1rq5zEZYfGQMjFVbdQmQLT9D",
                            "type": "X25519KeyAgreementKey2019",
                            "controller": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
                            "publicKeyBase58": "DcPDq3XaLBLnrCzttAKmhGcc962RxfECrGmv8x7sd5NT",
                        }
                    ],
                    "verificationMethod": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
                },
            ),
        )
    ],
)

PRESENTATION_V2_UNSIGNED = {
    "@context": ["https://www.w3.org/ns/credentials/v2"],
    "type": ["VerifiablePresentation"],
    "verifiableCredential": [
        {
            "@context": [
                "https://www.w3.org/ns/credentials/v2",
                "https://w3id.org/security/suites/ed25519-2020/v1",
            ],
            "type": ["VerifiableCredential"],
            "issuer": {"id": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY"},
            "credentialSubject": {"id": "did:example:alice", "name": "Alice"},
            "proof": {
                "type": "Ed25519Signature2020",
                "proofPurpose": "assertionMethod",
                "verificationMethod": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
                "created": "2025-01-21T01:35:19+00:00",
                "proofValue": "z5H6wcxVZrqyvxRaUFZaV86DYGqQPGuZqxhrL1LcqyQkY5Qk3CMbrnDNgFQkHyhRJgs8KuxcoBntnqNWsXGx17Y8C",
            },
        }
    ],
}

PRESENTATION_V2_SIGNED = {
    "verifiablePresentation": {
        "@context": [
            "https://www.w3.org/ns/credentials/v2",
            "https://w3id.org/security/suites/ed25519-2020/v1",
        ],
        "type": ["VerifiablePresentation"],
        "holder": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
        "verifiableCredential": [
            {
                "@context": [
                    "https://www.w3.org/ns/credentials/v2",
                    "https://w3id.org/security/suites/ed25519-2020/v1",
                ],
                "type": ["VerifiableCredential"],
                "issuer": {
                    "id": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY"
                },
                "credentialSubject": {"id": "did:example:alice", "name": "Alice"},
                "proof": {
                    "type": "Ed25519Signature2020",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
                    "created": "2025-01-21T01:35:19+00:00",
                    "proofValue": "z5H6wcxVZrqyvxRaUFZaV86DYGqQPGuZqxhrL1LcqyQkY5Qk3CMbrnDNgFQkHyhRJgs8KuxcoBntnqNWsXGx17Y8C",
                },
            }
        ],
        "proof": {
            "type": "Ed25519Signature2020",
            "proofPurpose": "assertionMethod",
            "verificationMethod": "did:key:z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY#z6MkeqZtEymBvfpKs4RDdkiCKVpwS5Wqt7vQxd7Sp8pCVUJY",
            "created": "2025-01-21T01:42:55+00:00",
            "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "proofValue": "z5QRjgXP5k86j4jeb9uKvQovZffkd6g9BoAn96sS5gW8Gfbb9RsnV6aBYywTGoLX3HX7ux73UEHYfED5eLSYNSRBL",
        },
    }
}
