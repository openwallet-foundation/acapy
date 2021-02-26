"""
DID Document Class.

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

import logging
import copy
import json
from typing import Union, Sequence

from .publickeytype import PublicKeyType
from .verification_method import VerificationMethod
from .service import Service
from .schemas.diddocschema import DIDDocSchema
from ....resolver.did import DID_PATTERN, DIDUrl

LOGGER = logging.getLogger(__name__)


class DIDDoc:
    """
    DID document, grouping a DID with verification keys and services.

    Retains DIDs as raw values (orientated toward indy-facing operations),
    everything else as URIs (oriented toward W3C-facing operations).
    """

    CONTEXT = "https://w3id.org/did/v1"

    def __init__(
            self,
            id: str,
            also_known_as: list = None,
            controller=None,
            verification_method: list = None,
            authentication: list = None,
            assertion_method: list = None,
            key_agreement: list = None,
            capability_invocation: list = None,
            capability_delegation: list = None,
            public_key: list = None,
            service: list = None,
    ) -> None:
        """
        Initialize the DIDDoc instance.

        Retain DID ('id' in DIDDoc context); initialize verification keys
        and services to empty lists.

        Args:
            id: DIDDoc id.
            also_known_as: One or more other identifiers of the DIDDoc.
            controller: Contain verification relationships of the DIDDoc.
            verification_method: Specific verification method of the DIDDoc.
            authentication: Specific verification method of the DIDDoc.
            assertion_method: Specific verification method of the DIDDoc.
            key_agreement: Specific verification method of the DIDDoc.
            capability_invocation: Specific verification method of the DIDDoc.
            capability_delegation: Specific verification method of the DIDDoc.,
            public_key: Specific verification method of the DIDDoc.
            service: Communicating of the DID subject or associated entities.

        Raises:
            ValueError: for bad input DID.

        """
        # Validation process
        DIDDoc.validate_id(id)

        self._id = id
        self._also_known_as = also_known_as
        self._controller = controller
        self._index = {}
        self._ref_content = {}

        params = (
            ("verificationMethod", verification_method or []),
            ("authentication", authentication or []),
            ("assertionMethod", assertion_method or []),
            ("keyAgreement", key_agreement or []),
            ("capabilityInvocation", capability_invocation or []),
            ("capabilityDelegation", capability_delegation or []),
            ("publicKey", public_key or []),
        )
        self._index_params(params)
        self._keys_refactor_on_services(service or [])

    def _keys_refactor_on_services(self, services):
        """Process to check the services keys and refactor to not duplicate data."""
        for service in services:
            routing = self._keys_refactor(service.routing_keys)
            recipient = self._keys_refactor(service.recipient_keys)
            service.recipient_keys = recipient
            service.routing_keys = routing

        param = (("service", services or []),)
        self._index_params(param)

    def _keys_refactor(self, keys):
        """Keys Refactor to set Keys and save the DID URL reference in services."""
        for index, key in enumerate(keys):
            if isinstance(key, str):
                if not self.dereference(key):
                    raise ValueError("Key '{}' not found on DIDDoc".format(key))
            else:
                self._set(key)
                keys[index] = key.id

        return keys

    def _index_params(self, params):
        """
        Process to index the DID Doc parameters.

        Args:
            params: Sequence with tuples that contains the name of the variable and the
            content.
        Raises:
            ValueError: Due to the duplication of the id with different content

        """
        for param in params:
            aux_content = []
            for item in param[1]:
                if not isinstance(item, str):
                    did_item = self._index.get(item.id)
                    if not self._index.get(item.id):
                        self._index[item.id] = item  # {id: <param object>}
                        aux_content.append(item.id)
                    else:
                        if not (did_item.serialize() == item.serialize()):
                            raise ValueError(
                                "{} has different specifications".format(item.id)
                            )
                        else:
                            aux_content.append(item.id)
                else:
                    if not self._index.get(item):
                        aux_content.append(item)
            self._ref_content[param[0]] = aux_content  # {param: [<List of Ids>]}

    @classmethod
    def validate_id(self, id: str):
        """
        Validate the ID by a RegEx.

        Args:
            id: DID Doc id to validate
        """
        if not DID_PATTERN.match(id):
            raise ValueError("Not valid DID")

    @classmethod
    def deserialize(cls, did_doc: Union[dict, str]):
        """
        Deserialize a dict into a DIDDoc object.

        Args:
            did_doc: service or public key to set
        Returns: DIDDoc object
        """
        if isinstance(did_doc, str):
            did_doc = json.loads(did_doc)
        schema = DIDDocSchema()
        did_doc = schema.load(did_doc)
        return did_doc

    def serialize(self) -> dict:
        """
        Serialize the DIDDoc object into dict.

        Returns: Dict
        """
        schema = DIDDocSchema()
        did_doc = schema.dump(copy.deepcopy(self))
        did_doc["@context"] = self.CONTEXT
        return did_doc

    @property
    def id(self) -> str:
        """Getter for DIDDoc id."""
        return self._id

    @property
    def also_known_as(self):
        """Getter for DIDDoc alsoKnownAs."""
        return self._also_known_as

    @property
    def controller(self):
        """Getter for DIDDoc controller."""
        return self._controller

    @property
    def verification_method(self):
        """Getter for DIDDoc verificationMethod."""
        aux_ids = []
        ids = self._ref_content.get("verificationMethod")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def authentication(self):
        """Getter for DIDDoc authentication."""
        aux_ids = []
        ids = self._ref_content.get("authentication")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def assertion_method(self):
        """Getter for DIDDoc assertionMethod."""
        aux_ids = []
        ids = self._ref_content.get("assertionMethod")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def key_agreement(self):
        """Getter for DIDDoc keyAgreement."""
        aux_ids = []
        ids = self._ref_content.get("keyAgreement")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def capability_invocation(self):
        """Getter for DIDDoc capabilityInvocation."""
        aux_ids = []
        ids = self._ref_content.get("capabilityInvocation")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def capability_delegation(self):
        """Getter for DIDDoc capabilityDelegation."""
        aux_ids = []
        ids = self._ref_content.get("capabilityDelegation")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def public_key(self):
        """Getter for DIDDoc publicKey."""
        aux_ids = []
        ids = self._ref_content.get("publicKey")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def service(self):
        """Getter for DIDDoc service."""
        aux_ids = []
        ids = self._ref_content.get("service")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @id.setter
    def id(self, value: str) -> None:
        """
        Set DID ('id' in DIDDoc context).

        Args:
            value: id

        Raises:
            ValueError: for bad input DID.

        """

        # Validation process
        DIDDoc.validate_id(value)

        self._id = value

    def add_verification_method(
            self,
            type: Union[PublicKeyType, str],
            controller: Union[str, Sequence],
            value: str,
            *,
            ident: str = None,
            usage: str = None,
            authentication: bool = False,
            verification_type: str = "publicKey",
            upsert: bool = False
    ) -> VerificationMethod:
        """Add a verification method to this document."""
        if ident:
            id = "{}#{}".format(self.id, ident)
            if self._index.get(id) and not upsert:
                raise ValueError("ID already exists, use arg upsert to update it")
        else:
            for index in range(1, 100):
                id_aux = "{}#keys-{}".format(self.id, index)
                if not self._index.get(id_aux):
                    id = id_aux
                    break

        key = VerificationMethod(id, type, controller, usage, value, authentication)
        self._set(key, upsert=upsert, verification_type=verification_type)
        return key

    def add_service(
            self,
            type: Union[str, list],
            endpoint: Union[str, Sequence, dict],
            ident: str = None,
            priority: int = 0,
            upsert: bool = False
    ) -> Service:
        """Add service to this document."""
        if ident:
            id = "{}#{}".format(self.id, ident)
            if self._index.get(id) and not upsert:
                raise ValueError("ID already exists, use arg upsert to update it")
        else:
            for index in range(1, 100):
                id_aux = "{}#service-{}".format(self.id, index)
                if not self._index.get(id_aux):
                    id = id_aux
                    break

        service = Service(id, type, endpoint, priority=priority)
        self._set(service, upsert=upsert)

    def _add_keys(self, keys):
        result = []
        if isinstance(keys, list):
            for key in keys:
                result.append(key.id)
                self._set(key)

        elif isinstance(keys, VerificationMethod):
            result.append(keys.id)
            self._set(keys)

        return result

    def add_didcomm_service(
            self,
            type: Union[str, list],
            recipient_keys: Union[Sequence[VerificationMethod], VerificationMethod],
            routing_keys: Union[Sequence[VerificationMethod], VerificationMethod],
            endpoint: Union[str, Sequence, dict],
            priority: int = 0
    ) -> Service:
        """Add DIDComm Service to this document."""
        for index in range(1, 100):
            id_aux = "{}#didcomm-{}".format(self.id, index)
            if not self._index.get(id_aux):
                id = id_aux
                break

        # RECIPIENT KEYS
        recip_keys = self._add_keys(recipient_keys)

        # ROUTING KEYS
        rout_keys = self._add_keys(routing_keys)

        service = Service(id, type, endpoint, recip_keys, rout_keys, priority)
        self._set(service)

    def _set(
            self,
            item: Union[Service, VerificationMethod],
            upsert: bool = False,
            verification_type: str = "publicKey",
    ) -> "DIDDoc":
        """
        Add or replace service or verification method; return current DIDDoc.

        Raises:
            ValueError: if input item is neither service nor public key.

        Args:
            item: service or public key to set
            upsert: True for overwrite if the ID exists
            verification_type: verification atribute choosen to insert the item
            if it is a verification method.

        """
        # Upsert validation
        existing_item = self._index.get(item.id)
        if existing_item and (not upsert):
            if item.serialize() != existing_item.serialize():
                raise ValueError("ID already exists, use arg upsert to update it")
            else:
                return

        # Inserting item
        self._index[item.id] = item

        if isinstance(item, Service):
            if item.id not in self._ref_content["service"]:
                self._ref_content["service"].append(item.id)
        else:
            if item.id not in self._ref_content[verification_type]:
                self._ref_content[verification_type].append(item.id)

    def dereference(self, did_url: str):
        """
        Retrieve a verification method or service by it id.

        Raises:
            ValueError: if input did_url is not good defined.
        Args:
            did_url: verification method or service id.

        """

        # Verification did url
        DIDUrl.parse(did_url)

        return self._index.get(did_url)


class AntiquatedDIDDoc(DIDDoc):
    """Antiquated DIDDoc implementation for methodless ids."""

    PREFIX = "did:sov:"

    def __init__(self, nym: str, *args, **kwargs):
        """Initialize the antiquated DIDDoc instance."""
        did = self.PREFIX + nym
        super().__init__(did, *args, **kwargs)
