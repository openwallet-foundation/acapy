"""
DIDDoc utility methods.

Copyright 2017-2019 Government of Canada
Public Services and Procurement Canada - buyandsell.gc.ca

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json

from typing import Tuple
from base58 import b58decode
from urllib.parse import urlparse
from pydid.did import DID_PATTERN
from peerdid.dids import DID, DIDDocument, create_peer_did_numalgo_2, resolve_peer_did
from peerdid.keys import X25519KeyAgreementKey, Ed25519VerificationKey


def resource(ref: str, delimiter: str = None) -> str:
    """
    Extract the resource for an identifier.

    Given a (URI) reference, return up to its delimiter (exclusively), or all of it if
    there is none.

    Args:
        ref: reference
        delimiter: delimiter character
            (default None maps to '#', or ';' introduces identifiers)
    """

    return ref.split(delimiter if delimiter else "#")[0]


def canon_did(uri: str) -> str:
    """
    Convert a URI into a DID if need be, left-stripping 'did:sov:' if present.

    Args:
        uri: input URI or DID

    Raises:
        ValueError: for invalid input.

    """

    if ok_did(uri):
        return uri

    if uri.startswith("did:sov:"):
        rv = uri[8:]
        if ok_did(rv):
            return rv
    raise ValueError(
        "Bad specification {} does not correspond to a sovrin DID".format(uri)
    )


def canon_ref(did: str, ref: str, delimiter: str = None):
    """
    Given a reference in a DID document, return it in its canonical form of a URI.

    Args:
        did: DID acting as the identifier of the DID document
        ref: reference to canonicalize, either a DID or a fragment pointing to a
            location in the DID doc
        delimiter: delimiter character marking fragment (default '#') or
            introducing identifier (';') against DID resource
    """
    # if it's already a valid did, allow it
    if DID_PATTERN.match(did):
        return DID(did)

    # if not, handle unqualified dids with legacy code
    if not ok_did(did):
        raise ValueError("Bad DID {} cannot act as DID document identifier".format(did))

    if ok_did(ref):  # e.g., LjgpST2rjsoxYegQDRm7EL
        return "did:sov:{}".format(did)

    if ok_did(resource(ref, delimiter)):  # e.g., LjgpST2rjsoxYegQDRm7EL#keys-1
        return "did:sov:{}".format(ref)

    if ref.startswith(
        "did:sov:"
    ):  # e.g., did:sov:LjgpST2rjsoxYegQDRm7EL, did:sov:LjgpST2rjsoxYegQDRm7EL#3
        rv = ref[8:]
        if ok_did(resource(rv, delimiter)):
            return ref
        raise ValueError("Bad URI {} does not correspond to a sovrin DID".format(ref))

    if urlparse(ref).scheme:  # e.g., https://example.com/messages/8377464
        return ref

    return "did:sov:{}{}{}".format(did, delimiter if delimiter else "#", ref)  # e.g., 3


def ok_did(token: str) -> bool:
    """
    Whether input token looks like a valid decentralized identifier.

    Args:
        token: candidate string

    Returns: whether input token looks like a valid schema identifier

    """
    try:
        return len(b58decode(token)) == 16 if token else False
    except ValueError:
        return False


def create_peer_did_2(verkey: str, service: dict = None) -> Tuple[DID, DIDDocument]:
    """verkey must by base58"""

    enc_keys = [X25519KeyAgreementKey.from_base58(verkey)]
    sign_keys = [Ed25519VerificationKey.from_base58(verkey)]

    did = create_peer_did_numalgo_2(enc_keys, sign_keys, service)
    doc = resolve_peer_did(did)
    return did, doc



def upgrade_legacy_did_doc_to_peer_did(json_str:str) -> Tuple[DID, DIDDocument]:
    doc_dict = json.loads(json_str)

    public_key_b58 = doc_dict["publicKey"][0]["publicKeyBase58"]
    service = doc_dict["service"][0]

    if service["type"] == "IndyAgent":
        service["type"] =  "DIDCommMessaging"
    if "id" in service["id"]:
        del service["id"]
        
    return create_peer_did_2(public_key_b58,service)