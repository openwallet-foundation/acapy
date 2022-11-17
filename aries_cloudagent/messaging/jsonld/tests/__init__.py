TEST_SEED = "testseed000000000000000000000001"
TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"

TEST_SIGN_OBJ0 = {
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "id": "http://example.gov/credentials/3732",
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": ("did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"),
        "issuanceDate": "2020-03-10T04:24:12.164Z",
        "credentialSubject": {
            "id": ("did:key:" "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"),
            "degree": {
                "type": "BachelorDegree",
                "name": "Bachelor of Science and Arts",
            },
        },
    },
    "options": {
        "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
        "proofPurpose": "assertionMethod",
        "created": "2020-04-02T18:48:36Z",
        "domain": "example.com",
        "challenge": "d436f0c8-fbd9-4e48-bbb2-55fc5d0920a8",
    },
}
TEST_SIGN_OBJ1 = {
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "id": "http://example.gov/credentials/3735",
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": "did:example:123",
        "issuanceDate": "2020-03-16T22:37:26.544Z",
        "credentialSubject": {
            "id": "did:example:123",
            "degree": {
                "type": "BachelorDegree",
                "name": "Bachelor of Science and Arts",
            },
        },
    },
    "options": {
        "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
        "proofPurpose": "assertionMethod",
        "created": "2020-04-02T18:48:36Z",
        "domain": "example.com",
        "challenge": "d436f0c8-fbd9-4e48-bbb2-55fc5d0920a8",
    },
}
TEST_SIGN_OBJ2 = {
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "holder": "did:example:123",
        "type": "VerifiablePresentation",
        "verifiableCredential": [
            {
                "@context": [
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ]
            },
            {"id": "http://example.gov/credentials/3732"},
            {"type": ["VerifiableCredential", "UniversityDegreeCredential"]},
            {"issuer": "did:example:123"},
            {"issuanceDate": "2020-03-16T22:37:26.544Z"},
            {
                "credentialSubject": {
                    "id": "did:example:123",
                    "degree": {
                        "type": "BachelorDegree",
                        "name": "Bachelor of Science and Arts",
                    },
                }
            },
            {
                "proof": {
                    "type": "Ed25519Signature2018",
                    "created": "2020-04-02T18:28:08Z",
                    "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
                    "proofPurpose": "assertionMethod",
                    "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..YtqjEYnFENT7fNW-COD0HAACxeuQxPKAmp4nIl8jYAu__6IH2FpSxv81w-l5PvE1og50tS9tH8WyXMlXyo45CA",
                }
            },
        ],
        "proof": {
            "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
            "proofPurpose": "assertionMethod",
            "created": "2020-04-02T18:48:36Z",
            "domain": "example.com",
            "challenge": "d436f0c8-fbd9-4e48-bbb2-55fc5d0920a8",
            "type": "Ed25519Signature2018",
            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..a6dB9OAI9HWc1lDoWzd1---XF_QdArVMu99N2OKnOFT2Ize8MiuVvbJCIkYHpjn3arPle-o0iMlUx3q08ES_Bg",
        },
    },
    "options": {
        "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
        "proofPurpose": "assertionMethod",
        "created": "2020-04-02T18:48:36Z",
        "domain": "example.com",
        "challenge": "d436f0c8-fbd9-4e48-bbb2-55fc5d0920a8",
    },
}

TEST_SIGN_OBJS = [TEST_SIGN_OBJ0, TEST_SIGN_OBJ1, TEST_SIGN_OBJ2]  # , TEST_SIGN_OBJ3]

