"""Presentation verification and validation result classes."""

from typing import List

from ..ld_proofs import DocumentVerificationResult


class PresentationVerificationResult:
    """Presentation verification result class."""

    def __init__(
        self,
        *,
        verified: bool,
        presentation_result: DocumentVerificationResult = None,
        credential_results: List[DocumentVerificationResult] = None,
        errors: List[Exception] = None,
    ) -> None:
        """Create new PresentationVerificationResult instance."""
        self.verified = verified
        self.presentation_result = presentation_result
        self.credential_results = credential_results
        self.errors = errors

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))

    def __eq__(self, other: object) -> bool:
        """Comparison between presentation verification results."""
        if isinstance(other, PresentationVerificationResult):
            return (
                self.verified == other.verified
                and self.presentation_result == other.presentation_result
                # check credential results list
                and (
                    # both not present
                    (not self.credential_results and not other.credential_results)
                    # both list and matching
                    or (
                        isinstance(self.credential_results, list)
                        and isinstance(other.credential_results, list)
                        and all(
                            self_result == other_result
                            for (self_result, other_result) in zip(
                                self.credential_results, other.credential_results
                            )
                        )
                    )
                )
                # check error list
                and (
                    # both not present
                    (not self.errors and not other.errors)
                    # both list and matching
                    or (
                        isinstance(self.errors, list)
                        and isinstance(other.errors, list)
                        and all(
                            self_error == other_error
                            for (self_error, other_error) in zip(
                                self.errors, other.errors
                            )
                        )
                    )
                )
            )
        return False
