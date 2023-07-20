"""
DID Document classes.

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
import logging

from typing import List, Sequence, Union, Any, Optional
from pydid import DIDCommService
from peerdid import dids, keys
from peerdid.dids import DID, DIDDocument, create_peer_did_numalgo_0, resolve_peer_did
from .publickey import PublicKey, PublicKeyType
from .service import Service
from .util import canon_did, canon_ref, ok_did, resource

LOGGER = logging.getLogger(__name__)


class UnqualifiedDIDDoc(DIDDocument):
    """
    DID document, grouping a DID with verification keys and services.

    Retains DIDs as raw values (orientated toward indy-facing operations),
    everything else as URIs (oriented toward W3C-facing operations).
    """


    # ACAPY USED UNQUALIFIED DIDS, allow them in DIDDoc's for now....
    id: Union[DID, str] = ""
    controller: Optional[List[Union[DID, str]]] = None


class LegacyDIDDoc(UnqualifiedDIDDoc):
    
    _pubkey: dict = {}
    _service: dict = {}

    
    @property
    def did(self) -> str:
        """Accessor for DID."""
        return self.id

    @did.setter
    def did(self, value: str) -> None:
        """
        Set DID ('id' in DIDDoc context).

        Args:
            value: DID

        Raises:
            ValueError: for bad input DID.

        """

        self.id = canon_did(value) if value else None

    @property
    def pubkey(self) -> dict:
        """Accessor for public keys by identifier."""

        return self._pubkey

    @property
    def authnkey(self) -> dict:
        """Accessor for public keys marked as authentication keys, by identifier."""

        return {k: self._pubkey[k] for k in self._pubkey if self._pubkey[k].authn}

    @property
    def service(self) -> dict:
        """Accessor for services by identifier."""

        return self._service

    def set(self, item: Union[Service, PublicKey]) -> "DIDDoc":
        """
        Add or replace service or public key; return current DIDDoc.

        Raises:
            ValueError: if input item is neither service nor public key.

        Args:
            item: service or public key to set

        Returns: the current DIDDoc

        """
        if isinstance(item, Service):
            self._service[item.id] = item
        elif isinstance(item, PublicKey):
            self._pubkey[item.id] = item
        else:
            raise ValueError(
                "Cannot add item {} to DIDDoc on DID {}".format(item, self.did)
            )

    def serialize(self) -> dict:
        """
        Dump current object to a JSON-compatible dictionary.

        Returns:
            dict representation of current DIDDoc

        """

        return {
            "@context": self.context,
            "id": canon_ref(self.did, self.did),
            "publicKey": [pubkey.to_dict() for pubkey in self._pubkey.values()],
            "authentication": [
                {
                    "type": pubkey.type.authn_type,
                    "publicKey": canon_ref(self.did, pubkey.id),
                }
                for pubkey in self.pubkey.values()
                if pubkey.authn
            ],
            "service": [service.to_dict() for service in self._service.values()],
        }

    def to_json(self) -> str:
        """
        Dump current object as json (JSON-LD).

        Returns:
            json representation of current DIDDoc

        """

        return json.dumps(self.serialize())

    def add_service_pubkeys(
        self, service: dict, tags: Union[Sequence[str], str]
    ) -> List[PublicKey]:
        """
        Add public keys specified in service. Return public keys so discovered.

        Args:
            service: service from DID document
            tags: potential tags marking public keys of type of interest
                (the standard is still coalescing)

        Raises:
            ValueError: for public key reference not present in DID document.

        Returns: list of public keys from the document service specification

        """

        rv = []
        for tag in [tags] if isinstance(tags, str) else list(tags):
            for svc_key in service.get(tag, {}):
                canon_key = canon_ref(self.did, svc_key)
                pubkey = None

                if "#" in svc_key:
                    if canon_key in self.pubkey:
                        pubkey = self.pubkey[canon_key]
                    else:  # service key refers to another DID doc
                        LOGGER.debug(
                            "DID document %s has no public key %s", self.did, svc_key
                        )
                        raise ValueError(
                            "DID document {} has no public key {}".format(
                                self.did, svc_key
                            )
                        )
                else:
                    for existing_pubkey in self.pubkey.values():
                        if existing_pubkey.value == svc_key:
                            pubkey = existing_pubkey
                            break
                    else:
                        pubkey = PublicKey(
                            self.did,
                            ident=svc_key[-9:-1],  # industrial-grade uniqueness
                            value=svc_key,
                        )
                        self._pubkey[pubkey.id] = pubkey

                if (
                    pubkey and pubkey not in rv
                ):  # perverse case: could specify same key multiple ways; append once
                    rv.append(pubkey)

        return rv

    @classmethod
    def deserialize(cls, did_doc: dict) -> "LegacyDIDDoc":
        """
        Construct DIDDoc object from dict representation.

        Args:
            did_doc: DIDDoc dict representation

        Raises:
            ValueError: for bad DID or missing mandatory item.

        Returns: DIDDoc from input json

        """

        rv = None
        if "id" in did_doc:
            print("LegacyDIDDoc:deserialize")
            print(did_doc["id"])
            rv = LegacyDIDDoc(id=did_doc["id"])
        else:
            # heuristic: get DID to serve as DID document identifier from
            # the first OK-looking public key
            for section in ("publicKey", "authentication"):
                if rv is None and section in did_doc:
                    for key_spec in did_doc[section]:
                        try:
                            pubkey_did = canon_did(resource(key_spec.get("id", "")))
                            if ok_did(pubkey_did):
                                rv = LegacyDIDDoc(pubkey_did)
                                break
                        except ValueError:  # no identifier here, move on to next
                            break
            if rv is None:
                LOGGER.debug("no identifier in DID document")
                raise ValueError("No identifier in DID document")

        for pubkey in did_doc.get(
            "publicKey", {}
        ):  # include all public keys, authentication pubkeys by reference
            pubkey_type = PublicKeyType.get(pubkey["type"])
            authn = any(
                canon_ref(rv.id, ak.get("publicKey", ""))
                == canon_ref(rv.id, pubkey["id"])
                for ak in did_doc.get("authentication", {})
                if isinstance(ak.get("publicKey", None), str)
            )
            key = PublicKey(  # initialization canonicalizes id
                rv.id,
                pubkey["id"],
                pubkey[pubkey_type.specifier],
                pubkey_type,
                canon_did(pubkey["controller"]),
                authn,
            )
            rv._pubkey[key.id] = key

        for akey in did_doc.get(
            "authentication", {}
        ):  # include embedded authentication keys
            if "publicKey" not in akey:  # not yet got it with public keys
                pubkey_type = PublicKeyType.get(akey["type"])
                key = PublicKey(  # initialization canonicalized id
                    rv.id,
                    akey["id"],
                    akey[pubkey_type.specifier],
                    pubkey_type,
                    canon_did(akey["controller"]),
                    True,
                )
                rv._pubkey[key.id] = key

        for service in did_doc.get("service", {}):
            endpoint = service["serviceEndpoint"]
            svc = Service(  # initialization canonicalizes id
                rv.id,
                service.get(
                    "id",
                    canon_ref(
                        rv.id, "assigned-service-{}".format(len(rv._service)), ";"
                    ),
                ),
                service["type"],
                rv.add_service_pubkeys(service, "recipientKeys"),
                rv.add_service_pubkeys(service, ["mediatorKeys", "routingKeys"]),
                canon_ref(rv.id, endpoint, ";") if ";" in endpoint else endpoint,
                service.get("priority", None),
            )
            rv._service[svc.id] = svc

        return rv

    @classmethod
    def from_json(cls, did_doc_json: str) -> "LegacyDIDDoc":
        """
        Construct DIDDoc object from json representation.

        Args:
            did_doc_json: DIDDoc json representation

        Returns: DIDDoc from input json

        """

        return cls.deserialize(json.loads(did_doc_json))

    def __str__(self) -> str:
        """Return string representation for abbreviated display."""

        return f"DIDDoc({self.did})"

    def __repr__(self) -> str:
        """Format DIDDoc for logging."""

        return f"<DIDDoc did={self.did}>"


class PeerDIDDoc(DIDDocument):
    """
    did:peer:2 following the Method 2 of
    https://identity.foundation/peer-did-method-spec/#generation-method
    """

    @classmethod
    def create_peer_did_2_from_verkey(
        cls, verkey: str, service: dict = None
    ) -> dids.DID:
        """verkey must by base58"""

        enc_keys = [keys.X25519KeyAgreementKey.from_base58(verkey)]
        sign_keys = [keys.Ed25519VerificationKey.from_base58(verkey)]

        var = dids.create_peer_did_numalgo_2(
            enc_keys, sign_keys, service
        )
        return var

    @classmethod
    def resolve_peer_did(self, did:DID) -> DIDDocument:
        return resolve_peer_did(did)