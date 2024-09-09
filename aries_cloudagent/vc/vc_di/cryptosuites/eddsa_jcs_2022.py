"""EddsaJcs2022 cryptosuite."""

from hashlib import sha256
import canonicaljson
import nacl

from ....wallet.base import BaseWallet
from ....utils.multiformats import multibase
from ....core.profile import Profile
from .. import DataIntegrityProofException


class EddsaJcs2022:
    """EddsaJcs2022 suite."""

    def __init__(self, *, profile: Profile):
        """Create new EddsaJcs2022 Cryptosuite instance.

        https://www.w3.org/TR/vc-di-eddsa/#eddsa-rdfc-2022

        Args:
            profile: Key profile to use.

        """
        super().__init__()
        self.profile = profile

    async def _serialization(self, hash_data, options):
        """Data Integrity Proof Serialization Algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#proof-serialization-eddsa-jcs-2022

        """
        async with self.profile.session() as session:
            did_info = await session.inject(BaseWallet).get_local_did(
                options["verificationMethod"].split("#")[0]
            )
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
        proof_bytes = await wallet.sign_message(
            message=hash_data,
            from_verkey=did_info.verkey,
        )
        return proof_bytes

    async def add_proof(self, document, proof_options):
        """Data Integrity Add Proof Algorithm.

        https://www.w3.org/TR/vc-data-integrity/#add-proof

        Args:
            document: The data to sign.
            proof_options: The proof options.

        Returns:
            secured_document: The document with a new proof attached

        """

        existing_proof = document.pop("proof", [])
        assert isinstance(existing_proof, list) or isinstance(existing_proof, dict)
        existing_proof = (
            [existing_proof] if isinstance(existing_proof, dict) else existing_proof
        )

        assert proof_options["type"] == "DataIntegrityProof"
        assert proof_options["cryptosuite"] == "eddsa-jcs-2022"
        assert proof_options["proofPurpose"]
        assert proof_options["verificationMethod"]

        try:
            hash_data = (
                sha256(canonicaljson.encode_canonical_json(document)).digest()
                + sha256(canonicaljson.encode_canonical_json(proof_options)).digest()
            )
            proof_bytes = await self._serialization(hash_data, proof_options)

            proof = proof_options.copy()
            proof["proofValue"] = multibase.encode(proof_bytes, "base58btc")

            secured_document = document.copy()
            secured_document["proof"] = existing_proof
            secured_document["proof"].append(proof)

            return secured_document
        except Exception:
            raise DataIntegrityProofException()

    async def verify_proof(self, unsecured_document, proof):
        """Data Integrity Verify Proof Algorithm.

        https://www.w3.org/TR/vc-data-integrity/#verify-proof

        Args:
            unsecured_document: The data to check.
            proof: The proof.

        Returns:
            verification_response: Whether the signature is valid for the data

        """
        try:
            assert proof["type"] == "DataIntegrityProof"
            assert proof["cryptosuite"] == "eddsa-jcs-2022"
            assert proof["proofPurpose"]
            assert proof["proofValue"]
            assert proof["verificationMethod"]

            proof_options = proof.copy()
            proof_value = proof_options.pop("proofValue")
            proof_bytes = multibase.decode(proof_value)

            hash_data = (
                sha256(canonicaljson.encode_canonical_json(unsecured_document)).digest()
                + sha256(canonicaljson.encode_canonical_json(proof_options)).digest()
            )
            verification_method = proof["verificationMethod"]
            did = verification_method.split("#")[0]
            if did.split(":")[1] == "key":
                pub_key = multibase.decode(did.split(":")[-1])
                public_key_bytes = bytes(bytearray(pub_key)[2:])
            try:
                nacl.bindings.crypto_sign_open(proof_bytes + hash_data, public_key_bytes)
                return True
            except nacl.exceptions.BadSignatureError:
                return False
        except Exception:
            raise DataIntegrityProofException()
