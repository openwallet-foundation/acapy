from pyld.jsonld import JsonLdProcessor
from datetime import datetime
from typing import Union
import json

from ....wallet.util import b64_to_bytes, bytes_to_b64, str_to_b64, b64_to_str
from ..crypto import KeyPair
from ..document_loader import DocumentLoader
from .LinkedDataSignature import LinkedDataSignature


class JwsLinkedDataSignature(LinkedDataSignature):
    def __init__(
        self,
        *,
        signature_type: str,
        algorithm: str,
        required_key_type: str,
        key_pair: KeyPair,
        verification_method: dict,
        proof: dict = None,
        date: Union[datetime, str] = None,
    ):

        super().__init__(
            signature_type=signature_type,
            verification_method=verification_method,
            proof=proof,
            date=date,
        )

        self.algorithm = algorithm
        self.key_pair = key_pair
        self.required_key_type = required_key_type

    async def sign(self, verify_data: bytes, proof: dict):
        header = {"alg": self.algorithm, "b64": False, "crit": ["b64"]}
        encoded_header = self._encode_header(header)

        data = self._create_jws(encoded_header, verify_data)
        signature = await self.key_pair.sign(data)

        encoded_signature = bytes_to_b64(
            signature, urlsafe=True, pad=False, encoding="utf-8"
        )

        proof["jws"] = encoded_header + ".." + encoded_signature

        return proof

    async def verify_signature(
        self,
        verify_data: bytes,
        verification_method: dict,
        document: dict,
        proof: dict,
        document_loader: DocumentLoader,
    ):
        if not (isinstance(proof.get("jws"), str) and (".." in proof.get("jws"))):
            raise Exception('The proof does not contain a valid "jws" property.')

        encoded_header, payload, encoded_signature = proof.get("jws").split(".")

        header = self._decode_header(encoded_header)
        self._validate_header(header)

        signature = b64_to_bytes(encoded_signature, urlsafe=True)
        data = self._create_jws(encoded_header, verify_data)

        return await self.key_pair.verify(data, signature)

    def _decode_header(self, encoded_header: str) -> dict:
        header = None
        try:
            header = json.loads(b64_to_str(encoded_header, urlsafe=True))
        except Exception:
            raise Exception("Could not parse JWS header.")
        return header

    def _encode_header(self, header: dict) -> str:
        return str_to_b64(json.dumps(header), urlsafe=True, pad=False)

    def _create_jws(self, encoded_header: str, verify_data: bytes) -> bytes:
        """Compose JWS."""
        return (encoded_header + ".").encode("utf-8") + verify_data

    def _validate_header(self, header: dict):
        """ Validates the JWS header, throws if not ok """
        if not (header and isinstance(header, dict)):
            raise Exception("Invalid JWS header.")

        if not (
            header.get("alg") == self.algorithm
            and header.get("b64") is False
            and isinstance(header.get("crit"), list)
            and len(header.get("crit")) == 1
            and header.get("crit")[0] == "b64"
            and len(header.keys()) == 3
        ):
            raise Exception(f"Invalid JWS header params for {self.signature_type}")

    def _assert_verification_method(self, verification_method: dict):
        if not JsonLdProcessor.has_value(
            verification_method, "type", self.required_key_type
        ):
            raise Exception(
                f"Invalid key type. The key type must be {self.required_key_type}"
            )

    def _get_verification_method(self, proof: dict, document_loader: DocumentLoader):
        verification_method = super()._get_verification_method(proof, document_loader)
        self._assert_verification_method(verification_method)
        return verification_method
