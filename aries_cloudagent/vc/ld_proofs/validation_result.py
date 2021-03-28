"""Proof verification and validation result classes."""

from typing import List


class PurposeResult:
    """Proof purpose result class."""

    def __init__(
        self, *, valid: bool, error: Exception = None, controller: dict = None
    ) -> None:
        """Create new PurposeResult instance."""
        self.valid = valid
        self.error = error
        self.controller = controller

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))

    def __eq__(self, other: object) -> bool:
        """Comparison between proof purpose results."""
        if isinstance(other, PurposeResult):
            return (
                self.valid == other.valid
                and self.error == other.error
                and self.controller == other.controller
            )
        return False


class ProofResult:
    """Proof result class."""

    def __init__(
        self,
        *,
        verified: bool,
        proof: dict = None,
        error: Exception = None,
        purpose_result: PurposeResult = None,
    ) -> None:
        """Create new ProofResult instance."""
        self.verified = verified
        self.proof = proof
        self.error = error
        self.purpose_result = purpose_result

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))

    def __eq__(self, other: object) -> bool:
        """Comparison between proof results."""
        if isinstance(other, ProofResult):
            return (
                self.verified == other.verified
                and self.proof == other.proof
                and self.error == other.error
                and self.purpose_result == other.purpose_result
            )
        return False


class DocumentVerificationResult:
    """Domain verification result class."""

    def __init__(
        self,
        *,
        verified: bool,
        document: dict = None,
        results: List[ProofResult] = None,
        errors: List[Exception] = None,
    ) -> None:
        """Create new DocumentVerificationResult instance."""
        self.verified = verified
        self.document = document
        self.results = results
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
        """Comparison between document verification results."""
        if isinstance(other, DocumentVerificationResult):
            return (
                self.verified == other.verified
                and self.document == other.document
                # check results list
                and (
                    # both not present
                    (not self.results and not other.results)
                    # both list and matching
                    or (
                        isinstance(self.results, list)
                        and isinstance(other.results, list)
                        and all(
                            self_result == other_result
                            for (self_result, other_result) in zip(
                                self.results, other.results
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
