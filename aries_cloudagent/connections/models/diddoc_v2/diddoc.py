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

from typing import Union
from .publickey import PublicKey
from .service import Service
from .schemas.diddocschema import DIDDocSchema
from ....resolver.did import DIDUrl

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
        alsoKnownAs: list = None,
        controller=None,
        verificationMethod: list = [],
        authentication: list = [],
        assertionMethod: list = [],
        keyAgreement: list = [],
        capabilityInvocation: list = [],
        capabilityDelegation: list = [],
        publicKey: list = [],
        service: list = [],
    ) -> None:

        """
        Initialize the DIDDoc instance.

        Retain DID ('id' in DIDDoc context); initialize verification keys
        and services to empty lists.

        Args:
            did: DID for current DIDDoc.
            id: DIDDoc id.
            alsoKnownAs: One or more other identifiers of the DIDDoc.
            controller: Contain verification relationships of the DIDDoc.
            verificationMethod: Specific verification method of the DIDDoc.
            authentication: Specific verification method of the DIDDoc.
            assertionMethod: Specific verification method of the DIDDoc.
            keyAgreement: Specific verification method of the DIDDoc.
            capabilityInvocation: Specific verification method of the DIDDoc.
            capabilityDelegation: Specific verification method of the DIDDoc.,
            publicKey: Specific verification method of the DIDDoc.
            service: Communicating of the DID subject or associated entities.

        Raises:
            ValueError: for bad input DID.

        """

        self._id = id
        self._alsoKnownAs = alsoKnownAs
        self._controller = controller
        self._index = {}
        self._ref_content = {}

        params = (
            ("verificationMethod", verificationMethod),
            ("authentication", authentication),
            ("assertionMethod", assertionMethod),
            ("keyAgreement", keyAgreement),
            ("capabilityInvocation", capabilityInvocation),
            ("capabilityDelegation", capabilityDelegation),
            ("publicKey", publicKey),
            ("service", service),
        )

        for param in params:
            aux_content = []
            for item in param[1]:
                if not isinstance(item, str):
                    did_item = self._index.get(item)
                    if not self._index.get(item):
                        self._index[item.id] = item  # {id: <kind of param>}
                        aux_content.append(item.id)
                    else:
                        if not (did_item.serialize() == item.serialize()):
                            raise ValueError(
                                "{} has different specifications".format(item.id)
                            )
                else:
                    if not self._index.get(item):
                        self._index[item] = param[0]
                        aux_content.append(item.id)
            self._ref_content[param[0]] = aux_content

    @classmethod
    def deserialize(cls, json: dict):
        """
        Deserialize a dict into a DIDDoc object.

        Args:
            json: service or public key to set
        Returns: DIDDoc object
        """
        schema = DIDDocSchema()
        did_doc = schema.load(json)
        return did_doc

    def serialize(self) -> dict:
        """
        Serialize the DIDDoc object into dict.

        Returns: Dict
        """
        schema = DIDDocSchema()
        did_doc = schema.dump(self)
        did_doc["@context"] = self.CONTEXT
        return did_doc

    @property
    def id(self) -> str:
        """
        Getter for DIDDoc id
        """
        return self._id

    @property
    def alsoKnownAs(self):
        """
        Getter for DIDDoc alsoKnownAs
        """
        return self._alsoKnownAs

    @property
    def controller(self):
        """
        Getter for DIDDoc controller
        """
        return self._controller

    @property
    def verificationMethod(self):
        """
        Getter for DIDDoc verificationMethod
        """
        aux_ids = []
        ids = self._ref_content.get("verificationMethod")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def authentication(self):
        """
        Getter for DIDDoc authentication
        """
        aux_ids = []
        ids = self._ref_content.get("authentication")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def assertionMethod(self):
        """
        Getter for DIDDoc assertionMethod
        """
        aux_ids = []
        ids = self._ref_content.get("assertionMethod")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def keyAgreement(self):
        """
        Getter for DIDDoc keyAgreement
        """
        aux_ids = []
        ids = self._ref_content.get("keyAgreement")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def capabilityInvocation(self):
        """
        Getter for DIDDoc capabilityInvocation
        """
        aux_ids = []
        ids = self._ref_content.get("capabilityInvocation")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def capabilityDelegation(self):
        """
        Getter for DIDDoc capabilityDelegation
        """
        aux_ids = []
        ids = self._ref_content.get("capabilityDelegation")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def publicKey(self):
        """
        Getter for DIDDoc publicKey
        """
        aux_ids = []
        ids = self._ref_content.get("publicKey")
        for item in ids:
            aux_ids.append(self._index.get(item))
        return aux_ids

    @property
    def service(self):
        """
        Getter for DIDDoc service
        """
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
        DIDUrl.parse(value)

        self._id = value

    def set(
        self,
        item: Union[Service, PublicKey],
        upsert=False,
        verification_type="publicKey",
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
        Returns: None
        """

        # Verification did url
        DIDUrl.parse(item.id)

        # Upsert validation
        if self._index.get(item.id) and (not upsert):
            raise ValueError("ID already exists, use arg upsert to update it")

        self._index[item.id] = item

        if isinstance(item, Service):
            if not item.id in self._ref_content["service"]:
                self._ref_content["service"].append(item.id)
        else:
            if not item.id in self._ref_content[verification_type]:
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
