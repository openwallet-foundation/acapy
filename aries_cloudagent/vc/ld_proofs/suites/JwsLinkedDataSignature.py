from pyld import jsonld
from datetime import datetime
from typing import Union
import json

from ....wallet.util import bytes_to_b64, str_to_b64, b64_to_str
from ..crypto import KeyPair
from .LinkedDataSignature import LinkedDataSignature


class JwsLinkedDataSignature(LinkedDataSignature):
    def __init__(
        self,
        signature_type: str,
        algorithm: str,
        key_pair: KeyPair,
        verification_method: str,
        *,
        proof: dict = None,
        date: Union[datetime, str],
    ):

        super().__init__(signature_type, verification_method, proof=proof, date=date)

        self.algorithm = algorithm
        self.key_pair = key_pair

    def _decode_header(self, encoded_header: str) -> dict:
        header = None
        try:
            header = json.loads(b64_to_str(encoded_header, urlsafe=True))
        except Exception:
            raise Exception("Could not parse JWS header.")
        return header

    def _validate_header(self, header: dict):
        """ Validates the JWS header, throws if not ok """
        if not (header and isinstance(header, dict)):
            raise Exception("Invalid JWS header.")

        if not (
            header["alg"] == self.algorithm
            and header["b64"] is False
            and isinstance(header["crit"], list)
            and header["crit"].len() == 1
            and header["crit"][0] == "b64"
            and header.keys().len() == 3
        ):
            raise Exception(f"Invalid JWS header params for {self.signature_type}")

    def _create_jws(
        self, encoded_header: Union[str, bytes], verify_data: bytes
    ) -> bytes:
        """Compose JWS."""
        return (encoded_header + ".").encode("utf-8") + verify_data

    async def sign(self, verify_data: bytes, proof: dict):

        header = {"alg": self.algorithm, "b64": False, "crit": ["b64"]}
        encoded_header = str_to_b64(json.dumps(header), urlsafe=True, pad=False)

        data = self._create_jws(encoded_header, verify_data)
        signature = await self.key_pair.sign(data)

        encoded_signature = bytes_to_b64(signature, urlsafe=True, pad=False)

        proof["jws"] = str(encoded_header) + ".." + encoded_signature

        return proof

    async def verify_signature(
        self, verify_data: bytes, verification_method: dict, proof: dict
    ):

        if not (
            ("jws" in proof) and isinstance(proof["jws"], str) and ("." in proof["jws"])
        ):
            raise Exception('The proof does not contain a valid "jws" property.')

        encoded_header, payload, encoded_signature = proof["jws"].split(".")

        header = self._decode_header(encoded_header)

        self._validate_header(header)

        signature = b64_to_str(encoded_signature, urlsafe=True)
        data = self._create_jws(encoded_header, verify_data)

        return await self.key_pair.verify(data, signature)

    def assert_verification_method(self, verification_method: dict):
        if not jsonld.has_value(verification_method, "type", self.required_key_type):
            raise Exception(
                f"Invalid key type. The key type must be {self.required_key_type}"
            )

    async def get_verification_method(self, proof: dict, document_loader: callable):
        verification_method = await super(
            LinkedDataSignature, self
        ).get_verification_method(proof, document_loader)
        self.assert_verification_method(verification_method)
        return verification_method

    # async def match_proof(self, proof, document, purpose, document_loader):
    #   if not super(LinkedDataProof, self).match_proof(proof['type']):
    #     return False

    #   if not self.key:
    #     return True

    #   verification_method = proof['verificationMethod']

    #   if isinstance(verification_method, dict):
    #     return verification_method['id'] == self.key.id

    #  return verification_method == self.key.id
