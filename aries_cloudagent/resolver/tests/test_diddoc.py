"""Test resolved DID Doc."""

import pytest

from ..diddoc import ExternalResourceError, ResolvedDIDDoc, _index_ids_of_doc

DOC = {
    "@context": "https://w3id.org/did/v1",
    "id": "did:example:1234abcd",
    "verificationMethod": [
        {
            "id": "3",
            "type": "RsaVerificationKey2018",
            "controller": "did:example:1234abcd",
            "publicKeyPem": "-----BEGIN PUBLIC X…",
        },
        {
            "id": "4",
            "type": "RsaVerificationKey2018",
            "controller": "did:example:1234abcd",
            "publicKeyPem": "-----BEGIN PUBLIC 9…",
        },
        {
            "id": "6",
            "type": "RsaVerificationKey2018",
            "controller": "did:example:1234abcd",
            "publicKeyPem": "-----BEGIN PUBLIC A…",
        },
    ],
    "authentication": [
        {
            "type": "RsaSignatureAuthentication2018",
            "publicKey": "did:example:1234abcd#4",
        }
    ],
    "service": [
        {
            "id": "did:example:123456789abcdefghi;did-communication",
            "type": "did-communication",
            "priority": 0,
            "recipientKeys": ["did:example:1234abcd#4"],
            "routingKeys": ["did:example:1234abcd#3"],
            "serviceEndpoint": "did:example:xd45fr567794lrzti67;did-communication",
        }
    ],
}


def test_index():
    index = _index_ids_of_doc(DOC)
    assert len(index) == 5
    assert "did:example:1234abcd" in index
    assert "3" in index
    assert "4" in index
    assert "6" in index
    assert "did:example:123456789abcdefghi;did-communication" in index


def test_dereference():
    doc = ResolvedDIDDoc(DOC)
    assert doc.dereference("did:example:1234abcd#4") == DOC["verificationMethod"][1]


def test_dereference_x():
    doc = ResolvedDIDDoc(DOC)
    with pytest.raises(ExternalResourceError):
        doc.dereference("did:example:different#4")


def test_basic():
    doc = ResolvedDIDDoc(DOC)
    service, *_ = doc.didcomm_services()
    for key_ref in service["recipientKeys"]:
        doc.dereference(key_ref)
