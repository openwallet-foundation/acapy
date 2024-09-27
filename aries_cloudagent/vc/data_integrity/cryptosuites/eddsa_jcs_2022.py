"""EddsaJcs2022 cryptosuite."""

from hashlib import sha256
import canonicaljson

from ....wallet.base import BaseWallet
from ....wallet.keys.manager import MultikeyManager
from ....utils.multiformats import multibase
from ....core.profile import ProfileSession
from ....resolver.did_resolver import DIDResolver
from ..errors import PROBLEM_DETAILS


class CryptosuiteError(Exception):
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

    async def create_proof(self, unsecured_data_document: dict, options: dict):
        """Create proof algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#create-proof-eddsa-jcs-2022.
        """
        proof = options.copy()

        # Spec says to copy document context to the proof but it's unecessary IMO,
        # commenting out for the time being...

        # if '@context' in unsecured_data_document:
        #     proof['@context'] = unsecured_data_document['@context']

        proof_config = self.proof_configuration(proof)
        transformed_data = self.transformation(unsecured_data_document, options)
        hash_data = self.hashing(transformed_data, proof_config)
        proof_bytes = await self.proof_serialization(hash_data, options)

        proof["proofValue"] = multibase.encode(proof_bytes, "base58btc")

        return proof

    def proof_configuration(self, options: dict):
        """Proof configuration algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#proof-configuration-eddsa-jcs-2022.
        """
        proof_config = options.copy()

        assert (
            proof_config["type"] == "DataIntegrityProof"
        ), 'Expected proof.type to be "DataIntegrityProof'
        assert (
            proof_config["cryptosuite"] == "eddsa-jcs-2022"
        ), 'Expected proof.cryptosuite to be "eddsa-jcs-2022'

        if "created" in proof_config:
            # TODO assert proper [XMLSCHEMA11-2] dateTimeStamp string
            assert proof_config[
                "created"
            ], "Expected proof.created to be a [XMLSCHEMA11-2] dateTimeStamp string."

        if "expires" in proof_config:
            # TODO assert proper [XMLSCHEMA11-2] dateTimeStamp string
            assert proof_config[
                "expires"
            ], "Expected proof.expires to be a [XMLSCHEMA11-2] dateTimeStamp string."

        return self._canonicalize(proof_config)

    def transformation(self, unsecured_document: dict, options: dict):
        """Transformation algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#transformation-eddsa-jcs-2022.
        """
        assert (
            options["type"] == "DataIntegrityProof"
        ), "Expected proof.type to be `DataIntegrityProof`"
        assert (
            options["cryptosuite"] == "eddsa-jcs-2022"
        ), "Expected proof.cryptosuite to be `eddsa-jcs-2022`"

        return self._canonicalize(unsecured_document)

    def hashing(self, transformed_document, canonical_proof_config):
        """Hashing algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#hashing-eddsa-jcs-2022.
        """
        return (
            sha256(canonical_proof_config).digest()
            + sha256(transformed_document).digest()
        )

    async def proof_serialization(self, hash_data: bytes, options: dict):
        """Proof Serialization Algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#proof-serialization-eddsa-jcs-2022.
        """
        # If the verification method is a did:key: URI,
        # we derive the signing key from a multikey value
        if options["verificationMethod"].startswith("did:key:"):
            multikey = options["verificationMethod"].split("#")[-1]
            key_info = await self.key_manager.from_multikey(multikey)

        # Otherwise we derive the signing key from a kid
        else:
            key_info = await self.key_manager.from_kid(options["verificationMethod"])

        return await self.wallet.sign_message(
            message=hash_data,
            from_verkey=self.key_manager._multikey_to_verkey(key_info["multikey"]),
        )

    def _canonicalize(self, data: dict):
        """Json canonicalization."""
        return canonicaljson.encode_canonical_json(data)

    async def _get_multikey(self, kid: str):
        """Derive a multikey from the verification method."""

        # If verification method is a did:key URI,
        # we derive the multikey directly from the value.
        if kid.startswith("did:key:"):
            return kid.split("#")[-1]

        # Otherwise we resolve the verification method and extract the multikey.
        else:
            verification_method = await DIDResolver().dereference(
                profile=self.session.profile, did_url=kid
            )
            assert (
                verification_method["type"] == "Multikey"
            ), "Expected Multikey verificationMethod type"

            return verification_method["publicKeyMultibase"]

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

            transformed_data = self.transformation(unsecured_document, proof_options)
            proof_config = self.proof_configuration(proof_options)
            hash_data = self.hashing(transformed_data, proof_config)
            if not await self.proof_verification(hash_data, proof_bytes, proof_options):
                raise CryptosuiteError("Invalid signature.")

        except (AssertionError, CryptosuiteError) as err:
            problem_detail = PROBLEM_DETAILS["PROOF_VERIFICATION_ERROR"] | {
                "message": str(err)
            }
            return {"verified": False, "proof": proof, "problemDetails": [problem_detail]}

        return {"verified": True, "proof": proof, "problemDetails": []}

    async def proof_verification(
        self, hash_data: bytes, proof_bytes: bytes, options: dict
    ):
        """Proof verification algorithm.

        https://www.w3.org/TR/vc-di-eddsa/#proof-verification-eddsa-jcs-2022.
        """
        multikey = await self._get_multikey(options["verificationMethod"])
        return await self.wallet.verify_message(
            message=hash_data,
            signature=proof_bytes,
            from_verkey=self.key_manager._multikey_to_verkey(multikey),
            key_type=self.key_manager.key_type_from_multikey(multikey),
        )
