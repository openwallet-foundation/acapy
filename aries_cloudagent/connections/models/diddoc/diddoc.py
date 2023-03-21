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

from typing import List, Sequence, Union
from uuid import uuid4

from .publickey import PublicKey, PublicKeyType
from .service import Service
from .util import canon_did, canon_ref, ok_did, resource

from ....did.did_key import DIDKey

LOGGER = logging.getLogger(__name__)


class DIDDoc:
    """
    DID document, grouping a DID with verification keys and services.

    Retains DIDs as raw values (orientated toward indy-facing operations),
    everything else as URIs (oriented toward W3C-facing operations).
    """

    CONTEXT = "https://w3id.org/did/v1"

    def __init__(self, did: str = None) -> None:
        """
        Initialize the DIDDoc instance.

        Retain DID ('id' in DIDDoc context); initialize verification keys
        and services to empty lists.

        Args:
            did: DID for current DIDdoc

        Raises:
            ValueError: for bad input DID.

        """

        self._did = canon_did(did) if did else None  # allow specification post-hoc
        self._pubkey = {}
        self._service = {}

    @property
    def did(self) -> str:
        """Accessor for DID."""

        return self._did

    @did.setter
    def did(self, value: str) -> None:
        """
        Set DID ('id' in DIDDoc context).

        Args:
            value: DID

        Raises:
            ValueError: for bad input DID.

        """

        self._did = canon_did(value) if value else None

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
            self.service[item.id] = item
        elif isinstance(item, PublicKey):
            self.pubkey[item.id] = item
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
            "@context": DIDDoc.CONTEXT,
            "id": canon_ref(self.did, self.did),
            "publicKey": [pubkey.to_dict() for pubkey in self.pubkey.values()],
            "authentication": [
                {
                    "type": pubkey.type.authn_type,
                    "publicKey": canon_ref(self.did, pubkey.id),
                }
                for pubkey in self.pubkey.values()
                if pubkey.authn
            ],
            "service": [service.to_dict() for service in self.service.values()],
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
                            did=self.did,
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
    def deserialize(cls, did_doc: dict) -> "DIDDoc":
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
            rv = DIDDoc(did_doc["id"])
        else:
            # heuristic: get DID to serve as DID document identifier from
            # the first OK-looking public key
            for section in ("publicKey", "authentication"):
                if rv is None and section in did_doc:
                    for key_spec in did_doc[section]:
                        try:
                            pubkey_did = canon_did(resource(key_spec.get("id", "")))
                            if ok_did(pubkey_did):
                                rv = DIDDoc(pubkey_did)
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
                canon_ref(rv.did, ak.get("publicKey", ""))
                == canon_ref(rv.did, pubkey["id"])
                for ak in did_doc.get("authentication", {})
                if isinstance(ak.get("publicKey", None), str)
            )
            key = PublicKey(  # initialization canonicalizes id
                did=rv.did,
                ident=pubkey["id"],
                value=pubkey[pubkey_type.specifier],
                pk_type=pubkey_type,
                controller=canon_did(pubkey["controller"]),
                authn=authn,
            )
            rv.pubkey[key.id] = key

        for akey in did_doc.get(
            "authentication", {}
        ):  # include embedded authentication keys
            if "publicKey" not in akey:  # not yet got it with public keys
                pubkey_type = PublicKeyType.get(akey["type"])
                key = PublicKey(  # initialization canonicalized id
                    did=rv.did,
                    ident=akey["id"],
                    value=akey[pubkey_type.specifier],
                    pk_type=pubkey_type,
                    controller=canon_did(akey["controller"]),
                    authn=True,
                )
                rv.pubkey[key.id] = key

        for service in did_doc.get("service", {}):
            endpoint = service["serviceEndpoint"]
            svc = Service(  # initialization canonicalizes id
                did=rv.did,
                ident=service.get(
                    "id",
                    canon_ref(
                        rv.did, "assigned-service-{}".format(len(rv.service)), ";"
                    ),
                ),
                typ=service["type"],
                recip_keys=rv.add_service_pubkeys(service, "recipientKeys"),
                routing_keys=rv.add_service_pubkeys(
                    service, ["mediatorKeys", "routingKeys"]
                ),
                endpoint=canon_ref(rv.did, endpoint, ";")
                if ";" in endpoint
                else endpoint,
                priority=service.get("priority", None),
            )
            rv.service[svc.id] = svc

        return rv

    @classmethod
    def from_json(cls, did_doc_json: str) -> "DIDDoc":
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


