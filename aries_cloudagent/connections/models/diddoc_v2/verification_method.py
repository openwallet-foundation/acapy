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
from aries_cloudagent.resolver.did import DIDUrl


class VerificationMethod:
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
        # Validation process
        DIDUrl.parse(id)

        self._id = id
        if isinstance(type, list) and len(type) == 1:
            type = type[0]

        self._type = type
        self._controller = controller
        self._usage = usage
        self._authn = authn
        item_type = None
        if kwargs and not value:
            item_type = PublicKeyType.get(type)
            if item_type:
                item_type = item_type.specifier
                value = kwargs.get(item_type)
            else:
                item_type, value = self._find_key_type_from_kwargs(kwargs)

        self._fill_key(value, item_type)

    def _find_key_type_from_kwargs(self, kwargs):
        keys = [
            "publicKeyBase58",
            "publicKeyHex",
            "publicKeyPem",
            "publicKeyBase64",
            "publicKeyJwk",
        ]
        for key in keys:
            if kwargs.get(key):
                return key, kwargs.get(key)
        raise ValueError('"{}" does not have Public Key'.format(self._id))

    def _fill_key(self, value: str, item_type: str = None):
        if item_type:
            if "publicKeyJwk" == item_type:
                try:
                    value = dict(value)
                except Exception:
                    value = json.loads(value)
                self.publicKeyJwk = value

            elif "publicKeyBase58" == item_type:
                self.publicKeyBase58 = value

            elif "publicKeyHex" == item_type:
                self.publicKeyHex = value

            elif "publicKeyPem" == item_type:
                self.publicKeyPem = value

            else:
                self.publicKeyBase64 = value

            self._key_value = value
            return

        if isinstance(self._type, PublicKeyType):
            self._type = self._type.ver_type

        if self._type == "RsaVerificationKey2018":
            self.publicKeyPem = value

        elif self._type == "Ed25519VerificationKey2018":
            self.publicKeyBase58 = value

        elif self._type == "Secp256k1VerificationKey2018":
            self.publicKeyHex = value

        elif self._type == "EcdsaSecp256k1RecoveryMethod2020":
            try:
                value = dict(value)
            except Exception:
                value = json.loads(value)
            self.publicKeyJwk = value

        self._key_value = value

    def _get_key(self):
        return self._key_value

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
        if isinstance(value, PublicKeyType):
            self._type = value.ver_type
        else:
            self._type = value

    @property
    def value(self):
        """Getter for the public key value."""

        return self._get_key()

    @value.setter
    def value(self, value: str):
        """Setter for the public key value."""

        self._fill_key(value)

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
        """
        Return a PublicKey object to embed in DIDDoc object.

        Args:
            value: dict representation of a publicKey
        """
        schema = VerificationMethodSchema()
        pub_key = schema.load(value)
        return pub_key