TEST_SIGN_ERROR_OBJ0 = {
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://essif-lab.pages.grnet.gr/interoperability/eidas-generic-use-case/contexts/ehic-v1.jsonld",
        ],
        "id": "https://ec.europa.eu/credentials/83627465",
        "type": ["VerifiableCredential", "EuropeanHealthInsuranceCard"],
        "issuer": "did:example:28394728934792387",
        "name": "European Health Insurance Card",
        "description": "Example of a European Health Insurance Card",
        "attribute2drop": "drop it like it's hot",
        "issuanceDate": "2021-01-01T12:19:52Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "institutionID": "09999 - GE KVG",
        "cardNo": "80756099990000034111",
        "personalID": "09999 111999",
        "credentialSubject": {
            "id": "did:example:b34ca6cd37bbf23",
            "type": ["EuropeanHealthInsuranceHolder", "Person"],
            "familyName": "Muster",
            "giveName": "Maria",
            "birthDate": "1958-07-17",
        },
    },
    "options": {
        "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
        "proofPurpose": "assertionMethod",
        "created": "2020-04-02T18:48:36Z",
        "domain": "example.com",
        "challenge": "d436f0c8-fbd9-4e48-bbb2-55fc5d0920a8",
    },
}
TEST_SIGN_ERROR_OBJ1 = {
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://essif-lab.pages.grnet.gr/interoperability/eidas-generic-use-case/contexts/ehic-v1.jsonld",
        ],
        "id": "https://ec.europa.eu/credentials/83627465",
        "type": ["VerifiableCredential", "EuropeanHealthInsuranceCard"],
        "issuer": "did:example:28394728934792387",
        "name": "European Health Insurance Card",
        "description": "Example of a European Health Insurance Card",
        "issuanceDate": "2021-01-01T12:19:52Z",
        "expirationDate": "2029-12-03T12:19:52Z",
        "institutionID": "09999 - GE KVG",
        "cardNo": "80756099990000034111",
        "personalID": "09999 111999",
        "credentialSubject": {
            "id": "did:example:b34ca6cd37bbf23",
            "type": ["EuropeanHealthInsuranceHolder", "Person"],
            "attribute2drop": "drop it like it's hot",
            "familyName": "Muster",
            "giveName": "Maria",
            "birthDate": "1958-07-17",
        },
    },
    "options": {
        "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
        "proofPurpose": "assertionMethod",
        "created": "2020-04-02T18:48:36Z",
        "domain": "example.com",
        "challenge": "d436f0c8-fbd9-4e48-bbb2-55fc5d0920a8",
    },
}
TEST_VALIDATE_ERROR_OBJ2 = {
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "holder": "did:example:123",
        "type": "VerifiablePresentation",
        "verifiableCredential": [
            {
                "@context": [
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ]
            },
            {"id": "http://example.gov/credentials/3732"},
            {"type": ["VerifiableCredential", "UniversityDegreeCredential"]},
            {"issuer": "did:example:123"},
            {"issuanceDate": "2020-03-16T22:37:26.544Z"},
            {
                "credentialSubject": {
                    "id": "did:example:123",
                    "degree": {
                        "type": "BachelorDegree",
                        "name": "Bachelor of Science and Arts",
                    },
                }
            },
            {
                "proof": {
                    "type": "Ed25519Signature2018",
                    "created": "2020-04-02T18:28:08Z",
                    "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
                    "proofPurpose": "assertionMethod",
                    "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..YtqjEYnFENT7fNW-COD0HAACxeuQxPKAmp4nIl8jYAu__6IH2FpSxv81w-l5PvE1og50tS9tH8WyXMlXyo45CA",
                }
            },
        ],
        "proof": {
            "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
            "attribute2drop": "drop it like it's hot",
            "proofPurpose": "assertionMethod",
            "created": "2020-04-02T18:48:36Z",
            "domain": "example.com",
            "challenge": "d436f0c8-fbd9-4e48-bbb2-55fc5d0920a8",
            "type": "Ed25519Signature2018",
            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..a6dB9OAI9HWc1lDoWzd1---XF_QdArVMu99N2OKnOFT2Ize8MiuVvbJCIkYHpjn3arPle-o0iMlUx3q08ES_Bg",
        },
    },
    "verkey": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
}
TEST_SIGN_ERROR_OBJS = [TEST_SIGN_ERROR_OBJ0, TEST_SIGN_ERROR_OBJ1]

