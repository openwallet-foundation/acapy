"""Class to represent a Linked Data proof set."""

from typing import List, Union

from pyld.jsonld import JsonLdProcessor

from .constants import SECURITY_CONTEXT_URL
from .document_loader import DocumentLoaderMethod
from .error import LinkedDataProofException
from .purposes.proof_purpose import ProofPurpose
from .suites import _LinkedDataProof as LinkedDataProof
from .validation_result import DocumentVerificationResult, ProofResult


class ProofSet:
    """Class for managing proof sets on a JSON-LD document."""

    @staticmethod
    async def add(
        *,
        document: dict,
        suite: LinkedDataProof,
        purpose: ProofPurpose,
        document_loader: DocumentLoaderMethod,
    ) -> dict:
        """Add a Linked Data proof to the document.

        If the document contains other proofs, the proof will be appended
        to the existing set of proofs.

        Important note: This method assumes that the term `proof` in the given
        document has the same definition as the `https://w3id.org/security/v2`
        JSON-LD @context.

        Args:
            document (dict): JSON-LD document to be signed.
            suite (LinkedDataProof): A signature suite instance that will create the proof
            purpose (ProofPurpose): A proof purpose instance that will augment the proof
                with information describing its intended purpose.
            document_loader (DocumentLoader): Document loader to use.

        Returns:
            dict: The signed document, with the signature in the top-level
                `proof` property.

        """
        # Shallow copy document to allow removal of existing proofs
        input = document.copy()
        input.pop("proof", None)

        # create the new proof, suites MUST output a proof using security-v2 `@context`
        proof = await suite.create_proof(
            document=input, purpose=purpose, document_loader=document_loader
        )

        JsonLdProcessor.add_value(document, "proof", proof)
        return document

    @staticmethod
    async def verify(
        *,
        document: dict,
        suites: List[LinkedDataProof],
        purpose: ProofPurpose,
        document_loader: DocumentLoaderMethod,
    ) -> DocumentVerificationResult:
        """Verify Linked Data proof(s) on a document.

        The proofs to be verified must match the given proof purse.

        Important note: This method assumes that the term `proof` in the given
        document has the same definition as the `https://w3id.org/security/v2`
        JSON-LD @context.

        Args:
            document (dict): JSON-LD document with one or more proofs to be verified.
            suites (List[LinkedDataProof]): Acceptable signature suite instances
                for verifying the proof(s).
            purpose (ProofPurpose): A proof purpose instance that will match proofs
                to be verified and ensure they were created according to the
                appropriate purpose.
            document_loader (DocumentLoader): Document loader to use.

        Returns:
            DocumentVerificationResult: Object with a `verified` property that is `true`
                if at least one proof matching the given purpose and suite verifies
                and `false` otherwise. Also contains `errors` and `results` properties
                with extra data.

        """
        try:
            # Shallow copy document to allow removal of proof property without
            # modifying external document
            input = document.copy()

            if len(suites) == 0:
                raise LinkedDataProofException("At least one suite is required.")

            # Get proofs from document, remove proof property
            proof_set = await ProofSet._get_proofs(document=input)
            input.pop("proof", None)

            results = await ProofSet._verify(
                document=input,
                suites=suites,
                proof_set=proof_set,
                purpose=purpose,
                document_loader=document_loader,
            )

            # If no proofs were verified because of no matching suites and purposes
            # throw an error
            if len(results) == 0:
                suite_names = ", ".join([suite.signature_type for suite in suites])
                raise LinkedDataProofException(
                    f"Could not verify any proofs; no proofs matched the required"
                    f" suites ({suite_names}) and purpose ({purpose.term})"
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
        document_loader: DocumentLoaderMethod,
        nonce: bytes = None,
    ) -> dict:
        """Create new derived Linked Data proof(s) on document using the reveal document.

        Important note: This method assumes that the term `proof` in the given
        document has the same definition as the `https://w3id.org/security/v2`
        JSON-LD @context. (v3 because BBS?)

        Args:
            document (dict): JSON-LD document with one or more proofs to be derived.
            reveal_document (dict): JSON-LD frame specifying the attributes to reveal.
            suite (LinkedDataProof): A signature suite instance to derive the proof.
            document_loader (DocumentLoader): Document loader to use.
            nonce (bytes, optional): Nonce to use for the proof. Defaults to None.

        Returns:
            dict: The derived document with the derived proof(s) in the top-level
                `proof` property.

        """
        # Shallow copy document to allow removal of existing proofs
        input = document.copy()

        # Check if suite supports derivation
        if not suite.supported_derive_proof_types:
            raise LinkedDataProofException(
                f"{suite.signature_type} does not support derivation"
            )

        # Get proofs, remove proof from document
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
                derived_proof["proof"].append(additional_derived_proof["proof"])

        JsonLdProcessor.add_value(
            derived_proof["document"], "proof", derived_proof["proof"]
        )

        return derived_proof["document"]

    @staticmethod
    async def _get_proofs(
        document: dict, proof_types: Union[List[str], None] = None
    ) -> list:
        """Get proof set from document, optionally filtered by proof_types."""
        proof_set = JsonLdProcessor.get_values(document, "proof")

        # If proof_types is present, only take proofs that match
        if proof_types:
            proof_set = list(filter(lambda _: _["type"] in proof_types, proof_set))

        if len(proof_set) == 0:
            raise LinkedDataProofException(
                "No matching proofs found in the given document"
            )

        # Shallow copy proofs and add document context or SECURITY_CONTEXT_URL
        context = document.get("@context") or SECURITY_CONTEXT_URL
        proof_set = [{"@context": context, **proof} for proof in proof_set]

        return proof_set

    @staticmethod
    async def _verify(
        document: dict,
        suites: List[LinkedDataProof],
        proof_set: List[dict],
        purpose: ProofPurpose,
        document_loader: DocumentLoaderMethod,
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
        #   proof_set = [{proofPurpose:'assertionMethod'},{proofPurpose: 'another'}]
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
