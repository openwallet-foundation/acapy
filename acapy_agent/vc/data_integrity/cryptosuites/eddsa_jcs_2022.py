"""EddsaJcs2022 cryptosuite."""

from datetime import datetime
from hashlib import sha256

import canonicaljson

from ....core.error import BaseError
from ....core.profile import ProfileSession
from ....utils.multiformats import multibase
from ....wallet.base import BaseWallet
from ....wallet.keys.manager import (
    MultikeyManager,
    key_type_from_multikey,
    multikey_to_verkey,
)
from ..errors import PROBLEM_DETAILS
from ..models.options import DataIntegrityProofOptions
from ..models.proof import DataIntegrityProof
from ..models.verification_response import DataIntegrityVerificationResult, ProblemDetails


class CryptosuiteError(BaseError):
    """Generic Cryptosuite Error."""


class EddsaJcs2022:
    """EddsaJcs2022 cryptosuite.

    https://www.w3.org/TR/vc-di-eddsa/#eddsa-jcs-2022.
    """

    def __init__(self, *, session: ProfileSession):
        """Create new EddsaJcs2022 Cryptosuite instance.

        Args:
            session: ProfileSession to use during crypto operations.

        """
        super().__init__()
        self.session = session
        self.wallet = session.inject(BaseWallet)
        self.key_manager = MultikeyManager(session)

    async def create_proof(
        self, unsecured_data_document: dict, options: DataIntegrityProofOptions
    ):
        """Create proof algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#create-proof-eddsa-jcs-2022.
        """
        proof = DataIntegrityProof.deserialize(options.serialize().copy())

        # Spec says to copy document context to the proof but it's unecessary IMO,
        # commenting out for the time being...

        # if '@context' in unsecured_data_document:
        #     proof['@context'] = unsecured_data_document['@context']

        proof_config = self.proof_configuration(proof)
        transformed_data = self.transformation(unsecured_data_document, options)
        hash_data = self.hashing(transformed_data, proof_config)
        proof_bytes = await self.proof_serialization(hash_data, options)

        proof.proof_value = multibase.encode(proof_bytes, "base58btc")

        return proof

    def proof_configuration(self, options: DataIntegrityProofOptions):
        """Proof configuration algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#proof-configuration-eddsa-jcs-2022.
        """
        proof_config = options
        assert proof_config.type == "DataIntegrityProof", (
            'Expected proof.type to be "DataIntegrityProof'
        )
        assert proof_config.cryptosuite == "eddsa-jcs-2022", (
            'Expected proof.cryptosuite to be "eddsa-jcs-2022'
        )

        if proof_config.created:
            assert datetime.fromisoformat(proof_config.created)

        if proof_config.expires:
            assert datetime.fromisoformat(proof_config.expires)

        return self._canonicalize(proof_config.serialize())

    def transformation(
        self, unsecured_document: dict, options: DataIntegrityProofOptions
    ):
        """Transformation algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#transformation-eddsa-jcs-2022.
        """
        assert options.type == "DataIntegrityProof", (
            "Expected proof.type to be `DataIntegrityProof`"
        )
        assert options.cryptosuite == "eddsa-jcs-2022", (
            "Expected proof.cryptosuite to be `eddsa-jcs-2022`"
        )

        return self._canonicalize(unsecured_document)

    def hashing(self, transformed_document: bytes, canonical_proof_config: bytes):
        """Hashing algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#hashing-eddsa-jcs-2022.
        """
        return (
            sha256(canonical_proof_config).digest()
            + sha256(transformed_document).digest()
        )

    async def proof_serialization(
        self, hash_data: bytes, options: DataIntegrityProofOptions
    ):
        """Proof Serialization Algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#proof-serialization-eddsa-jcs-2022.
        """
        # TODO encapsulate in a key manager method
        if options.verification_method.startswith("did:key:"):
            multikey = options.verification_method.split("#")[-1]
            key_info = await self.key_manager.from_multikey(multikey)

        else:
            key_info = await self.key_manager.from_kid(options.verification_method)

        return await self.wallet.sign_message(
            message=hash_data,
            from_verkey=multikey_to_verkey(key_info["multikey"]),
        )

    def _canonicalize(self, data: dict):
        """Json canonicalization."""
        return canonicaljson.encode_canonical_json(data)

    async def verify_proof(self, secured_document: dict):
        """Verify proof algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#verify-proof-eddsa-jcs-2022.
        """
        unsecured_document = secured_document.copy()
        proof = unsecured_document.pop("proof")
        proof_options = proof.copy()
        proof_bytes = multibase.decode(proof_options.pop("proofValue"))

        try:
            # Currently leaving context processing out of scope,
            # leaving code commented as it's technically an algorithm step.
            # Due to the cryptosuite being based on JSON canonicalization,
            # the integrity of the document is protected without RDF processing.

            # https://www.w3.org/TR/vc-data-integrity/#validating-contexts

            # assert secured_document['@context'] == proof_options['@context']
            # unsecured_document['@context'] = proof_options['@context']

            proof_options = DataIntegrityProofOptions.deserialize(proof_options)
            transformed_data = self.transformation(unsecured_document, proof_options)
            proof_config = self.proof_configuration(proof_options)
            hash_data = self.hashing(transformed_data, proof_config)
            verified = await self.proof_verification(
                hash_data, proof_bytes, proof_options
            )
            if not verified:
                raise CryptosuiteError("Invalid signature.")

        except CryptosuiteError as err:
            problem_detail = ProblemDetails.deserialize(
                PROBLEM_DETAILS["PROOF_VERIFICATION_ERROR"]
            )
            problem_detail.detail = str(err)
            return DataIntegrityVerificationResult(
                verified=False,
                proof=DataIntegrityProof.deserialize(proof),
                problem_details=[problem_detail],
            )

        return DataIntegrityVerificationResult(
            verified=True,
            proof=DataIntegrityProof.deserialize(proof),
            problem_details=[],
        )

    async def proof_verification(
        self, hash_data: bytes, proof_bytes: bytes, options: DataIntegrityProofOptions
    ):
        """Proof verification algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#proof-verification-eddsa-jcs-2022.
        """
        multikey = await MultikeyManager(
            self.session
        ).resolve_multikey_from_verification_method_id(options.verification_method)
        verkey = multikey_to_verkey(multikey)
        key_type = key_type_from_multikey(multikey)
        return await self.wallet.verify_message(
            message=hash_data,
            signature=proof_bytes,
            from_verkey=verkey,
            key_type=key_type,
        )
