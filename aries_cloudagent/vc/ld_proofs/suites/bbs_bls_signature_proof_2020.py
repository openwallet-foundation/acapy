"""BbsBlsSignatureProof2020 class."""

import re

from os import urandom
from typing import List

from pyld import jsonld

from .bbs_bls_signature_2020_base import BbsBlsSignature2020Base

if BbsBlsSignature2020Base.BBS_SUPPORTED:
    from ursa_bbs_signatures import (
        create_proof as bls_create_proof,
        verify_proof as bls_verify_proof,
        CreateProofRequest,
        VerifyProofRequest,
        get_total_message_count,
        ProofMessage,
        BlsKeyPair,
        ProofMessageType,
    )

from ....utils.dependencies import assert_ursa_bbs_signatures_installed
from ....wallet.util import b64_to_bytes, bytes_to_b64

from ..crypto import _KeyPair as KeyPair
from ..error import LinkedDataProofException
from ..validation_result import ProofResult
from ..document_loader import DocumentLoaderMethod
from ..purposes import _ProofPurpose as ProofPurpose

from .bbs_bls_signature_2020 import BbsBlsSignature2020
from .linked_data_proof import DeriveProofResult


class BbsBlsSignatureProof2020(BbsBlsSignature2020Base):
    """BbsBlsSignatureProof2020 class."""

    signature_type = "BbsBlsSignatureProof2020"

    def __init__(
        self,
        *,
        key_pair: KeyPair,
    ):
        """Create new BbsBlsSignatureProof2020 instance.

        Args:
            key_pair (KeyPair): Key pair to use. Must provide BBS signatures

        """
        super().__init__(
            signature_type=BbsBlsSignatureProof2020.signature_type,
            supported_derive_proof_types=(
                BbsBlsSignatureProof2020.supported_derive_proof_types
            ),
        )
        self.key_pair = key_pair
        self.mapped_derived_proof_type = "BbsBlsSignature2020"

    async def derive_proof(
        self,
        *,
        proof: dict,
        document: dict,
        reveal_document: dict,
        document_loader: DocumentLoaderMethod,
        nonce: bytes = None,
    ):
        """Derive proof for document, return dict with derived document and proof."""
        assert_ursa_bbs_signatures_installed()

        # Validate that the input proof document has a proof compatible with this suite
        if proof.get("type") not in self.supported_derive_proof_types:
            raise LinkedDataProofException(
                f"Proof document proof incompatible, expected proof types of"
                f" {self.supported_derive_proof_types}, received " + proof["type"]
            )

        # Extract the BBS signature from the input proof
        signature = b64_to_bytes(proof["proofValue"])

        # Initialize the BBS signature suite
        # This is used for creating the input document verification data
        # NOTE: both suite._create_verify_xxx_data and self._create_verify_xxx_data
        # are used in this file. They have small changes in behavior
        suite = BbsBlsSignature2020(key_pair=self.key_pair)

        # Initialize the derived proof
        derived_proof = self.proof.copy() if self.proof else {}

        # Ensure proof type is set
        derived_proof["type"] = self.signature_type

        # Get the input document and proof statements
        document_statements = suite._create_verify_document_data(
            document=document, document_loader=document_loader
        )
        proof_statements = suite._create_verify_proof_data(
            proof=proof, document=document, document_loader=document_loader
        )

        # Transform any blank node identifiers for the input
        # document statements into actual node identifiers
        # e.g _:c14n0 => urn:bnid:_:c14n0
        transformed_input_document_statements = (
            self._transform_blank_node_ids_into_placeholder_node_ids(
                document_statements
            )
        )

        # Transform the resulting RDF statements back into JSON-LD
        compact_input_proof_document = jsonld.from_rdf(
            "\n".join(transformed_input_document_statements)
        )

        # Frame the result to create the reveal document result
        reveal_document_result = jsonld.frame(
            compact_input_proof_document,
            reveal_document,
            {"documentLoader": document_loader},
        )

        # Canonicalize the resulting reveal document
        reveal_document_statements = suite._create_verify_document_data(
            document=reveal_document_result, document_loader=document_loader
        )

        # Get the indices of the revealed statements from the transformed input document
        # offset by the number of proof statements
        number_of_proof_statements = len(proof_statements)

        # Always reveal all the statements associated to the original proof
        # these are always the first statements in the normalized form
        proof_reveal_indices = [indice for indice in range(number_of_proof_statements)]

        # Reveal the statements indicated from the reveal document
        document_reveal_indices = list(
            map(
                lambda reveal_statement: transformed_input_document_statements.index(
                    reveal_statement
                )
                + number_of_proof_statements,
                reveal_document_statements,
            )
        )

        # Check there is not a mismatch
        if len(document_reveal_indices) != len(reveal_document_statements):
            raise LinkedDataProofException(
                "Some statements in the reveal document not found in original proof"
            )

        # Combine all indices to get the resulting list of revealed indices
        reveal_indices = [*proof_reveal_indices, *document_reveal_indices]

        # Create a nonce if one is not supplied
        nonce = nonce or urandom(50)

        derived_proof["nonce"] = bytes_to_b64(
            nonce, urlsafe=False, pad=True, encoding="utf-8"
        )

        # Combine all the input statements that were originally signed
        # NOTE: we use plain strings here as input for the bbs lib.
        # the MATTR lib uses bytes, but the wrapper expects strings
        # it also works if we pass bytes as input
        all_input_statements = [*proof_statements, *document_statements]

        # Fetch the verification method
        verification_method = self._get_verification_method(
            proof=proof, document_loader=document_loader
        )

        # Create key pair from public key in verification method
        key_pair = self.key_pair.from_verification_method(verification_method)

        # Get the proof messages (revealed or not)
        proof_messages = []
        for input_statement_index in range(len(all_input_statements)):
            # if input statement index in revealed messages indexes use revealed type
            # otherwise use blinding
            proof_type = (
                ProofMessageType.Revealed
                if input_statement_index in reveal_indices
                else ProofMessageType.HiddenProofSpecificBlinding
            )
            proof_messages.append(
                ProofMessage(
                    message=all_input_statements[input_statement_index],
                    proof_type=proof_type,
                )
            )

        # get bbs key from bls key pair
        bbs_public_key = BlsKeyPair(public_key=key_pair.public_key).get_bbs_key(
            len(all_input_statements)
        )

        # Compute the proof
        proof_request = CreateProofRequest(
            public_key=bbs_public_key,
            messages=proof_messages,
            signature=signature,
            nonce=nonce,
        )

        output_proof = bls_create_proof(proof_request)

        # Set the proof value on the derived proof
        derived_proof["proofValue"] = bytes_to_b64(
            output_proof, urlsafe=False, pad=True, encoding="utf-8"
        )

        # Set the relevant proof elements on the derived proof from the input proof
        derived_proof["verificationMethod"] = proof["verificationMethod"]
        derived_proof["proofPurpose"] = proof["proofPurpose"]
        derived_proof["created"] = proof["created"]

        return DeriveProofResult(
            document={**reveal_document_result}, proof=derived_proof
        )

    async def verify_proof(
        self,
        *,
        proof: dict,
        document: dict,
        purpose: ProofPurpose,
        document_loader: DocumentLoaderMethod,
    ) -> ProofResult:
        """Verify proof against document and proof purpose."""
        assert_ursa_bbs_signatures_installed()
        try:
            proof["type"] = self.mapped_derived_proof_type

            # Get the proof and document statements
            proof_statements = self._create_verify_proof_data(
                proof=proof, document=document, document_loader=document_loader
            )
            document_statements = self._create_verify_document_data(
                document=document, document_loader=document_loader
            )

            # Transform the blank node identifier placeholders for the document statements
            # back into actual blank node identifiers
            transformed_document_statements = (
                self._transform_placeholder_node_ids_into_blank_node_ids(
                    document_statements
                )
            )

            # Combine all the statements to be verified
            # NOTE: we use plain strings here as input for the bbs lib.
            # the MATTR lib uses bytes, but the wrapper expects strings
            # it also works if we pass bytes as input
            statements_to_verify = [*proof_statements, *transformed_document_statements]

            # Fetch the verification method
            verification_method = self._get_verification_method(
                proof=proof, document_loader=document_loader
            )

            key_pair = self.key_pair.from_verification_method(verification_method)
            proof_bytes = b64_to_bytes(proof["proofValue"])

            total_message_count = get_total_message_count(proof_bytes)

            # get bbs key from bls key pair
            bbs_public_key = BlsKeyPair(public_key=key_pair.public_key).get_bbs_key(
                total_message_count
            )

            # verify dervied proof
            verify_request = VerifyProofRequest(
                public_key=bbs_public_key,
                proof=proof_bytes,
                messages=statements_to_verify,
                nonce=b64_to_bytes(proof["nonce"]),
            )

            verified = bls_verify_proof(verify_request)

            if not verified:
                raise LinkedDataProofException(
                    f"Invalid signature on document {document}"
                )

            purpose_result = purpose.validate(
                proof=proof,
                document=document,
                suite=self,
                verification_method=verification_method,
                document_loader=document_loader,
            )

            if not purpose_result.valid:
                return ProofResult(
                    verified=False,
                    purpose_result=purpose_result,
                    error=purpose_result.error,
                )

            return ProofResult(verified=True, purpose_result=purpose_result)
        except Exception as err:
            return ProofResult(verified=False, error=err)

    def _canonize_proof(
        self, *, proof: dict, document: dict, document_loader: DocumentLoaderMethod
    ):
        """Canonize proof dictionary. Removes proofValue."""
        proof = {**proof, "@context": document.get("@context") or self._default_proof}

        proof.pop("proofValue", None)
        proof.pop("nonce", None)

        return self._canonize(input=proof, document_loader=document_loader)

    def _transform_blank_node_ids_into_placeholder_node_ids(
        self,
        statements: List[str],
    ) -> List[str]:
        """Transform blank node identifiers for the input into actual node identifiers.

        e.g _:c14n0 => urn:bnid:_:c14n0

        Args:
            statements (List[str]): List with possible blank node identifiers

        Returns:
            List[str]: List of transformed output statements

        """
        # replace all occurrences of _:c14nX with <urn:bnid:_:c14nX>
        transformed_statements = [
            re.sub(r"(_:c14n[0-9]+)", r"<urn:bnid:\1>", statement)
            for statement in statements
        ]

        return transformed_statements

    def _transform_placeholder_node_ids_into_blank_node_ids(
        self,
        statements: List[str],
    ) -> List[str]:
        """Transform the blank node placeholder identifiers back into actual blank nodes.

        e.g urn:bnid:_:c14n0 => _:c14n0

        Args:
            statements (List[str]): List with possible placeholder node identifiers

        Returns:
            List[str]: List of transformed output statements

        """
        # replace all occurrences of <urn:bnid:_:c14nX> with _:c14nX
        transformed_statements = [
            re.sub(r"<urn:bnid:(_:c14n[0-9]+)>", r"\1", statement)
            for statement in statements
        ]

        return transformed_statements

    supported_derive_proof_types = [
        "BbsBlsSignature2020",
        "sec:BbsBlsSignature2020",
        "https://w3id.org/security#BbsBlsSignature2020",
    ]
