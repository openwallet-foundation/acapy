"""BbsBlsSignature2020Base class."""

from abc import ABCMeta, abstractmethod
from pyld import jsonld
from typing import List

from ..error import LinkedDataProofException
from ..document_loader import DocumentLoader
from .LinkedDataProof import LinkedDataProof


class BbsBlsSignature2020Base(LinkedDataProof, metaclass=ABCMeta):
    """Base class for BbsBlsSignature suites."""

    def _create_verify_proof_data(
        self, *, proof: dict, document: dict, document_loader: DocumentLoader
    ) -> List[str]:
        """Create proof verification data."""
        c14_proof_options = self._canonize_proof(
            proof=proof, document=document, document_loader=document_loader
        )

        # Return only the lines that have any content in them
        # e.g. "aa\nbb\n\n\ncccdkea\n" -> ['aa', 'bb', 'cccdkea']
        return list(filter(lambda _: len(_) > 0, c14_proof_options.split("\n")))

    def _create_verify_document_data(
        self, *, document: dict, document_loader: DocumentLoader
    ) -> List[str]:
        """Create document verification data."""
        c14n_doc = self._canonize(input=document, document_loader=document_loader)

        # Return only the lines that have any content in them
        # e.g. "aa\nbb\n\n\ncccdkea\n" -> ['aa', 'bb', 'cccdkea']
        return list(filter(lambda _: len(_) > 0, c14n_doc.split("\n")))

    def _canonize(self, *, input, document_loader: DocumentLoader = None) -> str:
        """Canonize input document using URDNA2015 algorithm."""
        # application/n-quads format always returns str
        return jsonld.normalize(
            input,
            {
                "algorithm": "URDNA2015",
                "format": "application/n-quads",
                "documentLoader": document_loader,
            },
        )

    @abstractmethod
    def _canonize_proof(
        self, *, proof: dict, document: dict, document_loader: DocumentLoader = None
    ):
        """Canonize proof dictionary. Removes values that are not part of signature."""

    def _assert_verification_method(self, verification_method: dict):
        """Assert verification method. Throws if not ok."""
        # FIXME: bls is not in security yet. (may be fixed in lower level class)
        required_key_type = "sec:Bls12381G2Key2020"
        if not jsonld.JsonLdProcessor.has_value(
            verification_method, "type", required_key_type
        ):
            raise LinkedDataProofException(
                f"Invalid key type. The key type must be {required_key_type}"
            )

    def _get_verification_method(self, *, proof: dict, document_loader: DocumentLoader):
        """Get verification method.

        Overwrites base get verification method to assert key type.
        """
        verification_method = super()._get_verification_method(
            proof=proof, document_loader=document_loader
        )
        self._assert_verification_method(verification_method)

        return verification_method
