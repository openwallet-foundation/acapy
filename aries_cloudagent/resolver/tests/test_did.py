"""Test DID class."""

import pytest
from ..did import DID, DIDUrl

TEST_DID0 = "did:sov:Kkyqu7CJFuQSvBp468uaDe"
TEST_DID1 = "did:btcr:8kyt-fzzq-qpqq-ljsc-5l"
TEST_DID2 = "did:ethr:mainnet:0xb9c5714089478a327f09197987f16f9e5d936e8a"
TEST_DID3 = "did:ion:EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A"
TEST_DID4 = "did:github:ghdid"

TEST_DIDS = [
    TEST_DID0,
    TEST_DID1,
    TEST_DID2,
    TEST_DID3,
    TEST_DID4,
]

TEST_DID_METHOD0 = "sov"
TEST_DID_METHOD1 = "btcr"
TEST_DID_METHOD2 = "ethr"
TEST_DID_METHOD3 = "ion"
TEST_DID_METHOD4 = "github"

TEST_DID_METHODS = [
    TEST_DID_METHOD0,
    TEST_DID_METHOD1,
    TEST_DID_METHOD2,
    TEST_DID_METHOD3,
    TEST_DID_METHOD4,
]

TEST_METHOD_SPECIFIC_ID0 = "Kkyqu7CJFuQSvBp468uaDe"
TEST_METHOD_SPECIFIC_ID1 = "8kyt-fzzq-qpqq-ljsc-5l"
TEST_METHOD_SPECIFIC_ID2 = "mainnet:0xb9c5714089478a327f09197987f16f9e5d936e8a"
TEST_METHOD_SPECIFIC_ID3 = "EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A"
TEST_METHOD_SPECIFIC_ID4 = "ghdid"

TEST_METHOD_SPECIFIC_IDS = [
    TEST_METHOD_SPECIFIC_ID0,
    TEST_METHOD_SPECIFIC_ID1,
    TEST_METHOD_SPECIFIC_ID2,
    TEST_METHOD_SPECIFIC_ID3,
    TEST_METHOD_SPECIFIC_ID4,
]


@pytest.mark.parametrize("did", TEST_DIDS)
def test_can_parse_dids(did):
    DID(did)


@pytest.mark.parametrize("did, method", zip(TEST_DIDS, TEST_DID_METHODS))
def test_method(did, method):
    assert DID(did).method == method


@pytest.mark.parametrize(
    "did, method_specific_id", zip(TEST_DIDS, TEST_METHOD_SPECIFIC_IDS)
)
def test_method_specific_id(did, method_specific_id):
    assert DID(did).method_specific_id == method_specific_id


@pytest.mark.parametrize("did", TEST_DIDS)
def test_str(did):
    assert str(DID(did)) == did


@pytest.mark.parametrize("did, next_did", zip(TEST_DIDS, TEST_DIDS[1:]))
def test_eq(did, next_did):
    same = DID(did)
    did = DID(did)
    next_did = DID(next_did)
    assert did == same
    assert did != next_did


@pytest.mark.parametrize(
    "inputs, output",
    [
        ({"did": TEST_DID0, "path": "test"}, TEST_DID0 + "/test"),
        ({"did": TEST_DID1, "path": "/test"}, TEST_DID1 + "/test"),
        ({"did": TEST_DID2, "query": {"key": "value"}}, TEST_DID2 + "?key=value"),
        (
            {"did": TEST_DID3, "query": {"key": "value", "another": "value"}},
            TEST_DID3 + "?key=value&another=value",
        ),
        ({"did": TEST_DID4, "fragment": "test"}, TEST_DID4 + "#test"),
        (
            {
                "did": TEST_DID0,
                "path": "test/path",
                "query": {"key": "value", "another": "value"},
                "fragment": "fragment",
            },
            TEST_DID0 + "/test/path?key=value&another=value#fragment",
        ),
    ],
)
def test_did_url(inputs, output):
    assert str(DIDUrl(**inputs)) == output


@pytest.mark.parametrize(
    "url, parts",
    [
        (TEST_DID0 + "/test/path", {"did": TEST_DID0, "path": "/test/path"}),
        (TEST_DID1 + "?key=value", {"did": TEST_DID1, "query": {"key": "value"}}),
        (TEST_DID2 + "#fragment", {"did": TEST_DID2, "fragment": "fragment"}),
        (
            TEST_DID3 + "/test/path?key=value#fragment",
            {
                "did": TEST_DID3,
                "path": "/test/path",
                "query": {"key": "value"},
                "fragment": "fragment",
            },
        ),
    ],
)
def test_did_url_parse(url, parts):
    assert DIDUrl.parse(url) == DIDUrl(**parts)
