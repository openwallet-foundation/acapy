"""Test json-ld credential."""

import pytest
import asyncio
from asynctest import mock as async_mock
from itertools import cycle
from ....admin.request_context import AdminRequestContext
from ..credential import verify_credential, sign_credential, did_key, InvalidJWSHeader
from ....core.in_memory import InMemoryProfile
from ....wallet.in_memory import InMemoryWallet
from ....wallet.base import BaseWallet

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
TEST_SIGN_OBJS = [
    TEST_SIGN_OBJ0,
    TEST_SIGN_OBJ1,
    TEST_SIGN_OBJ2,
]

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
                "eyJhbGciOiJ0RWRUZXN0RWQiLCJiNjQiOmZhbHNlLCJjcml0IjpbImI2NCJdfQ..l9d0YHjcFAH2H4dB9xlWFZQLUp"
                "ixVCWJk0eOt4CXQe1NXKWZwmhmn9OQp6YxX0a2Lffe"
                "gtYESTCJEoGVXLqWAA"
            ),
        },
    },
}


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def wallet():
    profile = InMemoryProfile.test_profile()
    wallet = InMemoryWallet(profile)
    await wallet.create_signing_key(TEST_SEED)
    yield wallet


@pytest.fixture(scope="module")
async def mock_session(wallet):
    session_inject = {BaseWallet: wallet}
    context = AdminRequestContext.test_context(session_inject)
    session = await context.session()
    yield session


@pytest.mark.parametrize("input", TEST_VERIFY_OBJS)
@pytest.mark.asyncio
async def test_verify_credential(input, mock_session):
    result = await verify_credential(
        mock_session, input.get("doc"), input.get("verkey")
    )
    assert result


@pytest.mark.parametrize("input", TEST_SIGN_OBJS)
@pytest.mark.asyncio
async def test_sign_credential(input, mock_session):
    result = await sign_credential(
        mock_session, input.get("doc"), input.get("options"), TEST_VERKEY
    )
    assert "proof" in result.keys()
    assert "jws" in result.get("proof", {}).keys()


@pytest.mark.asyncio
async def test_Invalid_JWS_header(mock_session):
    with pytest.raises(InvalidJWSHeader):
        await verify_credential(
            mock_session, TEST_VERIFY_ERROR.get("doc"), TEST_VERIFY_ERROR.get("verkey")
        )


@pytest.mark.parametrize(
    "verkey",
    (
        "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
        "did:key:z3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
    ),
)
def test_did_key(verkey):
    assert did_key(verkey).startswith("did:key:z")
