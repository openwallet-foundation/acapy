"""Indy issuer implementation."""

import json
import logging

import indy.anoncreds

from ..core.error import BaseError

from .base import BaseIssuer
from .util import encode


class IssuerError(BaseError):
    """Generic issuer error."""


class IndyIssuer(BaseIssuer):
    """Indy issuer class."""

    def __init__(self, wallet):
        """
        Initialize an IndyIssuer instance.

        Args:
            wallet: IndyWallet instance

        """
        self.logger = logging.getLogger(__name__)
        self.wallet = wallet

    async def create_credential_offer(self, credential_definition_id: str):
        """
        Create a credential offer for the given credential definition id.

        Args:
            credential_definition_id: The credential definition to create an offer for

        Returns:
            A credential offer

        """
        credential_offer_json = await indy.anoncreds.issuer_create_credential_offer(
            self.wallet.handle, credential_definition_id
        )

        credential_offer = json.loads(credential_offer_json)

        return credential_offer

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

        encoded_values = {}
        schema_attributes = schema["attrNames"]
        for attribute in schema_attributes:
            # Ensure every attribute present in schema to be set.
            # Extraneous attribute names are ignored.
            try:
                credential_value = credential_values[attribute]
            except KeyError:
                raise IssuerError(
                    "Provided credential values are missing a value "
                    + f"for the schema attribute '{attribute}'"
                )

            encoded_values[attribute] = {}
            encoded_values[attribute]["raw"] = str(credential_value)
            encoded_values[attribute]["encoded"] = encode(credential_value)

        (
            credential_json,
            credential_revocation_id,
            revoc_reg_delta_json,
        ) = await indy.anoncreds.issuer_create_credential(
            self.wallet.handle,
            json.dumps(credential_offer),
            json.dumps(credential_request),
            json.dumps(encoded_values),
            revoc_reg_id,
            tails_reader_handle,
        )

        # may throw AnoncredsRevocationRegistryFullError

        # pass revoc JSON to registry for storage / submission
        print("delta", json.dumps(revoc_reg_delta_json, indent=2))

        return json.loads(credential_json), credential_revocation_id

    async def revoke_credential(
        self, revoc_reg_id: str, tails_reader_handle: int, cred_revoc_id: str
    ) -> dict:
        """
        Revoke a credential.

        Args
            revoc_reg_id: ID of the revocation registry
            tails_reader_handle: handle for the registry tails file
            cred_revoc_id: index of the credential in the revocation registry

        """
        revoc_reg_delta_json = await indy.anoncreds.issuer_revoke_credential(
            self.wallet.handle, tails_reader_handle, revoc_reg_id, cred_revoc_id
        )
        # may throw AnoncredsInvalidUserRevocId if using ISSUANCE_ON_DEMAND

        delta = json.loads(revoc_reg_delta_json)
        # pass revoc JSON to registry for storage / submission
        print("delta", json.dumps(revoc_reg_delta_json, indent=2))

        return delta
