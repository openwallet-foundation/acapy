"""
DID Document Public Key classes.

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

from collections import namedtuple
from enum import Enum

LinkedDataKeySpec = namedtuple("LinkedDataKeySpec", "ver_type authn_type specifier")


class PublicKeyType(Enum):
    """Class encapsulating public key types."""

    RSA_SIG_2018 = LinkedDataKeySpec(
        "RsaVerificationKey2018", "RsaSignatureAuthentication2018", "publicKeyPem"
    )
    ED25519_SIG_2018 = LinkedDataKeySpec(
        "Ed25519VerificationKey2018",
        "Ed25519SignatureAuthentication2018",
        "publicKeyBase58",
    )
    EDDSA_SA_SIG_SECP256K1 = LinkedDataKeySpec(
        "Secp256k1VerificationKey2018",
        "Secp256k1SignatureAuthenticationKey2018",
        "publicKeyHex",
    )

    @staticmethod
    def get(val: str) -> "PublicKeyType":
        """
        Find enum instance corresponding to input value (RsaVerificationKey2018 etc).

        Args:
            val: input value marking public key type

        Returns: the public key type

        """

        for pktype in PublicKeyType:
            if val in (pktype.ver_type, pktype.authn_type):
                return pktype
        return None

    @property
    def ver_type(self) -> str:
        """Accessor for the verification type identifier."""

        return self.value.ver_type

    @property
    def authn_type(self) -> str:
        """Accessor for the authentication type identifier."""

        return self.value.authn_type

    @property
    def specifier(self) -> str:
        """Accessor for the value specifier."""

        return self.value.specifier

    def specification(self, val: str) -> str:
        """
        Return specifier and input value for use in public key specification.

        Args:
            val: value of public key

        Returns: dict mapping applicable specifier to input value

        """

        return {self.specifier: val}
