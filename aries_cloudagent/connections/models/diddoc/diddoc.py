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
from pydid import DIDCommService, DIDUrl
from peerdid.dids import DID, DIDDocument, encode_service, resolve_peer_did
from multiformats import multibase
from .publickey import PublicKey, PublicKeyType
from .service import Service
from ....did.did_key import DIDKey, KeyTypes
from .util import canon_did, canon_ref, ok_did, resource, upgrade_legacy_did_doc_to_peer_did
from ....wallet.util import b58_to_bytes
from ....utils.jwe import b64url, from_b64url, JweEnvelope, JweRecipient

LOGGER = logging.getLogger(__name__)


# class UnqualifiedDIDDoc(DIDDocument):
#     """
#     DID document, grouping a DID with verification keys and services.

#     Retains DIDs as raw values (orientated toward indy-facing operations),
#     everything else as URIs (oriented toward W3C-facing operations).
#     """

#     # ACAPY USED UNQUALIFIED DIDS, allow them in DIDDoc's for now....
#     id: Union[DID, str] = ""
#     controller: Optional[List[Union[DID, str]]] = None


# class LegacyTESTDIDDoc(UnqualifiedDIDDoc):
#     # TODO How much of this class can be destroyed....
#     @property
#     def did(self) -> str:
#         """Accessor for DID."""
#         return self.id

#     @did.setter
#     def did(self, value: str) -> None:
#         """
#         Set DID ('id' in DIDDoc context).

#         Args:
#             value: DID

#         Raises:
#             ValueError: for bad input DID.

#         """

#         self.id = canon_did(value) if value else None



#     def to_json(self) -> str:
#         """
#         Dump current object as json (JSON-LD).

#         Returns:
#             json representation of current DIDDoc

#         """

#         return json.dumps(self.serialize())

#     def add_service_pubkeys(
#         self, service: dict, tags: Union[Sequence[str], str]
#     ) -> List[PublicKey]:
#         """
#         Add public keys specified in service. Return public keys so discovered.

#         Args:
#             service: service from DID document
#             tags: potential tags marking public keys of type of interest
#                 (the standard is still coalescing)

#         Raises:
#             ValueError: for public key reference not present in DID document.

#         Returns: list of public keys from the document service specification

#         """

#         rv = []
#         for tag in [tags] if isinstance(tags, str) else list(tags):
#             for svc_key in service.get(tag, {}):
#                 canon_key = canon_ref(self.did, svc_key)
#                 pubkey = None

#                 if "#" in svc_key:
#                     if canon_key in self.pubkey:
#                         pubkey = self.pubkey[canon_key]
#                     else:  # service key refers to another DID doc
#                         LOGGER.debug(
#                             "DID document %s has no public key %s", self.did, svc_key
#                         )
#                         raise ValueError(
#                             "DID document {} has no public key {}".format(
#                                 self.did, svc_key
#                             )
#                         )
#                 else:
#                     for existing_pubkey in self.pubkey.values():
#                         if existing_pubkey.value == svc_key:
#                             pubkey = existing_pubkey
#                             break
#                     else:
#                         pubkey = PublicKey(
#                             self.did,
#                             ident=svc_key[-9:-1],  # industrial-grade uniqueness
#                             value=svc_key,
#                         )
#                         self._pubkey[pubkey.id] = pubkey

#                 if (
#                     pubkey and pubkey not in rv
#                 ):  # perverse case: could specify same key multiple ways; append once
#                     rv.append(pubkey)

#         return rv

#     @classmethod
#     def deserialize(cls, did_doc: dict) -> "LegacyDIDDoc":
#         """
#         Construct DIDDoc object from dict representation.

#         Args:
#             did_doc: DIDDoc dict representation

#         Raises:
#             ValueError: for bad DID or missing mandatory item.

#         Returns: DIDDoc from input json

