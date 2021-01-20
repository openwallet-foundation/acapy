"""Test DID class."""

import pytest
from ..did import DID

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


def test_did_url():
    did = DID(TEST_DID0)
    assert did.url(path="test") == TEST_DID0 + "/test"
    assert did.url(path="/test") == TEST_DID0 + "/test"
    assert did.url(query={"key": "value"}) == TEST_DID0 + "?key=value"
    assert (
        did.url(query={"key": "value", "another": "value"})
        == TEST_DID0 + "?key=value&another=value"
    )
    assert did.url(fragment="fragment") == TEST_DID0 + "#fragment"
    assert (
        did.url("test", {"key": "value"}, "fragment")
        == TEST_DID0 + "/test?key=value#fragment"
    )
