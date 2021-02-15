"""
DID Document PublicKey Class.

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
from typing import Sequence, Union

from .schemas.verificationmethodschema import VerificationMethodSchema
from .publickeytype import PublicKeyType
from ....resolver.did import DIDUrl


class PublicKey:
    """
    Public key specification to embed in DID document.

    Retains DIDs as raw values (orientated toward indy-facing operations),
    everything else as URIs (oriented toward W3C-facing operations).
    """

    def __init__(
        self,
        id: str,
        type: PublicKeyType,
        controller: Union[str, Sequence],
        usage: str = None,
        value: str = None,
        authn: bool = False,
        **kwargs
    ) -> None:

        """
        Retain key specification particulars.

        Args:
            did: DID of DID document embedding public key
            ident: identifier for public key
            value: key content, encoded as key specification requires
            pk_type: public key type (enum), default ED25519_SIG_2018
            controller: controller DID (default DID of DID document)
            authn: whether key as has DID authentication privilege (default False)

        Raises:
            ValueError: on any bad input DID.

        """

        self._id = id
        self._type = type
        self._controller = controller
        self._usage = usage
        self._authn = authn
        if kwargs:
            value = kwargs.get(PublicKeyType.get(type).specifier)
        self._fill_key(value)

    def _fill_key(self, value: str):
        if self._type == "RsaVerificationKey2018":
            self.publicKeyPem = value

        elif self._type == "Ed25519VerificationKey2018":
            self.publicKeyBase58 = value

        elif self._type == "Secp256k1VerificationKey2018":
            self.publicKeyHex = value

        elif self._type == "EcdsaSecp256k1RecoveryMethod2020":
            try:
                value = dict(value)
            except:
                value = json.loads(value)
            self.publicKeyJwk = value

    def _get_key(self):
        if self._type == "RsaVerificationKey2018":
            return self.publicKeyPem

        elif self._type == "Ed25519VerificationKey2018":
            return self.publicKeyBase58

        elif self._type == "Secp256k1VerificationKey2018":
            return self.publicKeyHex

        elif self._type == "EcdsaSecp256k1RecoveryMethod2020":
            return str(self.publicKeyJwk)

    @property
    def id(self) -> str:
        """Getter for the public key identifier."""

        return self._id

    @id.setter
    def id(self, value: str):
        """Setter for the public key identifier."""

        # Validation process
        DIDUrl.parse(value)
        self._id = value

    @property
    def type(self) -> PublicKeyType:
        """Getter for the public key type."""

        return self._type

    @type.setter
    def type(self, value: PublicKeyType):
        """Setter for the public key type."""

        self._type = value

    @property
    def value(self) -> str:
        """Getter for the public key value."""

        return self._get_key()

    @value.setter
    def value(self, value: str):
        """Setter for the public key value."""

        self.__fill_key__(value)

    @property
    def usage(self) -> PublicKeyType:
        """Getter for the public key usage."""

        return self._usage

    @usage.setter
    def usage(self, value: PublicKeyType):
        """Setter for the public key usage."""

        self._usage = value

    @property
    def controller(self) -> Union[str, Sequence]:
        """Getter for the controller DID."""

        return self._controller

    @controller.setter
    def controller(self, value: Union[str, Sequence]):
        """Setter for the controller DID."""

        self._controller = value

    @property
    def authn(self) -> bool:
        """Accessor for the authentication marker.

        Returns: whether public key is marked as having DID authentication privilege
        """

        return self._authn

    @authn.setter
    def authn(self, value: bool) -> None:
        """Setter for the authentication marker.

        Args:
            value: authentication marker
        """

        self._authn = value

    def serialize(self) -> dict:
        """Return dict representation of public key to embed in DID document."""
        schema = VerificationMethodSchema()
        result = schema.dump(self)
        return result

    @classmethod
    def deserialize(cls, value: dict):
        """Return a PublicKey object to embed in DIDDoc object.
        Args:
            value: dict representation of a publicKey"""
        schema = VerificationMethodSchema()
        pub_key = schema.load(value)
        return pub_key
