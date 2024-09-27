"""DataIntegrity class."""

from ...core.profile import ProfileSession
from .cryptosuites import CRYPTOSUITES


class DataIntegrityManagerError(Exception):
    """Generic DataIntegrityManager Error."""


class DataIntegrityManager:
    """Class for managing data integrity proofs."""

    def __init__(self, session: ProfileSession):
        """Initialize the DataIntegrityManager."""
        self.session = session

    async def add_proof(self, document, options):
        """Data integrity add proof algorithm.

        https://www.w3.org/TR/vc-data-integrity/#add-proof.
        """

        # Instanciate a cryptosuite
        suite = CRYPTOSUITES[options["cryptosuite"]](session=self.session)

        # Capture existing proofs if any
        all_proofs = document.pop("proof", [])
        assert isinstance(all_proofs, list) or isinstance(all_proofs, dict)
        all_proofs = [all_proofs] if isinstance(all_proofs, dict) else all_proofs

        # Create secured document and create new proof
        secured_document = document.copy()
        secured_document["proof"] = all_proofs
        secured_document["proof"].append(await suite.create_proof(document, options))
        return secured_document

    async def verify_proof(self, secured_document):
        """Verify a proof attached to a secured document.

        https://www.w3.org/TR/vc-data-integrity/#verify-proof.
        """
        unsecured_document = secured_document.copy()
        all_proofs = unsecured_document.pop("proof")
        all_proofs = all_proofs if isinstance(all_proofs, list) else [all_proofs]
        verification_results = {}
        verification_results["verifiedDocument"] = unsecured_document
        verification_results["results"] = []
        for proof in all_proofs:
            try:
                self.assert_proof(proof)
                # Instanciate a cryptosuite
                suite = CRYPTOSUITES[proof["cryptosuite"]](session=self.session)
                input_document = unsecured_document.copy()
                input_document["proof"] = proof
                verification_result = await suite.verify_proof(input_document)
                verification_results["results"].append(verification_result)
            except AssertionError as err:
                verification_result = {
                    "verified": False,
                    "problemDetails": [{"type": "", "message": str(err)}],
                }
                verification_results["results"].append(verification_result)
        verification_results["verified"] = (
            True
            if all(result["verified"] for result in verification_results["results"])
            else False
        )
        return verification_results

    def assert_proof(self, proof):
        """Generic proof assertions for a data integrity proof."""
        assert proof["cryptosuite"] in CRYPTOSUITES, "Unsupported cryptosuite."
        assert proof["proofValue"], "Missing proof value."
        assert proof["proofPurpose"] in [
            "authentication",
            "assertionMethod",
        ], "Unknown proofPurpose."