#         """
#         def make_didurl(id, not_found):
#             rv = None
#             if id:
#                 if "#" in id:
#                     rv = id.split("#")[1]
#                 else:
#                     rv = not_found
#             else: 
#                 rv = not_found


#             if rv[0] != "#":
#                 rv = "#" + rv

#             return rv

#         rv = None
#         new_did_doc = did_doc.copy()

#         key_dict = {}

#         if not DIDUrl.is_valid(new_did_doc["id"]):
#             new_did_doc["id"] = "did:sov:"+new_did_doc["id"]

#         if "publicKey" in new_did_doc:
#             key_dict = {pk["id"]:pk for pk in new_did_doc["publicKey"]}
#             new_did_doc["verificationMethod"] = []
#             for i, pk in enumerate(new_did_doc.pop("publicKey")):
#                 # replace publicKeys with VerificationMethod
#                 pk["id"] = make_didurl(pk["id"],f"#vm-{i}")

#                 new_did_doc["verificationMethod"].append(pk)

#         new_auth_list = []
#         if "verificationMethod" not in new_did_doc:
#             new_did_doc["verificationMethod"] = []

#         for i, auth in enumerate(new_did_doc.get("authentication",[])):
#             if isinstance(auth,dict):
#                 id = make_didurl(auth.get("id"),f"#vma-{i}")

#                 #create verificationmethod 
#                 new_vm = {
#                         "id":id,
#                         "controller":new_did_doc["id"],
#                     }
#                 new_vm.update({k:m for (k,m) in auth.items() if k not in ["id","controller"]})
#                 new_did_doc["verificationMethod"].append(new_vm)
#                 # and now reference it
#                 new_auth_list.append(new_vm["id"])

#             elif isinstance(auth, str):
#                 new_auth_list.append(auth)
        
#         new_did_doc["authentication"]=new_auth_list

#         for i, service in enumerate(new_did_doc.get("service", [])):
#             if ";" in service.get("id",""):
#                 # legacy DIDDoc behaviour
#                 service["id"] = service["id"].replace(";", "#")
            
#             service["id"] = make_didurl(service.get("id"), f"#service{i}")

#             if "recipientKeys" in service and new_did_doc["verificationMethod"]:
#                 # must be referenced, not directly embedded
#                 service["recipient_keys"] = [new_did_doc["verificationMethod"][0]["id"]]
#                 service.pop("recipientKeys")
#             else:
#                 service["recipient_keys"] = service.get("recipient_keys",[])

#             if ";" in service.get("serviceEndpoint",""):
#                 # this is trying to be a didUrl
#                 service["serviceEndpoint"] = service["serviceEndpoint"].replace(";", "#")


#         rv = super().deserialize(new_did_doc)

#         for s in rv.service:
#             # if s is not a DIDCommService, errors will arise later... after serde it will become an UnknownService
#             assert isinstance(s, DIDCommService), s
#         return rv

#     # TIMO's algo, based on https://github.com/TimoGlastra/legacy-did-transformation
#     @classmethod
#     def deserialize3(cls, did_doc: dict) -> "LegacyDIDDoc":
#         """
#         Construct DIDDoc object from dict representation.

#         Args:
#             did_doc: DIDDoc dict representation

#         Raises:
#             ValueError: for bad DID or missing mandatory item.

#         Returns: DIDDoc from input json

#         """

