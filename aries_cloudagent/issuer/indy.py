"""Indy issuer implementation."""

import json
import logging


import indy.anoncreds

from ..error import BaseError
from .base import BaseIssuer
from .util import encode


class IssuerError(BaseError):
    """Generic issuer error."""


class IndyIssuer(BaseIssuer):
    """Indy issuer class."""

    def __init__(self, wallet):
        """
        Initialize an IndyLedger instance.

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
        self, schema, credential_offer, credential_request, credential_values
    ):
        """
        Create a credential.

        Args
            schema: Schema to create credential for
            credential_offer: Credential Offer to create credential for
            credential_request: Credential request to create credential for
            credential_values: Values to go in credential

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
            _,
        ) = await indy.anoncreds.issuer_create_credential(
            self.wallet.handle,
            json.dumps(credential_offer),
            json.dumps(credential_request),
            json.dumps(encoded_values),
            None,
            None,
        )

        return json.loads(credential_json), credential_revocation_id
