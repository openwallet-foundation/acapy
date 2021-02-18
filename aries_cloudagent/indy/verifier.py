"""Base Indy Verifier class."""

import logging

from abc import ABC, ABCMeta, abstractmethod

LOGGER = logging.getLogger(__name__)


class IndyVerifier(ABC, metaclass=ABCMeta):
    """Base class for Indy Verifier."""

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        return "<{}>".format(self.__class__.__name__)

    @abstractmethod
    def verify_presentation(
        self,
        presentation_request,
        presentation,
        schemas,
        credential_definitions,
        rev_reg_defs,
        rev_reg_entries,
    ):
        """
        Verify a presentation.

        Args:
            presentation_request: Presentation request data
            presentation: Presentation data
            schemas: Schema data
            credential_definitions: credential definition data
            rev_reg_defs: revocation registry definitions
            rev_reg_entries: revocation registry entries
        """