#         did = "did:peer:2"
#         authenticationFingerprints = []
#         _resolved_legacy_authentication = None
#         resolved_legacy_authentication = None
#         #3
#         for legacy_auth in did_doc.get("authentication",[]) :
#             if legacy_auth["type"] not in ("Ed25519SignatureAuthentication2018","Ed25519VerificationKey2018"):
#                 continue
#             key_type_name = None
#             auth_pk = legacy_auth.get('publicKey')
#             if legacy_auth["type"]  == "Ed25519SignatureAuthentication2018" and auth_pk:
#                 pk_entry = [pk for pk in did_doc["publicKey"] if pk["id"] == auth_pk]
#                 if not pk_entry:
#                   raise Exception("")
#                 _resolved_legacy_authentication = pk_entry[0]
#                 key_type_name = "x25519"
#             if legacy_auth["type"] == "Ed25519Signature2018":
#                 _resolved_legacy_authentication = legacy_auth
#                 key_type_name = "ed25519"
#             #3.iv
#             if not _resolved_legacy_authentication:
#                 raise Exception(f"Could not find referenced key ${legacy_auth['publicKey']}")
#             else: 
#                 resolved_legacy_authentication = _resolved_legacy_authentication

#             fingerprint = DIDKey.from_public_key_b58(resolved_legacy_authentication["publicKeyBase58"],KeyTypes().from_key_type(key_type_name)).fingerprint


#             authenticationFingerprints.append(fingerprint)

#         for legacy_pk in did_doc.get("publicKey", []):
#             if legacy_pk["type"] != "Ed25519VerificationKey2018":
#                 continue
#             fingerprint = multibase.encode(
#                 b58_to_bytes(legacy_pk["publicKeyBase58"]), "base58btc"
#             )
#             if fingerprint not in authenticationFingerprints:
#                 authenticationFingerprints.append(fingerprint)
    

#         for fp in authenticationFingerprints:
#             did += f'.V{fp}'


#         for service in did_doc.get("service",[]):
#             json_dict = {
#                 "priority": service.get("priority"),
#                 "routingKeys": service.get("routingKeys"),
#                 "recipientKeys": service.get("recipientKeys"),
#                 "serviceEndpoint": service.get("serviceEndpoint"),
#                 "type": "IndyAgent"
#             }
#             #remove null
#             json_dict = {k:v for (k,v) in json_dict.items() if v }

#             encoded = encode_service(json_dict)
            
#             did+=encoded
#         #did complete
#         return resolve_peer_did(did)

#     @classmethod
#     def from_json(cls, did_doc_json: str) -> "LegacyDIDDoc":
#         """
#         Construct DIDDoc object from json representation.

#         Args:
#             did_doc_json: DIDDoc json representation

#         Returns: DIDDoc from input json

#         """

#         return cls.deserialize(json.loads(did_doc_json))

#     def __str__(self) -> str:
#         """Return string representation for abbreviated display."""

#         return f"LegacyDIDDoc({self.did})"

#     def __repr__(self) -> str:
#         """Format LegacyDIDDoc for logging."""

#         return f"<LegacyDIDDoc did={self.did}>"


class DIDDoc:
    """
    DID document, grouping a DID with verification keys and services.

    Retains DIDs as raw values (orientated toward indy-facing operations),
    everything else as URIs (oriented toward W3C-facing operations).
    """

    CONTEXT = "https://w3id.org/did/v1"

    def __init__(self, id: str = None) -> None:
        """
        Initialize the DIDDoc instance.

        Retain DID ('id' in DIDDoc context); initialize verification keys
        and services to empty lists.

        Args:
            did: DID for current DIDdoc

        Raises:
            ValueError: for bad input DID.

        """

        self._did = canon_did(id) if id else None  # allow specification post-hoc
        self._pubkey = {}
        self._service = {}

    @property
    def did(self) -> str:
        """Accessor for DID."""

        return self._did

    @property
    def id(self) -> str:
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
    def deserialize(cls, did_doc: dict) -> "DIDDocument":
        """
        Construct DIDDoc object from dict representation.

        Args:
            did_doc: DIDDoc dict representation

        Raises:
            ValueError: for bad DID or missing mandatory item.

        Returns: DIDDoc from input json

        """
        return upgrade_legacy_did_doc_to_peer_did(json.dumps(did_doc))[1]
        ## ANY ATTEMPTED DESERIALIZATION SHOULD RETURN DIDDocument


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


LegacyDIDDoc = DIDDoc
