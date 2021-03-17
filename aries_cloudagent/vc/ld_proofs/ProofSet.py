"""Class to represent a linked data proof set."""

from typing import List
from pyld.jsonld import JsonLdProcessor

from .constants import SECURITY_V2_URL
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
        document_loader: DocumentLoader
    ) -> dict:
        document = document.copy()

        if "proof" in document:
            del document["proof"]

        proof = await suite.create_proof(
            document=document, purpose=purpose, document_loader=document_loader
        )

        if "@context" in proof:
            del proof["@context"]

        JsonLdProcessor.add_value(document, "proof", proof)

        return document

    @staticmethod
    async def verify(
        *,
        document: dict,
        suites: List[LinkedDataProof],
        purpose: ProofPurpose,
        document_loader: DocumentLoader
    ) -> dict:
        try:
            document = document.copy()

            proofs = await ProofSet._get_proofs(document=document)

            results = await ProofSet._verify(
                document=document,
                suites=suites,
                proof_set=proofs.get("proof_set"),
                purpose=purpose,
                document_loader=document_loader,
            )

            if len(results) == 0:
                raise Exception(
                    "Could not verify any proofs; no proofs matched the required suite and purpose"
                )

            verified = any(result.get("verified") for result in results)

            if not verified:
                errors = [
                    result.get("error") for result in results if result.get("error")
                ]
                result = {"verified": verified, "results": results}

                if len(errors) > 0:
                    result["error"] = errors

                return result

            return {"verified": verified, "results": results}
        except Exception as e:
            return {"verified": verified, "error": e}

    @staticmethod
    async def _get_proofs(document: dict) -> dict:
        proof_set = JsonLdProcessor.get_values(document, "proof")

        if "proof" in document:
            del document["proof"]

        if len(proof_set) == 0:
            raise Exception("No matching proofs found in the given document")

        proof_set = [{"@context": SECURITY_V2_URL, **proof} for proof in proof_set]

        return {"proof_set": proof_set, "document": document}

    @staticmethod
    async def _verify(
        document: dict,
        suites: List[LinkedDataProof],
        proof_set: List[dict],
        purpose: ProofPurpose,
        document_loader: DocumentLoader,
    ) -> List[dict]:
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
                    results.append({"proof": proof, **result})

        return results