TEST_VERIFY_OBJ0 = {
    "verkey": ("5yKdnU7ToTjAoRNDzfuzVTfWBH38qyhE1b9xh4v8JaWF"),
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "id": "http://example.gov/credentials/3732",
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": ("did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"),
        "issuanceDate": "2020-03-10T04:24:12.164Z",
        "credentialSubject": {
            "id": ("did:key:" "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"),
            "degree": {
                "type": "BachelorDegree",
                "name": "Bachelor of Science and Arts",
            },
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "created": "2020-04-10T21:35:35Z",
            "verificationMethod": (
                "did:key:"
                "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc"
                "4tXLt9DoHd#z6MkjRagNiMu91DduvCvgEsqLZD"
                "VzrJzFrwahc4tXLt9DoHd"
            ),
            "proofPurpose": "assertionMethod",
            "jws": (
                "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaX"
                "QiOlsiYjY0Il19..l9d0YHjcFAH2H4dB9xlWFZQLUp"
                "ixVCWJk0eOt4CXQe1NXKWZwmhmn9OQp6YxX0a2Lffe"
                "gtYESTCJEoGVXLqWAA"
            ),
        },
    },
}
TEST_VERIFY_OBJ1 = {
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "id": "http://example.gov/credentials/3732",
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": "did:example:123",
        "issuanceDate": "2020-03-16T22:37:26.544Z",
        "credentialSubject": {
            "id": "did:example:123",
            "degree": {
                "type": "BachelorDegree",
                "name": "Bachelor of Science and Arts",
            },
        },
        "proof": {
            "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
            "proofPurpose": "assertionMethod",
            "created": "2020-04-02T18:48:36Z",
            "domain": "example.com",
            "challenge": "d436f0c8-fbd9-4e48-bbb2-55fc5d0920a8",
            "type": "Ed25519Signature2018",
            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..MthZGAH62bEu2e4rZSE6b0XvGr_5z6J3FSXuVJnOOxr6sgdJpUenXJ-113MTtjArwC2JXh0zeolhXithxud_Dw",
        },
    },
    "verkey": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
}
TEST_VERIFY_OBJ2 = {
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "holder": "did:example:123",
        "type": "VerifiablePresentation",
        "verifiableCredential": [
            {
                "@context": [
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/credentials/examples/v1",
                ]
            },
            {"id": "http://example.gov/credentials/3732"},
            {"type": ["VerifiableCredential", "UniversityDegreeCredential"]},
            {"issuer": "did:example:123"},
            {"issuanceDate": "2020-03-16T22:37:26.544Z"},
            {
                "credentialSubject": {
                    "id": "did:example:123",
                    "degree": {
                        "type": "BachelorDegree",
                        "name": "Bachelor of Science and Arts",
                    },
                }
            },
            {
                "proof": {
                    "type": "Ed25519Signature2018",
                    "created": "2020-04-02T18:28:08Z",
                    "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
                    "proofPurpose": "assertionMethod",
                    "jws": "eyJhbGciOiJFZERTQSIsImI2NCI6ZmFsc2UsImNyaXQiOlsiYjY0Il19..YtqjEYnFENT7fNW-COD0HAACxeuQxPKAmp4nIl8jYAu__6IH2FpSxv81w-l5PvE1og50tS9tH8WyXMlXyo45CA",
                }
            },
        ],
        "proof": {
            "verificationMethod": "did:example:123#z6MksHh7qHWvybLg5QTPPdG2DgEjjduBDArV9EF9mRiRzMBN",
            "proofPurpose": "assertionMethod",
            "created": "2020-04-02T18:48:36Z",
            "domain": "example.com",
            "challenge": "d436f0c8-fbd9-4e48-bbb2-55fc5d0920a8",
            "type": "Ed25519Signature2018",
            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..a6dB9OAI9HWc1lDoWzd1---XF_QdArVMu99N2OKnOFT2Ize8MiuVvbJCIkYHpjn3arPle-o0iMlUx3q08ES_Bg",
        },
    },
    "verkey": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
}
TEST_VERIFY_OBJS = [
    TEST_VERIFY_OBJ0,
    TEST_VERIFY_OBJ1,
    TEST_VERIFY_OBJ2,
]
TEST_VERIFY_ERROR = {
    "verkey": "5yKdnU7ToTjAoRNDzfuzVTfWBH38qyhE1b9xh4v8JaWF",
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "id": "http://example.gov/credentials/3732",
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "issuer": ("did:key:z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"),
        "issuanceDate": "2020-03-10T04:24:12.164Z",
        "credentialSubject": {
            "id": ("did:key:" "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc4tXLt9DoHd"),
            "degree": {
                "type": "BachelorDegree",
                "name": "Bachelor of Science and Arts",
            },
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "created": "2020-04-10T21:35:35Z",
            "verificationMethod": (
                "did:key:"
                "z6MkjRagNiMu91DduvCvgEsqLZDVzrJzFrwahc"
                "4tXLt9DoHd#z6MkjRagNiMu91DduvCvgEsqLZD"
                "VzrJzFrwahc4tXLt9DoHd"
            ),
            "proofPurpose": "assertionMethod",
            "jws": (
                "eyJhbGciOiJ0RWRUZXN0RWQiLCJiNjQiOmZhbHNlLCJjcml0IjpbImI2NCJdfQ..l9d0YHjcFAH2H4dB9xlWFZQLUp"
                "ixVCWJk0eOt4CXQe1NXKWZwmhmn9OQp6YxX0a2Lffe"
                "gtYESTCJEoGVXLqWAA"
            ),
        },
    },
}
TEST_EURO_HEALTH = {
    "@context": {
        "@version": 1.1,
        "@protected": True,
        "name": "http://schema.org/name",
        "description": "http://schema.org/description",
        "EuropeanHealthInsuranceCard": {
            "@id": "https://essif-lab.pages.grnet.gr/interoperability/eidas-generic-use-case#EuropeanHealthInsuranceCard",
            "@context": {
                "@version": 1.1,
                "@protected": True,
                "id": "@id",
                "type": "@type",
                "ehic": "https://essif-lab.pages.grnet.gr/interoperability/eidas-generic-use-case#",
                "description": "http://schema.org/description",
                "name": "http://schema.org/name",
                "institutionID": "ehic:identificationNumberOfTheInstitution",
                "cardNo": "ehic:identificationNumberOfTheCard",
                "personalID": "ehic:personalIdentificationNumber",
            },
        },
        "EuropeanHealthInsuranceHolder": {
            "@id": "https://essif-lab.pages.grnet.gr/interoperability/eidas-generic-use-case#EuropeanHealthInsuranceHolder",
            "@context": {
                "@version": 1.1,
                "@protected": True,
                "schema": "http://schema.org/",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "id": "@id",
                "type": "@type",
                "birthDate": {"@id": "schema:birthDate", "@type": "xsd:dateTime"},
                "familyName": "schema:familyName",
                "givenName": "schema:givenName",
            },
        },
        "Person": "http://schema.org/Person",
    }
}
