"""Class to represent a linked data proof set."""
import asyncio
from typing import Union, List
from pyld.jsonld import JsonLdProcessor

from .suites import LinkedDataProof
from .purposes.ProofPurpose import ProofPurpose
from .document_loader import DocumentLoader
from .constants import SECURITY_CONTEXT_V2_URL


class ProofSet:
    async def add(
        self,
        *,
        document: Union[dict, str],
        suite: LinkedDataProof,
        purpose: ProofPurpose,
        document_loader: DocumentLoader
    ) -> dict:

        if isinstance(document, str):
            document = await document_loader(document)

        input_ = document.copy()

        if "proof" in input_:
            del input_["proof"]

        proof = await suite.create_proof(input_, purpose, document_loader)

        if "@context" in proof:
            del proof["@context"]

        JsonLdProcessor.add_value(document, "proof", proof)

        return document

    async def verify(
        self,
        *,
        document: Union[dict, str],
        suites: List[LinkedDataProof],
        purpose: ProofPurpose,
        document_loader: DocumentLoader
    ):
        try:
            if isinstance(document, str):
                document = await document_loader(document)

            proofs = await ProofSet._get_proofs(document, document_loader)

            results = ProofSet._verify(
                document, suites, proofs["proof_set"], purpose, document_loader
            )

            if results.len() == 0:
                raise Exception(
                    "Could not verify any proofs; no proofs matched the required suite and purpose"
                )

            verified = any(x["verified"] for x in results)

            if not verified:
                errors = [r["error"] for r in results if r["error"]]
                result = {"verified": verified, "results": results}

                if errors.len() > 0:
                    result["error"] = errors

                return result

            return {"verified": verified, "results": results}
        except Exception as e:
            return {"verified": verified, "error": e}

    @staticmethod
    async def _get_proofs(document: dict, document_loader: DocumentLoader) -> dict:
        proof_set = JsonLdProcessor.get_values(document, "proof")

        del document["proof"]

        if proof_set.len() == 0:
            raise Exception("No matching proofs found in the given document")

        proof_set = [
            {"@context": SECURITY_CONTEXT_V2_URL, **proof} for proof in proof_set
        ]

        return {"proof_set": proof_set, "document": document}

    @staticmethod
    async def _verify(
        document: dict,
        suites: List[LinkedDataProof],
        proof_set: List[dict],
        purpose: ProofPurpose,
        document_loader: DocumentLoader,
    ):

        result = await asyncio.gather(
            *[
                purpose.match(proof["type"], document, document_loader)
                for proof in proof_set
            ]
        )

        matches = [x for i, x in enumerate(proof_set) if result[i]]

        if matches.len() == 0:
            return []

        out = []

        for m in matches:
            for s in suites:
                if await s.match_proof(m["type"]):
                    out.append(s.verify_proof(m, document, purpose, document_loader))

        results = await asyncio.gather(
            *[x.verify_proof(x, document, purpose, document_loader) for x in out]
        )

        return [
            None if not r else {"proof": matches[i], **r} for r, i in enumerate(results)
        ]
