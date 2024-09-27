"""DataIntegrity class."""

from ...core.profile import ProfileSession
from .cryptosuites import CRYPTOSUITES
from .models.proof import DataIntegrityProof
from .models.options import DataIntegrityProofOptions
from .models.verification_response import (
    DataIntegrityVerificationResponse,
    DataIntegrityVerificationResult,
    ProblemDetails,
)
from .errors import PROBLEM_DETAILS


class DataIntegrityManagerError(Exception):
    """Generic DataIntegrityManager Error."""


class DataIntegrityManager:
    """Class for managing data integrity proofs."""

    def __init__(self, session: ProfileSession):
        """Initialize the DataIntegrityManager."""
        self.session = session

    async def add_proof(self, document: dict, options: DataIntegrityProofOptions):
        """Data integrity add proof algorithm.

        https://www.w3.org/TR/vc-data-integrity/#add-proof.
        """

        # Instanciate a cryptosuite
        suite = CRYPTOSUITES[options.cryptosuite](session=self.session)

        # Capture existing proofs if any
        all_proofs = document.pop("proof", [])
        assert isinstance(all_proofs, list) or isinstance(all_proofs, dict)
        all_proofs = [all_proofs] if isinstance(all_proofs, dict) else all_proofs

        # Create secured document and create new proof
        secured_document = document.copy()
        secured_document["proof"] = all_proofs
        proof = await suite.create_proof(document, options)
        secured_document["proof"].append(proof.serialize())
        return secured_document

    async def verify_proof(self, secured_document: dict):
        """Verify a proof attached to a secured document.

        https://www.w3.org/TR/vc-data-integrity/#verify-proof.
        """
        unsecured_document = secured_document.copy()
        all_proofs = unsecured_document.pop("proof")
        all_proofs = all_proofs if isinstance(all_proofs, list) else [all_proofs]
        verification_results = []
        for proof in all_proofs:
            try:
                proof = DataIntegrityProof.deserialize(proof)
                self.assert_proof(proof)
                # Instanciate a cryptosuite
                suite = CRYPTOSUITES[proof.cryptosuite](session=self.session)
                input_document = unsecured_document.copy()
                input_document["proof"] = proof.serialize()
                verification_result = await suite.verify_proof(input_document)
            except AssertionError as err:
                problem_detail = ProblemDetails.deserialize(
                    PROBLEM_DETAILS["PROOF_VERIFICATION_ERROR"]
                )
                problem_detail.detail = str(err)
                verification_result = DataIntegrityVerificationResult(
                    verified=False,
                    proof=proof,
                    problem_details=[problem_detail],
                )
            verification_results.append(verification_result)
        return DataIntegrityVerificationResponse(
            verified=(
                True if all(result.verified for result in verification_results) else False
            ),
            verified_document=unsecured_document,
            results=verification_results,
        )

    def assert_proof(self, proof: DataIntegrityProof):
        """Generic proof assertions for a data integrity proof."""
        assert proof.cryptosuite in CRYPTOSUITES, "Unsupported cryptosuite."
        assert proof.proof_value, "Missing proof value."
        assert proof.proof_purpose in [
            "authentication",
            "assertionMethod",
        ], "Unknown proofPurpose."
