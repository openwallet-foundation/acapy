"""Test DID class."""

import pytest
from itertools import cycle
from ..did import DID, DIDUrl, InvalidDIDError, InvalidDIDUrlError

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

TEST_DID_URL0 = TEST_DID0 + "/test/path"
TEST_DID_URL1 = TEST_DID1 + "?key=value"
TEST_DID_URL2 = TEST_DID2 + "#fragment"
TEST_DID_URL3 = TEST_DID3 + "/test/path?key=value"
TEST_DID_URL4 = TEST_DID4 + "/test/path#fragment"
TEST_DID_URL5 = TEST_DID0 + "/test/path?key=value#fragment"
TEST_DID_URL6 = TEST_DID1 + "/test/path?key=value&another=thing#1"
TEST_DID_URLS = [
    TEST_DID_URL0,
    TEST_DID_URL1,
    TEST_DID_URL2,
    TEST_DID_URL3,
    TEST_DID_URL4,
    TEST_DID_URL5,
    TEST_DID_URL6,
]

TEST_DID_URL_PARTS0 = {"did": TEST_DID0, "path": "/test/path"}
TEST_DID_URL_PARTS1 = {"did": TEST_DID1, "query": {"key": "value"}}
TEST_DID_URL_PARTS2 = {"did": TEST_DID2, "fragment": "fragment"}
TEST_DID_URL_PARTS3 = {"did": TEST_DID3, "path": "test/path", "query": {"key": "value"}}
TEST_DID_URL_PARTS4 = {"did": TEST_DID4, "path": "test/path", "fragment": "fragment"}
TEST_DID_URL_PARTS5 = {"did": TEST_DID0, "path": "test/path", "query": {"key": "value"}, "fragment": "fragment"}
TEST_DID_URL_PARTS6 = {"did": TEST_DID1, "path": "/test/path", "query": {"key": "value", "another": "thing"}, "fragment": 1}
TEST_DID_URL_PARTS = [
    TEST_DID_URL_PARTS0,
    TEST_DID_URL_PARTS1,
    TEST_DID_URL_PARTS2,
    TEST_DID_URL_PARTS3,
    TEST_DID_URL_PARTS4,
    TEST_DID_URL_PARTS5,
    TEST_DID_URL_PARTS6,
]

@pytest.mark.parametrize("did", TEST_DIDS)
def test_can_parse_dids(did):
    did = DID(did)
    assert repr(did)


@pytest.mark.parametrize("bad_did", [
    "did:nomethodspecificidentifier",
    "did:invalid-chars-in-method:method-specific-id",
    "bad-prefix:method:method-specific-id",
    *TEST_DID_URLS
])
def test_parse_x(bad_did):
    with pytest.raises(InvalidDIDError):
        DID(bad_did)

@pytest.mark.parametrize("did, parts", zip(cycle(TEST_DIDS), TEST_DID_URL_PARTS))
def test_url_method(did, parts):
    did = DID(did)
    assert did.url(parts.get("path"), parts.get("query"), parts.get("fragment")) == DIDUrl(**parts)


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
    assert did != {"not a": "did"}


@pytest.mark.parametrize(
    "inputs, output",
    zip(TEST_DID_URL_PARTS, TEST_DID_URLS)
)
def test_did_url(inputs, output):
    url = DIDUrl(**inputs)
    assert str(url) == output
    assert repr(url)


@pytest.mark.parametrize(
    "url, parts",
    zip(TEST_DID_URLS, TEST_DID_URL_PARTS)
)
def test_did_url_parse(url, parts):
    assert DIDUrl.parse(url) == DIDUrl(**parts)

@pytest.mark.parametrize("lhs, rhs", zip(TEST_DID_URLS, TEST_DID_URLS[1:]))
def test_did_url_neq(lhs, rhs):
    lhs = DIDUrl.parse(lhs)
    assert lhs != rhs
    rhs = DIDUrl.parse(rhs)
    assert lhs != rhs
    assert lhs != {"not a": "DIDUrl"}

@pytest.mark.parametrize(
    "bad_url",
    [
        TEST_DID0,
        "not://a/did?url=value",
    ]
)
def test_did_url_parse_x(bad_url):
    with pytest.raises(InvalidDIDUrlError):
        DIDUrl.parse(bad_url)
