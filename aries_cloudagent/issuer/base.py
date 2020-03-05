"""Ledger issuer class."""

from abc import ABC, ABCMeta, abstractmethod


class BaseIssuer(ABC, metaclass=ABCMeta):
    """Base class for issuer."""

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        return "<{}>".format(self.__class__.__name__)

    @abstractmethod
    def create_credential_offer(self, credential_definition_id):
        """
        Create a credential offer for the given credential definition id.

        Args:
            credential_definition_id: The credential definition to create an offer for

        Returns:
            A credential offer

        """
        pass

    @abstractmethod
    async def create_credential(
        self,
        schema,
        credential_offer,
        credential_request,
        credential_values,
        revoc_reg_id: str = None,
        tails_reader_handle: int = None,
    ):
        """
        Create a credential.

        Args
            schema: Schema to create credential for
            credential_offer: Credential Offer to create credential for
            credential_request: Credential request to create credential for
            credential_values: Values to go in credential
            revoc_reg_id: ID of the revocation registry
            tails_reader_handle: Handle for the tails file blob reader

        Returns:
            A tuple of created credential, revocation id

        """
        pass

    @abstractmethod
    def revoke_credential(self, revoc_reg_id, tails_reader_handle, cred_revoc_id):
        """
        Revoke a credential.

        Args
            revoc_reg_id: ID of the revocation registry
            tails_reader_handle: handle for the registry tails file
            cred_revoc_id: index of the credential in the revocation registry

        """
        pass
