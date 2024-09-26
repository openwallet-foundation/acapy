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
        """Data integrity add proof algorithm
        https://www.w3.org/TR/vc-data-integrity/#add-proof
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
        unsecured_document = secured_document.copy()
        all_proofs = unsecured_document.pop("proof")
        all_proofs = [all_proofs] if isinstance(all_proofs, dict) else all_proofs
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
            except AssertionError as err:
                verification_result = {
                    "verified": False,
                    "problemDetails": [{"type": "", "message": str(err)}],
                }
                verification_result["proof"] = proof
                verification_results["results"].append(verification_result)
        verification_results["verified"] = (
            True
            if all(result["verified"] for result in verification_results["results"])
            else False
        )
        return verification_results

    def assert_proof(self, proof):
        assert proof["cryptosuite"] in CRYPTOSUITES, "Unsupported cryptosuite."
        assert proof["proofValue"], "Missing proof value."
        assert proof["proofPurpose"] in [
            "authentication",
            "assertionMethod",
        ], "Unknown proofPurpose."

    # def verify_proof(self, secured_document):
    #     all_proofs = secured_document['proof']
    #     all_proofs = (
    #         [all_proofs] if isinstance(all_proofs, dict) else all_proofs
    #     )
    #     verification_results = []
    #     for proof in all_proofs:
    #         matching_proofs = []
    #         if 'previousProof' in proof:
    #             previous_proofs = (
    #                 proof['previousProof']
    #                 if isinstance(proof['previousProof'], list)
    #                 else [proof['previousProof']]
    #             )
    #             for item in previous_proofs:
    #                 pass
    #         input_document = secured_document.copy()
    #         input_document.pop('proof')
    #         if len(matching_proofs) > 0:
    #             input_document['proof'] = matching_proofs
    #         cryptosuite_verification_result = self._verify_proof(input_document)

    #     successful_verification_results = []
    #     combined_verification_results = {}
    #     combined_verification_results['status'] = True
    #     combined_verification_results['document'] = None
    #     combined_verification_results['mediaType'] = None

    # async def _verify_proof(self, secured_document):
    #     unsecured_document = secured_document.copy()
    #     proofs = unsecured_document.pop("proof")
    #     verification_response = {
    #         "verifiedDocument": unsecured_document,
    #         "problemDetails": [],
    #         "results": {},
    #     }
    #     verification_response['results']['proof'] = []
    #     for proof in proofs:
    #         suite = CRYPTOSUITES[proof["cryptosuite"]](session=self.session)
    #         verified, problem_details = await suite.verify_proof(unsecured_document, proof)
    #         verification_response['results']["proofs"].append(proof | {
    #             "verified": verified,
    #             "problemDetails": problem_details
    #         })
    #         verification_response['problemDetails'].append()

    #     verification_response['verified'] = True if (
    #         proof['verified'] for proof in verification_response["proofs"]
    #         ) else False
    #     return verification_response
