"""Ed25519Signature2018 suite."""

from datetime import datetime
from typing import Union, List

from multiformats import multibase

from .linked_data_signature import LinkedDataSignature
from ..crypto import _KeyPair as KeyPair
from ..document_loader import DocumentLoaderMethod
from ..error import LinkedDataProofException


class Ed25519Signature2020(LinkedDataSignature):
    """Ed25519Signature2020 suite."""

    signature_type = "Ed25519Signature2020"

    def __init__(
        self,
        *,
        key_pair: KeyPair,
        proof: dict = None,
        verification_method: str = None,
        date: Union[datetime, str] = None,
    ):
        """Create new Ed25519Signature2020 instance.

        Args:
            key_pair (KeyPair): Key pair to use. Must provide EdDSA signatures
            proof (dict, optional): A JSON-LD document with options to use for the
                `proof` node (e.g. any other custom fields can be provided here
                using a context different from security-v2).
            verification_method (str, optional): A key id URL to the paired public key.
            date (datetime, optional): Signing date to use.
        """
        super().__init__(
            signature_type=Ed25519Signature2020.signature_type,
            verification_method=verification_method,
            proof=proof,
            date=date,
        )
        self.key_pair = key_pair

    async def sign(self, *, verify_data: bytes, proof: dict) -> dict:
        """Sign the data and add it to the proof.

        Args:
            verify_data (List[bytes]): The data to sign.
            proof (dict): The proof to add the signature to

        Returns:
            dict: The proof object with the added signature

        """
        signature = await self.key_pair.sign(verify_data)

        proof["proofValue"] = multibase.encode(signature, "base58btc")

        return proof

    async def verify_signature(
        self,
        *,
        verify_data: List[bytes],
        verification_method: dict,
        document: dict,
        proof: dict,
        document_loader: DocumentLoaderMethod,
    ) -> bool:
        """Verify the data against the proof.

        Args:
            verify_data (bytes): The data to check
            verification_method (dict): The verification method to use.
            document (dict): The document the verify data is derived for as extra context
            proof (dict): The proof to check
            document_loader (DocumentLoader): Document loader used for resolving

        Returns:
            bool: Whether the signature is valid for the data

        """

        if not (isinstance(proof.get("proofValue"), str)):
            raise LinkedDataProofException(
                'The proof does not contain a valid "proofValue" property.'
            )

        signature = multibase.decode(proof["proofValue"])

        # If the key pair has no public key yet, create a new key pair
        # from the verification method. We don't want to overwrite data
        # on the original key pair
        key_pair = self.key_pair
        if not key_pair.has_public_key:
            key_pair = key_pair.from_verification_method(verification_method)

        return await key_pair.verify(verify_data, signature)
