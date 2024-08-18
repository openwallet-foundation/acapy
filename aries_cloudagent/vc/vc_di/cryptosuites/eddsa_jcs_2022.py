"""EddsaJcs2022 cryptosuite."""

from hashlib import sha256
import canonicaljson
import nacl

from ....wallet.base import BaseWallet
from ....utils.multiformats import multibase
from ....core.profile import Profile
from .. import DataIntegrityProofException
from .. import DataIntegrityProofException
# from . import CONTEXTS

CONTEXTS = {
    'data-integrity-v2': 'https://w3id.org/security/data-integrity/v2'
}

class EddsaJcs2022:
    """EddsaJcs2022 suite."""

    def __init__(self, *, profile: Profile):
        """Create new EddsaJcs2022 instance.

        Args:
            profile: Key profile to use.
        """
        super().__init__()
        self.profile = profile
        
    def _proof_configuration(self, options):
        # https://www.w3.org/TR/vc-di-eddsa/#proof-configuration-eddsa-jcs-2022
        
        proof_config = options.copy()
        assert proof_config["type"] == "DataIntegrityProof"
        assert proof_config["cryptosuite"] == "eddsa-jcs-2022"

        if 'created' in proof_config:
            pass
        
        canonical_proof_config = canonicaljson.encode_canonical_json(proof_config)
        
        return canonical_proof_config
        
    def _transformation(self, unsecured_document, options):
        # https://www.w3.org/TR/vc-di-eddsa/#transformation-eddsa-jcs-2022
        assert options["type"] == "DataIntegrityProof"
        assert options["cryptosuite"] == "eddsa-jcs-2022"
        
        canonical_document = canonicaljson.encode_canonical_json(unsecured_document)
        
        return canonical_document
        
    def _hashing(self, transformed_document, proof_config):
        # https://www.w3.org/TR/vc-di-eddsa/#hashing-eddsa-jcs-2022
        transformed_document_hash = sha256(transformed_document).digest()
        proof_config_hash = sha256(proof_config).digest()
        hash_data = proof_config_hash+transformed_document_hash
        return hash_data
        
    async def _serialization(self, hash_data, options):
        # https://www.w3.org/TR/vc-di-eddsa/#proof-serialization-eddsa-jcs-2022
        async with self.profile.session() as session:
            did_info = await session.inject(BaseWallet).get_local_did(
                options['verificationMethod'].split('#')[0]
            )
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
        proof_bytes = await wallet.sign_message(
            message=hash_data,
            from_verkey=did_info.verkey,
        )
        return proof_bytes

    async def _create_proof(self, unsecured_document, options):
        """https://www.w3.org/TR/vc-di-eddsa/#create-proof-eddsa-jcs-2022"""
        
        proof = options.copy()
        # if '@context' in unsecured_document:
        #     proof = {"@context": unsecured_document['@context'], **proof}
        
        proof_config = self._proof_configuration(proof)
        transformed_document = self._transformation(unsecured_document, options)
        hash_data = self._hashing(transformed_document, proof_config)
        proof_bytes = await self._serialization(hash_data, options)
        proof['proofValue'] = multibase.encode(proof_bytes, "base58btc")
        return proof

    async def add_proof(self, input_document, options):
        # https://www.w3.org/TR/vc-data-integrity/#add-proof
        if '@context' not in input_document:
            context = [CONTEXTS['data-integrity-v2']]
        elif CONTEXTS['data-integrity-v2'] not in input_document['@context']:
            context = input_document['@context']+[CONTEXTS['data-integrity-v2']]
            
        # Force @context as the first key in our dictionary
        input_document = {"@context": context, **input_document}
            
        proof = input_document.pop('proof', None)
        all_proofs = []
        if isinstance(proof, list):
            all_proofs = proof
        if isinstance(proof, dict):
            all_proofs.append(proof)
        
        # try:
        proof = await self._create_proof(input_document, options)
        assert proof['type']
        assert proof['proofPurpose']
        assert proof['verificationMethod']
        if 'domain' in options and options['domain']:
            assert options['domain'] == proof['domain']
        if 'challenge' in options and options['challenge']:
            assert options['challenge'] == proof['challenge']
            
        all_proofs.append(proof)
            
        secured_data_document = input_document.copy()
        secured_data_document['proof'] = all_proofs

        return secured_data_document
        # except:
        #     raise DataIntegrityProofException()
        
    async def _proof_verification(self, hash_data, proof_bytes, options):
        verification_method = options['verificationMethod']
        if verification_method.split(":")[1] == "key":
            pub_key = multibase.decode(verification_method.split(":")[2])
            public_key_bytes = bytes(bytearray(pub_key)[2:])
        try:
            nacl.bindings.crypto_sign_open(proof_bytes + hash_data, public_key_bytes)
            return True
        except nacl.exceptions.BadSignatureError:
            return False
        
    async def _parse_json_bytes(self, json_bytes):
        return json_bytes.decode()

    async def verify_proof(
        self, 
        unsecured_document,
        proof
    ):
        """https://www.w3.org/TR/vc-data-integrity/#verify-proof"""
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
        proof_options = proof.copy()
        proof_value = proof_options.pop('proofValue', None)
        proof_bytes = multibase.decode(proof_value)
        if '@context' in proof_options:
            try:
                assert proof_options['@context'] == unsecured_document['@context']
            except:
                verification_result = {
                    'verified': False,
                    'verifiedDocument': None
                }
                return verification_result
        transformed_data = self._transformation(unsecured_document, proof_options)
        proof_config = self._proof_configuration(proof_options)
        hash_data = self._hashing(transformed_data, proof_config)
        verified = self._proof_verification(hash_data, proof_bytes, proof_config)
        verification_result = {
            'verified': verified,
            'verifiedDocument': unsecured_document
        }
        return verification_result

    async def verify_secured_document(
        self, 
        secured_document
    ):
        unsecured_document = secured_document.copy()
        proofs = unsecured_document.pop('proof', None)
        proofs = [proofs] if isinstance(proofs, dict) else proofs
        for proof in proofs:
            verification_result = self.verify_proof(unsecured_document, proof)