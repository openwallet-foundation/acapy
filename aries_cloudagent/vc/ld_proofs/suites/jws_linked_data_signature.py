"""JWS Linked Data class."""

import json

from datetime import datetime
from typing import Union

from pyld.jsonld import JsonLdProcessor

from ....wallet.util import b64_to_bytes, bytes_to_b64, str_to_b64, b64_to_str

from ..crypto import _KeyPair as KeyPair
from ..document_loader import DocumentLoaderMethod
from ..error import LinkedDataProofException

from .linked_data_signature import LinkedDataSignature


class JwsLinkedDataSignature(LinkedDataSignature):
    """JWS Linked Data class."""

    def __init__(
        self,
        *,
        signature_type: str,
        algorithm: str,
        required_key_type: str,
        key_pair: KeyPair,
        proof: dict = None,
        verification_method: str = None,
        date: Union[datetime, str] = None,
    ):
        """Create new JwsLinkedDataSignature instance.

        Must be subclassed, not initialized directly.

        Args:
            signature_type (str): Signature type for the proof, provided by subclass
            algorithm (str): JWS alg to use, provided by subclass
            required_key_type (str): Required key type in verification method.
            key_pair (KeyPair): Key pair to use, provided by subclass
            proof (dict, optional): A JSON-LD document with options to use for the
                `proof` node (e.g. any other custom fields can be provided here
                using a context different from security-v2).
            verification_method (str, optional): A key id URL to the paired public key.
            date (datetime, optional): Signing date to use. Defaults to now
        """

        super().__init__(
            signature_type=signature_type,
            verification_method=verification_method,
            proof=proof,
            date=date,
        )

        self.algorithm = algorithm
        self.key_pair = key_pair
        self.required_key_type = required_key_type

    async def sign(self, *, verify_data: bytes, proof: dict) -> dict:
        """Sign the data and add it to the proof.

        Adds a jws to the proof that can be used for multiple
        signature algorithms.

        Args:
            verify_data (bytes): The data to sign.
            proof (dict): The proof to add the signature to

        Returns:
            dict: The proof object with the added signature

        """

        header = {"alg": self.algorithm, "b64": False, "crit": ["b64"]}
        encoded_header = self._encode_header(header)

        data = self._create_jws(encoded_header=encoded_header, verify_data=verify_data)
        signature = await self.key_pair.sign(data)

        encoded_signature = bytes_to_b64(
            signature, urlsafe=True, pad=False, encoding="utf-8"
        )

        proof["jws"] = encoded_header + ".." + encoded_signature

        return proof

    async def verify_signature(
        self,
        *,
        verify_data: bytes,
        verification_method: dict,
        document: dict,
        proof: dict,
        document_loader: DocumentLoaderMethod,
    ):
        """Verify the data against the proof.

        Checks for a jws on the proof.

        Args:
            verify_data (bytes): The data to check
            verification_method (dict): The verification method to use.
            document (dict): The document the verify data is derived for as extra context
            proof (dict): The proof to check
            document_loader (DocumentLoader): Document loader used for resolving

        Returns:
            bool: Whether the signature is valid for the data

        """
        if not (isinstance(proof.get("jws"), str) and (".." in proof.get("jws"))):
            raise LinkedDataProofException(
                'The proof does not contain a valid "jws" property.'
            )

        encoded_header, payload, encoded_signature = proof.get("jws").split(".")

        header = self._decode_header(encoded_header)
        self._validate_header(header)

        signature = b64_to_bytes(encoded_signature, urlsafe=True)
        data = self._create_jws(encoded_header=encoded_header, verify_data=verify_data)

        # If the key pair has not public key yet, create a new key pair
        # from the verification method. We don't want to overwrite data
        # on the original key pair
        key_pair = self.key_pair
        if not key_pair.has_public_key:
            key_pair = key_pair.from_verification_method(verification_method)

        return await key_pair.verify(data, signature)

    def _decode_header(self, encoded_header: str) -> dict:
        """Decode header."""
        header = None
        try:
            header = json.loads(b64_to_str(encoded_header, urlsafe=True))
        except Exception:
            raise LinkedDataProofException("Could not parse JWS header.")
        return header

    def _encode_header(self, header: dict) -> str:
        """Encode header."""
        return str_to_b64(json.dumps(header), urlsafe=True, pad=False)

    def _create_jws(self, *, encoded_header: str, verify_data: bytes) -> bytes:
        """Compose JWS."""
        return (encoded_header + ".").encode("utf-8") + verify_data

    def _validate_header(self, header: dict):
        """Validate the JWS header, throws if not ok."""
        if not (header and isinstance(header, dict)):
            raise LinkedDataProofException("Invalid JWS header.")

        if not (
            header.get("alg") == self.algorithm
            and header.get("b64") is False
            and isinstance(header.get("crit"), list)
            and len(header.get("crit")) == 1
            and header.get("crit")[0] == "b64"
            and len(header.keys()) == 3
        ):
            raise LinkedDataProofException(
                f"Invalid JWS header params for {self.signature_type}"
            )

    def _assert_verification_method(self, verification_method: dict):
        """Assert verification method. Throws if not ok."""
        if not JsonLdProcessor.has_value(
            verification_method, "type", self.required_key_type
        ):
            raise LinkedDataProofException(
                f"Invalid key type. The key type must be {self.required_key_type}"
            )

    def _get_verification_method(
        self, *, proof: dict, document_loader: DocumentLoaderMethod
    ):
        """Get verification method.

        Overwrites base get verification method to assert key type.
        """
        verification_method = super()._get_verification_method(
            proof=proof, document_loader=document_loader
        )
        self._assert_verification_method(verification_method)

        return verification_method
