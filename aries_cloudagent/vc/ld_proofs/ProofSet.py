"""Class to represent a linked data proof set."""

from typing import List, Union
from pyld.jsonld import JsonLdProcessor

from .error import LinkedDataProofException
from .validation_result import DocumentVerificationResult, ProofResult
from .constants import SECURITY_CONTEXT_URL
from .document_loader import DocumentLoader
from .purposes.ProofPurpose import ProofPurpose
from .suites import LinkedDataProof


class ProofSet:
    @staticmethod
    async def add(
        *,
        document: dict,
        suite: LinkedDataProof,
        purpose: ProofPurpose,
        document_loader: DocumentLoader,
    ) -> dict:
        """Add a proof to the document."""

        input = document.copy()
        input.pop("proof", None)

        proof = await suite.create_proof(
            document=input, purpose=purpose, document_loader=document_loader
        )

        # remove context from proof, if it exists
        proof.pop("@context", None)

        JsonLdProcessor.add_value(document, "proof", proof)
        return document

    @staticmethod
    async def verify(
        *,
        document: dict,
        suites: List[LinkedDataProof],
        purpose: ProofPurpose,
        document_loader: DocumentLoader,
    ) -> DocumentVerificationResult:
        """Verify proof on the document"""
        try:
            input = document.copy()

            if len(suites) == 0:
                raise LinkedDataProofException("At least one suite is required.")

            # Get proof set, remove proof from document
            proof_set = await ProofSet._get_proofs(document=input)
            input.pop("proof", None)

            results = await ProofSet._verify(
                document=input,
                suites=suites,
                proof_set=proof_set,
                purpose=purpose,
                document_loader=document_loader,
            )

            if len(results) == 0:
                suite_names = ", ".join([suite.signature_type for suite in suites])
                raise LinkedDataProofException(
                    f"Could not verify any proofs; no proofs matched the required suites ({suite_names}) and purpose ({purpose.term})"
                )

            # check if all results are valid, create result
            verified = any(result.verified for result in results)
            result = DocumentVerificationResult(
                verified=verified, document=document, results=results
            )

            # If not valid, extract and optionally add errors to result
            if not verified:
                errors = [result.error for result in results if result.error]

                if len(errors) > 0:
                    result.errors = errors

            return result
        except Exception as e:
            return DocumentVerificationResult(
                verified=False, document=document, errors=[e]
            )

    @staticmethod
    async def derive(
        *,
        document: dict,
        reveal_document: dict,
        # TODO: I think this could support multiple suites?
        # But then, why do multiple proofs?
        suite: LinkedDataProof,
        document_loader: DocumentLoader,
        nonce: bytes = None,
    ) -> dict:
        """Derive proof(s), return derived document

        Args:
            document (dict): The document to derive the proof for
            reveal_document (dict): The JSON-LD frame specifying the revealed attributes
            suite (LinkedDataProof): The suite to derive the proof with
            document_loader (DocumentLoader): Document loader used for resolving
            nonce (bytes, optional): Nonce to use for the proof. Defaults to None.

        Returns:
            dict: The document with derived proofs
        """
        input = document.copy()

        if not suite.supported_derive_proof_types:
            raise LinkedDataProofException(
                f"{suite.signature_type} does not support derivation"
            )

        # Get proof set, remove proof from document
        proof_set = await ProofSet._get_proofs(
            document=input, proof_types=suite.supported_derive_proof_types
        )
        input.pop("proof", None)

        # Derive proof, remove context
        derived_proof = await suite.derive_proof(
            proof=proof_set[0],
            document=input,
            reveal_document=reveal_document,
            document_loader=document_loader,
            nonce=nonce,
        )
        derived_proof["proof"].pop("@context", None)

        if len(proof_set) > 1:
            derived_proof["proof"] = [derived_proof["proof"]]

            proof_set.pop(0)

            for proof in proof_set:
                additional_derived_proof = await suite.derive_proof(
                    proof=proof,
                    document=input,
                    reveal_document=reveal_document,
                    document_loader=document_loader,
                )
                additional_derived_proof["proof"].pop("@context", None)
                derived_proof["proof"].append(additional_derived_proof["proof"])

        JsonLdProcessor.add_value(
            derived_proof["document"], "proof", derived_proof["proof"]
        )

        return derived_proof["document"]

    @staticmethod
    async def _get_proofs(
        document: dict, proof_types: Union[List[str], None] = None
    ) -> list:
        "Get proof set from document, optionally filtered by proof_types" ""
        proof_set = JsonLdProcessor.get_values(document, "proof")

        # If proof_types is present, only take proofs that match
        if proof_types:
            proof_set = list(filter(lambda _: _ in proof_types, proof_set))

        if len(proof_set) == 0:
            raise LinkedDataProofException(
                "No matching proofs found in the given document"
            )

        # TODO: digitalbazaar changed this to use the document context
        # in jsonld-signatures. Does that mean we need to provide this ourselves?
        # https://github.com/digitalbazaar/jsonld-signatures/commit/5046805653ea7db47540e5c9c77578d134a559e1
        proof_set = [{"@context": SECURITY_CONTEXT_URL, **proof} for proof in proof_set]

        return proof_set

    @staticmethod
    async def _verify(
        document: dict,
        suites: List[LinkedDataProof],
        proof_set: List[dict],
        purpose: ProofPurpose,
        document_loader: DocumentLoader,
    ) -> List[ProofResult]:
        """Verify proofs in proof set.

        Returns results for proofs that match both on purpose and have a suite
        in the suites lists. This means proofs that don't match on any of these
        WILL NOT be verified OR included in the proof result list.
        """

        # Matches proof purposes proof set to passed purpose.
        # Only proofs with a `proofPurpose` that match the purpose are verified
        # e.g.:
        #   purpose = {term = 'assertionMethod'}
        #   proof_set = [ { proofPurpose: 'assertionMethod' }, { proofPurpose: 'anotherPurpose' }]
        #   return = [ { proofPurpose: 'assertionMethod' } ]
        matches = [proof for proof in proof_set if purpose.match(proof)]

        if len(matches) == 0:
            return []

        results = []

        for proof in matches:
            for suite in suites:
                if suite.match_proof(proof.get("type")):
                    result = await suite.verify_proof(
                        proof=proof,
                        document=document,
                        purpose=purpose,
                        document_loader=document_loader,
                    )
                    result.proof = proof

                    results.append(result)

        return results
