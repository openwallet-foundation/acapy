"""Indy issuer implementation."""

import json
import logging
from typing import Sequence, Tuple

import indy.anoncreds
import indy.blob_storage
from indy.error import AnoncredsRevocationRegistryFullError, IndyError, ErrorCode

from ..messaging.util import encode

from .base import (
    BaseIssuer,
    IssuerError,
    IssuerRevocationRegistryFullError,
    DEFAULT_CRED_DEF_TAG,
    DEFAULT_SIGNATURE_TYPE,
)
from ..indy import create_tails_reader, create_tails_writer
from ..indy.error import IndyErrorHandler


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

    def make_schema_id(
        self, origin_did: str, schema_name: str, schema_version: str
    ) -> str:
        """Derive the ID for a schema."""
        return f"{origin_did}:2:{schema_name}:{schema_version}"

    async def create_and_store_schema(
        self,
        origin_did: str,
        schema_name: str,
        schema_version: str,
        attribute_names: Sequence[str],
    ) -> Tuple[str, str]:
        """
        Create a new credential schema and store it in the wallet.

        Args:
            origin_did: the DID issuing the credential definition
            schema_name: the schema name
            schema_version: the schema version
            attribute_names: a sequence of schema attribute names

        Returns:
            A tuple of the schema ID and JSON

        """

        with IndyErrorHandler("Error when creating schema", IssuerError):
            schema_id, schema_json = await indy.anoncreds.issuer_create_schema(
                origin_did, schema_name, schema_version, json.dumps(attribute_names),
            )
        return (schema_id, schema_json)

    def make_credential_definition_id(
        self, origin_did: str, schema: dict, signature_type: str = None, tag: str = None
    ) -> str:
        """Derive the ID for a credential definition."""
        signature_type = signature_type or DEFAULT_SIGNATURE_TYPE
        tag = tag or DEFAULT_CRED_DEF_TAG
        return f"{origin_did}:3:{signature_type}:{str(schema['seqNo'])}:{tag}"

    async def credential_definition_in_wallet(
        self, credential_definition_id: str
    ) -> bool:
        """
        Check whether a given credential definition ID is present in the wallet.

        Args:
            credential_definition_id: The credential definition ID to check
        """
        try:
            await indy.anoncreds.issuer_create_credential_offer(
                self.wallet.handle, credential_definition_id
            )
            return True
        except IndyError as error:
            if error.error_code not in (
                ErrorCode.CommonInvalidStructure,
                ErrorCode.WalletItemNotFound,
            ):
                raise IndyErrorHandler.wrap_error(
                    error,
                    "Error when checking wallet for credential definition",
                    IssuerError,
                ) from error
            # recognized error signifies no such cred def in wallet: pass
        return False

    async def create_and_store_credential_definition(
        self,
        origin_did: str,
        schema: dict,
        signature_type: str = None,
        tag: str = None,
        support_revocation: bool = False,
    ) -> Tuple[str, str]:
        """
        Create a new credential definition and store it in the wallet.

        Args:
            origin_did: the DID issuing the credential definition
            schema: the schema used as a basis
            signature_type: the credential definition signature type (default 'CL')
            tag: the credential definition tag
            support_revocation: whether to enable revocation for this credential def

        Returns:
            A tuple of the credential definition ID and JSON

        """

        with IndyErrorHandler("Error when creating credential definition", IssuerError):
            (
                credential_definition_id,
                credential_definition_json,
            ) = await indy.anoncreds.issuer_create_and_store_credential_def(
                self.wallet.handle,
                origin_did,
                json.dumps(schema),
                tag or DEFAULT_CRED_DEF_TAG,
                signature_type or DEFAULT_SIGNATURE_TYPE,
                json.dumps({"support_revocation": support_revocation}),
            )
        return (credential_definition_id, credential_definition_json)

    async def create_credential_offer(self, credential_definition_id: str) -> str:
        """
        Create a credential offer for the given credential definition id.

        Args:
            credential_definition_id: The credential definition to create an offer for

        Returns:
            The created credential offer

        """
        with IndyErrorHandler("Exception when creating credential offer", IssuerError):
            credential_offer_json = await indy.anoncreds.issuer_create_credential_offer(
                self.wallet.handle, credential_definition_id
            )

        return credential_offer_json

    async def create_credential(
        self,
        schema: dict,
        credential_offer: dict,
        credential_request: dict,
        credential_values: dict,
        revoc_reg_id: str = None,
        tails_file_path: str = None,
    ) -> Tuple[str, str]:
        """
        Create a credential.

        Args
            schema: Schema to create credential for
            credential_offer: Credential Offer to create credential for
            credential_request: Credential request to create credential for
            credential_values: Values to go in credential
            revoc_reg_id: ID of the revocation registry
            tails_file_path: Path to the local tails file

        Returns:
            A tuple of created credential and revocation id

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

        tails_reader_handle = (
            await create_tails_reader(tails_file_path)
            if tails_file_path is not None
            else None
        )

        try:
            (
                credential_json,
                credential_revocation_id,
                _,  # rev_reg_delta_json only for ISSUANCE_ON_DEMAND, excluded by design
            ) = await indy.anoncreds.issuer_create_credential(
                self.wallet.handle,
                json.dumps(credential_offer),
                json.dumps(credential_request),
                json.dumps(encoded_values),
                revoc_reg_id,
                tails_reader_handle,
            )
        except AnoncredsRevocationRegistryFullError:
            self.logger.warning(
                f"Revocation registry {revoc_reg_id} is full: cannot create credential"
            )
            raise IssuerRevocationRegistryFullError(
                f"Revocation registry {revoc_reg_id} is full"
            )
        except IndyError as error:
            raise IndyErrorHandler.wrap_error(
                error, "Error when issuing credential", IssuerError
            ) from error

        return credential_json, credential_revocation_id

    async def revoke_credentials(
        self, revoc_reg_id: str, tails_file_path: str, cred_revoc_ids: Sequence[str]
    ) -> (str, Sequence[str]):
        """
        Revoke a set of credentials in a revocation registry.

        Args:
            revoc_reg_id: ID of the revocation registry
            tails_file_path: path to the local tails file
            cred_revoc_ids: sequences of credential indexes in the revocation registry

        Returns:
            Tuple with the combined revocation delta, list of cred rev ids not revoked

        """
        failed_crids = []
        tails_reader_handle = await create_tails_reader(tails_file_path)

        result_json = None
        for cred_revoc_id in cred_revoc_ids:
            with IndyErrorHandler("Exception when revoking credential", IssuerError):
                try:
                    delta_json = await indy.anoncreds.issuer_revoke_credential(
                        self.wallet.handle,
                        tails_reader_handle,
                        revoc_reg_id,
                        cred_revoc_id,
                    )
                except IndyError as error:
                    if error.error_code == ErrorCode.AnoncredsInvalidUserRevocId:
                        self.logger.error(
                            "Abstaining from revoking credential on "
                            f"rev reg id {revoc_reg_id}, cred rev id={cred_revoc_id}: "
                            "already revoked or not yet issued"
                        )
                    else:
                        self.logger.error(
                            IndyErrorHandler.wrap_error(
                                error, "Revocation error", IssuerError
                            ).roll_up
                        )
                    failed_crids.append(cred_revoc_id)
                    continue

                if result_json:
                    result_json = await self.merge_revocation_registry_deltas(
                        result_json, delta_json
                    )
                else:
                    result_json = delta_json

        return (result_json, failed_crids)

    async def merge_revocation_registry_deltas(
        self, fro_delta: str, to_delta: str
    ) -> str:
        """
        Merge revocation registry deltas.

        Args:
            fro_delta: original delta in JSON format
            to_delta: incoming delta in JSON format

        Returns:
            Merged delta in JSON format

        """

        return await indy.anoncreds.issuer_merge_revocation_registry_deltas(
            fro_delta, to_delta
        )

    async def create_and_store_revocation_registry(
        self,
        origin_did: str,
        cred_def_id: str,
        revoc_def_type: str,
        tag: str,
        max_cred_num: int,
        tails_base_path: str,
    ) -> Tuple[str, str, str]:
        """
        Create a new revocation registry and store it in the wallet.

        Args:
            origin_did: the DID issuing the revocation registry
            cred_def_id: the identifier of the related credential definition
            revoc_def_type: the revocation registry type (default CL_ACCUM)
            tag: the unique revocation registry tag
            max_cred_num: the number of credentials supported in the registry
            tails_base_path: where to store the tails file

        Returns:
            A tuple of the revocation registry ID, JSON, and entry JSON

        """

        tails_writer = await create_tails_writer(tails_base_path)

        with IndyErrorHandler(
            "Exception when creating revocation registry", IssuerError
        ):
            (
                revoc_reg_id,
                revoc_reg_def_json,
                revoc_reg_entry_json,
            ) = await indy.anoncreds.issuer_create_and_store_revoc_reg(
                self.wallet.handle,
                origin_did,
                revoc_def_type,
                tag,
                cred_def_id,
                json.dumps(
                    {
                        "issuance_type": "ISSUANCE_BY_DEFAULT",
                        "max_cred_num": max_cred_num,
                    }
                ),
                tails_writer,
            )
        return (revoc_reg_id, revoc_reg_def_json, revoc_reg_entry_json)
