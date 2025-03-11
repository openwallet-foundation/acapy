"""DataIntegrity class."""

from datetime import datetime

from ...core.error import BaseError
from ...core.profile import ProfileSession
from ...resolver.base import DIDNotFound
from .cryptosuites import EddsaJcs2022
from .errors import PROBLEM_DETAILS
from .models.options import DataIntegrityProofOptions
from .models.proof import DataIntegrityProof
from .models.verification_response import (
    DataIntegrityVerificationResponse,
    DataIntegrityVerificationResult,
    ProblemDetails,
)

CRYPTOSUITES = {
    "eddsa-jcs-2022": EddsaJcs2022,
}

PROOF_TYPES = ["DataIntegrityProof"]

PROOF_PURPOSES = [
    "authentication",
    "assertionMethod",
]


class DataIntegrityManagerError(BaseError):
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
        self.validate_proof_options(options)
        suite = self.select_suite(options)

        # Capture existing proofs if any
        all_proofs = document.pop("proof", [])
        if not isinstance(all_proofs, list) and not isinstance(all_proofs, dict):
            raise DataIntegrityManagerError("Expected proof to be a list or an object.")

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
            proof_options = proof.copy()
            proof_options.pop("proofValue")
            proof_options = DataIntegrityProofOptions.deserialize(proof_options)
            try:
                self.validate_proof_options(proof_options)
                suite = self.select_suite(proof_options)
                input_document = unsecured_document.copy()
                input_document["proof"] = proof
                verification_result = await suite.verify_proof(input_document)

            except (DataIntegrityManagerError, DIDNotFound) as err:
                problem_detail = ProblemDetails.deserialize(
                    PROBLEM_DETAILS["PROOF_VERIFICATION_ERROR"]
                )
                problem_detail.detail = str(err)
                verification_result = DataIntegrityVerificationResult(
                    verified=False,
                    proof=DataIntegrityProof.deserialize(proof),
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

    def select_suite(self, options: DataIntegrityProofOptions):
        """Instanciate a cryptographic suite.

        https://www.w3.org/TR/vc-data-integrity/#cryptographic-suites.
        """
        if options.type == "DataIntegrityProof":
            suite = CRYPTOSUITES[options.cryptosuite](session=self.session)

        elif options.type in PROOF_TYPES:
            # TODO add support for Ed25519Signature2020
            pass

        else:
            raise DataIntegrityManagerError(f"Unsupported proof type {options.type}")
        return suite

    def validate_proof_options(self, proof_options: DataIntegrityProofOptions):
        """Generic proof assertions for a data integrity proof options."""
        if proof_options.created:
            try:
                datetime.fromisoformat(proof_options.created)
            except ValueError:
                raise DataIntegrityManagerError(
                    f"Invalid proof creation datetime format {proof_options.created}"
                )
        if proof_options.expires:
            try:
                datetime.fromisoformat(proof_options.expires)
            except ValueError:
                raise DataIntegrityManagerError(
                    f"Invalid proof expiration datetime format {proof_options.expires}"
                )
        if proof_options.type not in PROOF_TYPES:
            raise DataIntegrityManagerError(
                f"Unsupported proof type {proof_options.type}"
            )
        if proof_options.type == "DataIntegrityProof":
            if not proof_options.cryptosuite:
                raise DataIntegrityManagerError(
                    "DataIntegrityProof must specify a cryptosuite."
                )
            if proof_options.cryptosuite not in CRYPTOSUITES:
                raise DataIntegrityManagerError(
                    f"Unsupported cryptosuite {proof_options.cryptosuite}"
                )
        if proof_options.proof_purpose not in PROOF_PURPOSES:
            raise DataIntegrityManagerError(
                f"Unsupported proof purpose {proof_options.proof_purpose}"
            )