class DIDPeerDoc:
    """
    Peer DID document, grouping a DID with verification keys and services.

    """

    CONTEXT = "https://w3id.org/did/v1"

    def __init__(self, did: str = None) -> None:
        """
        Initialize the DIDPeerDoc instance.

        Retain DID ('id' in DIDPeerDoc context); initialize verification keys
        and services to empty lists.

        Args:
            did: DID for current DIDdoc

        Raises:
            ValueError: for bad input DID.

        """

        self._did = canon_did(did) if did else None  # allow specification post-hoc
        self._pubkey = {}
        self._service = {}

    @property
    def did(self) -> str:
        """Accessor for DID."""

        return self._did

    @did.setter
    def did(self, value: str) -> None:
        """
        Set DID ('id' in DIDPeerDoc context).

        Args:
            value: DID

        Raises:
            ValueError: for bad input DID.

        """

        self._did = canon_did(value) if value else None

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

    def add_controller_to_pk(self, controller: str):
        """Add controller to PublicKey after Peer DID is available"""
        for pk in self._pubkey:
            pk.controller = controller
            self.set(pk)

    def set(self, item: Union[Service, PublicKey]) -> "DIDPeerDoc":
        """
        Add or replace service or public key; return current DIDPeerDoc.

        Raises:
            ValueError: if input item is neither service nor public key.

        Args:
            item: service or public key to set

        Returns: the current DIDPeerDoc

        """

        if isinstance(item, Service):
            self.service[item.id] = item
        elif isinstance(item, PublicKey):
            self.pubkey[item.id] = item
        else:
            raise ValueError(
                "Cannot add item {} to DIDPeerDoc on DID {}".format(item, self.did)
            )

    def serialize(self) -> dict:
        """
        Dump current object to a JSON-compatible dictionary.

        Returns:
            dict representation of current DIDPeerDoc

        """

        return {
            "@context": DIDPeerDoc.CONTEXT,
            "id": self.did,
            "authentication": [
                {
                    "type": pubkey.type.authn_type,
                    "publicKeyBase58": pubkey.value,
                    "id": f"#{str(uuid4())}",
                }
                for pubkey in self.pubkey.values()
                if pubkey.authn
            ],
            "keyAgreement": [
                {
                    "type": pubkey.type.authn_type,
                    "publicKeyBase58": pubkey.value,
                    "id": f"#{str(uuid4())}",
                }
                for pubkey in self.pubkey.values()
                if not pubkey.authn
            ],
            "service": [service.to_dict() for service in self.service.values()],
        }

    def to_json(self) -> str:
        """
        Dump current object as json (JSON-LD).

        Returns:
            json representation of current DIDPeerDoc

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
                pubkey = None
                if tag is "recipientKeys":
                    pubkey = PublicKey(
                        did=self.did,
                        ident=svc_key[-9:-1],  # industrial-grade uniqueness
                        value=svc_key,
                    )
                elif tag is "routingKeys":
                    pk_b58 = (
                        DIDKey.from_fingerprint(svc_key.split("#"[1]))
                    ).public_key_b58
                    pubkey = PublicKey(
                        did=self.did,
                        ident=svc_key[-9:-1],  # industrial-grade uniqueness
                        value=pk_b58,
                    )
                if pubkey and pubkey not in rv:
                    rv.append(pubkey)

        return rv

    @classmethod
    def deserialize(cls, did_peer_doc: dict) -> "DIDPeerDoc":
        """
        Construct DIDPeerDoc object from dict representation.

        Args:
            did_doc: DIDPeerDoc dict representation

        Raises:
            ValueError: for bad DID or missing mandatory item.

        Returns: DIDPeerDoc from input json

        """

        rv = None
        rv = DIDPeerDoc(did_peer_doc["id"])
        if rv is None:
            LOGGER.debug("no peer DID identifier in DID document")
            raise ValueError("No peer DID identifier in DID document")

        for key_agreement in did_peer_doc.get("keyAgreement", {}):
            pubkey_type = PublicKeyType.get(key_agreement["type"])
            key = PublicKey(
                did=rv.did,
                ident=key_agreement["id"],
                value=key_agreement[pubkey_type.specifier],
                pk_type=pubkey_type,
                authn=False,
            )
            rv.pubkey[key.id] = key

        for akey in did_peer_doc.get("authentication", {}):
            pubkey_type = PublicKeyType.get(akey["type"])
            key = PublicKey(
                did=rv.did,
                ident=akey["id"],
                value=akey[pubkey_type.specifier],
                pk_type=pubkey_type,
                authn=True,
            )
            rv.pubkey[key.id] = key

        for service in did_peer_doc.get("service", {}):
            endpoint = service["serviceEndpoint"]
            svc = Service(  # initialization canonicalizes id
                did=rv.did,
                ident=service.get(
                    "id",
                    canon_ref(
                        rv.did, "assigned-service-{}".format(len(rv.service)), ";"
                    ),
                ),
                typ=service["type"],
                recip_keys=rv.add_service_pubkeys(service, "recipientKeys"),
                routing_keys=rv.add_service_pubkeys(
                    service, ["mediatorKeys", "routingKeys"]
                ),
                endpoint=canon_ref(rv.did, endpoint, ";")
                if ";" in endpoint
                else endpoint,
                priority=service.get("priority", None),
            )
            rv.service[svc.id] = svc

        return rv

    @classmethod
    def from_json(cls, did_doc_json: str) -> "DIDDoc":
        """
        Construct DIDPeerDoc object from json representation.

        Args:
            did_doc_json: DIDPeerDoc json representation

        Returns: DIDPeerDoc from input json

        """

        return cls.deserialize(json.loads(did_doc_json))

    def __str__(self) -> str:
        """Return string representation for abbreviated display."""

        return f"DIDPeerDoc({self.did})"

    def __repr__(self) -> str:
        """Format DIDPeerDoc for logging."""

        return f"<DIDPeerDoc did={self.did}>"
