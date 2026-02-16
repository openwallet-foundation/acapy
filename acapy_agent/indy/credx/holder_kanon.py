"""Indy holder implementation."""

import asyncio
import inspect
import json
import logging
import re
from typing import Dict, Optional, Sequence, Tuple

from indy_credx import (
    Credential,
    CredentialRequest,
    CredentialRevocationState,
    CredxError,
    LinkSecret,
    Presentation,
    PresentCredentials,
)
from uuid_utils import uuid4

from ...core.profile import Profile, ProfileSession
from ...database_manager.db_errors import DBCode, DBError
from ...ledger.base import BaseLedger
from ...wallet.error import WalletNotFoundError
from ..holder import IndyHolder, IndyHolderError

LOGGER = logging.getLogger(__name__)

CATEGORY_CREDENTIAL = "credential"
CATEGORY_LINK_SECRET = "master_secret"

ERR_FETCH_LINK_SECRET = "Error fetching link secret"
ERR_LOAD_LINK_SECRET = "Error loading link secret"
ERR_CREATE_LINK_SECRET = "Error creating link secret"
ERR_SAVE_LINK_SECRET = "Error saving link secret"
ERR_CREATE_CRED_REQ = "Error creating credential request"
ERR_PROCESS_RECEIVED_CRED = "Error processing received credential"
ERR_PARSING_SCHEMA_ID = "Error parsing credential schema ID: {}"
ERR_PARSING_CRED_DEF_ID = "Error parsing credential definition ID: {}"
ERR_STORING_CREDENTIAL = "Error storing credential"
ERR_RETRIEVING_CREDENTIALS = "Error retrieving credentials"
ERR_LOADING_STORED_CREDENTIAL = "Error loading stored credential"
ERR_UNKNOWN_PRESENTATION_REQ_REF = "Unknown presentation request referent: {}"
ERR_RETRIEVING_CREDENTIAL = "Error retrieving credential"
ERR_LOADING_REQUESTED_CREDENTIAL = "Error loading requested credential"
ERR_RETRIEVING_CRED_MIME_TYPES = "Error retrieving credential mime types"
ERR_CREATE_PRESENTATION = "Error creating presentation"
ERR_CREATE_REV_STATE = "Error creating revocation state"


def _make_cred_info(cred_id, cred: Credential):
    cred_info = cred.to_dict()  # not secure!
    rev_info = cred_info["signature"]["r_credential"]
    return {
        "referent": cred_id,
        "schema_id": cred_info["schema_id"],
        "cred_def_id": cred_info["cred_def_id"],
        "rev_reg_id": cred_info["rev_reg_id"],
        "cred_rev_id": str(rev_info["i"]) if rev_info else None,
        "attrs": {name: val["raw"] for (name, val) in cred_info["values"].items()},
    }


def _normalize_attr_name(name: str) -> str:
    return name.replace(" ", "")


class IndyCredxHolder(IndyHolder):
    """Indy-credx holder class."""

    LINK_SECRET_ID = "default"

    def __init__(self, profile: Profile):
        """Initialize an IndyCredxHolder instance.

        Args:
            profile: The active profile instance

        """
        self._profile = profile

    @property
    def profile(self) -> Profile:
        """Accessor for the profile instance."""
        return self._profile

    async def get_link_secret(self) -> LinkSecret:
        """Get or create the default link secret."""
        LOGGER.debug("Attempting to fetch or create the link secret.")

        while True:
            async with self._profile.session() as session:
                record = await self._fetch_link_secret_record(session)

                if record:
                    secret = self._load_existing_link_secret(record)
                    break
                else:
                    secret = await self._create_and_save_link_secret(session)
                    if secret:  # Successfully created and saved
                        break
                    # else: retry due to duplicate error

        LOGGER.debug("Returning link secret.")
        return secret

    async def _fetch_link_secret_record(self, session: ProfileSession):
        """Fetch link secret record from storage."""
        try:
            fetch_method = session.handle.fetch
            if inspect.iscoroutinefunction(fetch_method):
                return await fetch_method(
                    CATEGORY_LINK_SECRET, IndyCredxHolder.LINK_SECRET_ID
                )
            return fetch_method(CATEGORY_LINK_SECRET, IndyCredxHolder.LINK_SECRET_ID)
        except DBError as err:
            LOGGER.error("%s", ERR_FETCH_LINK_SECRET)
            raise IndyHolderError(ERR_FETCH_LINK_SECRET) from err

    def _load_existing_link_secret(self, record) -> LinkSecret:
        """Load existing link secret from record."""
        try:
            LOGGER.debug("Loading LinkSecret")
            secret = LinkSecret.load(record.raw_value)
            LOGGER.debug("Loaded existing link secret.")
            return secret
        except CredxError as err:
            LOGGER.info("Attempt fallback method after error loading link secret")
            return self._load_link_secret_fallback(record, err)

    def _load_link_secret_fallback(self, record, original_err) -> LinkSecret:
        """Attempt fallback method to load link secret."""
        try:
            ms_string = record.value.decode("ascii")
            link_secret_dict = {"value": {"ms": ms_string}}
            secret = LinkSecret.load(link_secret_dict)
            LOGGER.debug("Loaded LinkSecret from AnonCreds secret.")
            return secret
        except CredxError:
            LOGGER.error("%s", ERR_LOAD_LINK_SECRET)
            raise IndyHolderError(ERR_LOAD_LINK_SECRET) from original_err

    async def _create_and_save_link_secret(self, session: ProfileSession) -> LinkSecret:
        """Create and save a new link secret."""
        secret = self._create_new_link_secret()

        try:
            insert_method = session.handle.insert
            if inspect.iscoroutinefunction(insert_method):
                await insert_method(
                    CATEGORY_LINK_SECRET,
                    IndyCredxHolder.LINK_SECRET_ID,
                    secret.to_json_buffer(),
                )
            else:
                insert_method(
                    CATEGORY_LINK_SECRET,
                    IndyCredxHolder.LINK_SECRET_ID,
                    secret.to_json_buffer(),
                )
            LOGGER.debug("Saved new link secret.")
            return secret
        except DBError as err:
            if self._is_duplicate_error(err):
                return None  # Retry needed
            LOGGER.error("%s", ERR_SAVE_LINK_SECRET)
            raise IndyHolderError(ERR_SAVE_LINK_SECRET) from err

    def _create_new_link_secret(self) -> LinkSecret:
        """Create a new link secret."""
        try:
            secret = LinkSecret.create()
            LOGGER.debug("Created new link secret.")
            return secret
        except CredxError as err:
            LOGGER.error("%s", ERR_CREATE_LINK_SECRET)
            raise IndyHolderError(ERR_CREATE_LINK_SECRET) from err

    def _is_duplicate_error(self, err) -> bool:
        """Check if error is a duplicate record error."""
        try:
            return err.code in DBCode.DUPLICATE
        except Exception:
            return False

    async def create_credential_request(
        self, credential_offer: dict, credential_definition: dict, holder_did: str
    ) -> Tuple[str, str]:
        """Create a credential request for the given credential offer.

        Args:
            credential_offer: The credential offer to create request for
            credential_definition: The credential definition to create an offer for
            holder_did: the DID of the agent making the request

        Returns:
            A tuple of the credential request and credential request metadata

        """
        try:
            secret = await self.get_link_secret()
            (
                cred_req,
                cred_req_metadata,
            ) = await asyncio.get_event_loop().run_in_executor(
                None,
                CredentialRequest.create,
                holder_did,
                credential_definition,
                secret,
                IndyCredxHolder.LINK_SECRET_ID,
                credential_offer,
            )
        except CredxError as err:
            raise IndyHolderError(ERR_CREATE_CRED_REQ) from err
        cred_req_json, cred_req_metadata_json = (
            cred_req.to_json(),
            cred_req_metadata.to_json(),
        )

        LOGGER.debug(
            "Created credential request. "
            "credential_request_json=%s credential_request_metadata_json=%s",
            cred_req_json,
            cred_req_metadata_json,
        )

        return cred_req_json, cred_req_metadata_json

    def _parse_and_validate_ids(self, cred_recvd) -> tuple[tuple, tuple]:
        """Parse and validate schema and credential definition IDs.

        Returns:
            Tuple of (schema_id_parts, cdef_id_parts)

        """
        schema_id = cred_recvd.schema_id
        # Handle both qualified (did:sov:V4SG:2:schema:1.0)
        # and unqualified (V4SG:2:schema:1.0) schema IDs
        schema_id_parts = re.match(
            r"^([^:]+(?::[^:]+:[^:]+)?):2:([^:]+):([^:]+)$", schema_id
        )
        if not schema_id_parts:
            raise IndyHolderError(ERR_PARSING_SCHEMA_ID.format(schema_id))

        cred_def_id = cred_recvd.cred_def_id
        cdef_id_parts = re.match(
            r"^([^:]+(?::[^:]+:[^:]+)?):3:CL:([^:]+):([^:]+)$", cred_def_id
        )
        if not cdef_id_parts:
            raise IndyHolderError(ERR_PARSING_CRED_DEF_ID.format(cred_def_id))

        return schema_id_parts, cdef_id_parts

    def _normalize_did(self, did: str) -> str:
        """Normalize DID to unqualified format for consistent storage."""
        return did[8:] if did.startswith("did:sov:") else did

    def _build_credential_tags(
        self,
        cred_recvd,
        schema_id_parts: tuple,
        cdef_id_parts: tuple,
        credential_data: dict,
        credential_attr_mime_types: Optional[dict],
    ) -> tuple[dict, dict]:
        """Build tags and mime_types for credential storage.

        Returns:
            Tuple of (tags, mime_types)

        """
        schema_issuer_did = self._normalize_did(schema_id_parts[1])
        issuer_did = self._normalize_did(cdef_id_parts[1])

        tags = {
            "schema_id": cred_recvd.schema_id,
            "schema_issuer_did": schema_issuer_did,
            "schema_name": schema_id_parts[2],
            "schema_version": schema_id_parts[3],
            "issuer_did": issuer_did,
            "cred_def_id": cred_recvd.cred_def_id,
            "rev_reg_id": cred_recvd.rev_reg_id or "None",
        }

        mime_types = {}
        for k, attr_value in credential_data["values"].items():
            attr_name = _normalize_attr_name(k)
            tags[f"attr::{attr_name}::value"] = attr_value["raw"]
            if credential_attr_mime_types and k in credential_attr_mime_types:
                mime_types[k] = credential_attr_mime_types[k]

        return tags, mime_types

    async def _insert_credential_record(
        self, txn: ProfileSession, credential_id: str, cred_recvd, tags: dict
    ) -> None:
        """Insert credential record into storage."""
        insert_method = txn.handle.insert
        if inspect.iscoroutinefunction(insert_method):
            await insert_method(
                CATEGORY_CREDENTIAL,
                credential_id,
                cred_recvd.to_json_buffer(),
                tags=tags,
            )
        else:
            insert_method(
                CATEGORY_CREDENTIAL,
                credential_id,
                cred_recvd.to_json_buffer(),
                tags=tags,
            )

    async def _insert_mime_types_record(
        self, txn: ProfileSession, credential_id: str, mime_types: dict
    ) -> None:
        """Insert MIME types record if needed."""
        if not mime_types:
            return

        insert_method = txn.handle.insert
        if inspect.iscoroutinefunction(insert_method):
            await insert_method(
                IndyHolder.RECORD_TYPE_MIME_TYPES,
                credential_id,
                value_json=mime_types,
            )
        else:
            insert_method(
                IndyHolder.RECORD_TYPE_MIME_TYPES,
                credential_id,
                value_json=mime_types,
            )

    async def _commit_transaction(self, txn) -> None:
        """Commit transaction if commit method exists."""
        commit_method = getattr(txn, "commit", None)
        if not commit_method:
            return

        if inspect.iscoroutinefunction(commit_method):
            await commit_method()
        else:
            commit_method()

    async def store_credential(
        self,
        credential_definition: dict,
        credential_data: dict,
        credential_request_metadata: dict,
        credential_attr_mime_types: Optional[dict] = None,
        credential_id: Optional[str] = None,
        rev_reg_def: Optional[dict] = None,
    ) -> str:
        """Store a credential in the wallet.

        Args:
            credential_definition: Credential definition for this credential
            credential_data: Credential data generated by the issuer
            credential_request_metadata: credential request metadata generated
                by the issuer
            credential_attr_mime_types: dict mapping attribute names to (optional)
                MIME types to store as non-secret record, if specified
            credential_id: optionally override the stored credential id
            rev_reg_def: revocation registry definition in json

        Returns:
            the ID of the stored credential

        """
        try:
            secret = await self.get_link_secret()
            cred = Credential.load(credential_data)
            cred_recvd = await asyncio.get_event_loop().run_in_executor(
                None,
                cred.process,
                credential_request_metadata,
                secret,
                credential_definition,
                rev_reg_def,
            )
        except CredxError as err:
            raise IndyHolderError(ERR_PROCESS_RECEIVED_CRED) from err

        schema_id_parts, cdef_id_parts = self._parse_and_validate_ids(cred_recvd)

        credential_id = credential_id or str(uuid4())

        tags, mime_types = self._build_credential_tags(
            cred_recvd,
            schema_id_parts,
            cdef_id_parts,
            credential_data,
            credential_attr_mime_types,
        )

        try:
            async with self._profile.transaction() as txn:
                await self._insert_credential_record(txn, credential_id, cred_recvd, tags)
                await self._insert_mime_types_record(txn, credential_id, mime_types)
                await self._commit_transaction(txn)
        except DBError as err:
            raise IndyHolderError(ERR_STORING_CREDENTIAL) from err

        return credential_id

    async def get_credentials(self, *, offset: int, limit: int, wql: dict):
        """Get credentials stored in the wallet.

        Args:
            offset: Starting index
            limit: Number of records to return
            wql: wql query dict

        """
        result = []

        try:
            rows = self._profile.store.scan(
                category=CATEGORY_CREDENTIAL,
                tag_filter=wql,
                offset=offset,
                limit=limit,
                profile=self._profile.settings.get("wallet.askar_profile"),
            )
            async for row in rows:
                cred = Credential.load(row.raw_value)
                result.append(_make_cred_info(row.name, cred))
        except DBError as err:
            raise IndyHolderError(ERR_RETRIEVING_CREDENTIALS) from err
        except CredxError as err:
            raise IndyHolderError(ERR_LOADING_STORED_CREDENTIAL) from err

        return result

    async def get_credentials_for_presentation_request_by_referent(
        self,
        presentation_request: dict,
        referents: Sequence[str],
        *,
        offset: int,
        limit: int,
        extra_query: Optional[dict] = None,
    ):
        """Get credentials stored in the wallet.

        Args:
            presentation_request: Valid presentation request from issuer
            referents: Presentation request referents to use to search for creds
            offset: Starting index
            limit: Maximum number of records to return
            extra_query: wql query dict

        """
        extra_query = extra_query or {}
        referents = self._get_effective_referents(presentation_request, referents)

        creds = {}
        for reft in referents:
            await self._process_referent(
                presentation_request, reft, creds, extra_query, offset, limit
            )

        self._finalize_credential_referents(creds)
        return list(creds.values())

    def _get_effective_referents(
        self, presentation_request: dict, referents: Sequence[str]
    ) -> Sequence[str]:
        """Get effective referents for the presentation request."""
        if not referents:
            return (
                *presentation_request["requested_attributes"],
                *presentation_request["requested_predicates"],
            )
        return referents

    async def _process_referent(
        self,
        presentation_request: dict,
        reft: str,
        creds: dict,
        extra_query: dict,
        offset: int,
        limit: int,
    ):
        """Process a single referent to find matching credentials."""
        names, restr = self._extract_referent_info(presentation_request, reft)
        tag_filter = self._build_tag_filter(names, restr, extra_query)

        rows = self._profile.store.scan(
            category=CATEGORY_CREDENTIAL,
            tag_filter=tag_filter,
            offset=offset,
            limit=limit,
            profile=self._profile.settings.get("wallet.askar_profile"),
        )

        async for row in rows:
            self._add_credential_to_results(row, reft, creds, presentation_request)

    def _extract_referent_info(
        self, presentation_request: dict, reft: str
    ) -> tuple[set, dict]:
        """Extract names and restrictions from a referent."""
        names = set()

        if reft in presentation_request["requested_attributes"]:
            attr = presentation_request["requested_attributes"][reft]
            names = self._extract_attribute_names(attr)
            restr = attr.get("restrictions")
        elif reft in presentation_request["requested_predicates"]:
            pred = presentation_request["requested_predicates"][reft]
            if "name" in pred:
                names.add(_normalize_attr_name(pred["name"]))
            restr = pred.get("restrictions")
        else:
            raise IndyHolderError(ERR_UNKNOWN_PRESENTATION_REQ_REF.format(reft))

        return names, restr

    def _extract_attribute_names(self, attr: dict) -> set:
        """Extract attribute names from attribute specification."""
        names = set()
        if "name" in attr:
            names.add(_normalize_attr_name(attr["name"]))
        elif "names" in attr:
            names.update(_normalize_attr_name(name) for name in attr["names"])
        return names

    def _build_tag_filter(self, names: set, restr: dict, extra_query: dict) -> dict:
        """Build tag filter for credential search."""
        tag_filter = {"$exist": [f"attr::{name}::value" for name in names]}

        filters_to_combine = [tag_filter]
        if restr:
            filters_to_combine.extend(restr if isinstance(restr, list) else [restr])
        if extra_query:
            filters_to_combine.append(extra_query)

        return {"$and": filters_to_combine} if len(filters_to_combine) > 1 else tag_filter

    def _add_credential_to_results(
        self, row, reft: str, creds: dict, presentation_request: dict
    ):
        """Add credential to results or update existing entry."""
        if row.name in creds:
            creds[row.name]["presentation_referents"].add(reft)
        else:
            cred_info = _make_cred_info(row.name, Credential.load(row.raw_value))
            creds[row.name] = {
                "cred_info": cred_info,
                "interval": presentation_request.get("non_revoked"),
                "presentation_referents": {reft},
            }

    def _finalize_credential_referents(self, creds: dict):
        """Convert presentation referents sets to lists."""
        for cred in creds.values():
            cred["presentation_referents"] = list(cred["presentation_referents"])

    async def get_credential(self, credential_id: str) -> str:
        """Get a credential stored in the wallet.

        Args:
            credential_id: Credential id to retrieve

        """
        get_cred_method = self._get_credential
        if inspect.iscoroutinefunction(get_cred_method):
            cred = await get_cred_method(credential_id)
        else:
            cred = get_cred_method(credential_id)
        return json.dumps(_make_cred_info(credential_id, cred))

    async def _get_credential(self, credential_id: str) -> Credential:
        """Get an unencoded Credential instance from the store."""
        try:
            async with self._profile.session() as session:
                fetch_method = session.handle.fetch
                if inspect.iscoroutinefunction(fetch_method):
                    cred = await fetch_method(CATEGORY_CREDENTIAL, credential_id)
                else:
                    cred = fetch_method(CATEGORY_CREDENTIAL, credential_id)
        except DBError as err:
            raise IndyHolderError(ERR_RETRIEVING_CREDENTIAL) from err

        if not cred:
            raise WalletNotFoundError(
                f"Credential {credential_id} not found in wallet {self.profile.name}"
            )

        try:
            return Credential.load(cred.raw_value)
        except CredxError as err:
            raise IndyHolderError(ERR_LOADING_REQUESTED_CREDENTIAL) from err

    async def credential_revoked(
        self,
        ledger: BaseLedger,
        credential_id: str,
        timestamp_from: Optional[int] = None,
        timestamp_to: Optional[int] = None,
    ) -> bool:
        """Check ledger for revocation status of credential by cred id.

        Args:
            ledger (BaseLedger): The ledger to check for revocation status.
            credential_id (str): The ID of the credential to check.
            timestamp_from (int, optional): The starting sequence number of the revocation
                registry delta. Defaults to None.
            timestamp_to (int, optional): The ending sequence number of the revocation
                registry delta. Defaults to None.

        Returns:
            bool: True if the credential is revoked, False otherwise.

        """
        get_cred_method = self._get_credential
        if inspect.iscoroutinefunction(get_cred_method):
            cred = await get_cred_method(credential_id)
        else:
            cred = get_cred_method(credential_id)
        rev_reg_id = cred.rev_reg_id

        if rev_reg_id:
            cred_rev_id = cred.rev_reg_index
            get_delta = ledger.get_revoc_reg_delta
            if inspect.iscoroutinefunction(get_delta):
                (rev_reg_delta, _) = await get_delta(
                    rev_reg_id,
                    timestamp_from,
                    timestamp_to,
                )
            else:
                (rev_reg_delta, _) = get_delta(
                    rev_reg_id,
                    timestamp_from,
                    timestamp_to,
                )
            return cred_rev_id in rev_reg_delta["value"].get("revoked", [])
        else:
            return False

    async def delete_credential(self, credential_id: str):
        """Remove a credential stored in the wallet.

        Args:
            credential_id: Credential id to remove

        """
        try:
            async with self._profile.session() as session:
                remove_method = session.handle.remove
                if inspect.iscoroutinefunction(remove_method):
                    await remove_method(CATEGORY_CREDENTIAL, credential_id)
                    await remove_method(IndyHolder.RECORD_TYPE_MIME_TYPES, credential_id)
                else:
                    remove_method(CATEGORY_CREDENTIAL, credential_id)
                    remove_method(IndyHolder.RECORD_TYPE_MIME_TYPES, credential_id)
        except DBError as err:
            # Ignore not-found deletes; re-raise others
            try:
                if err.code in DBCode.NOT_FOUND:
                    pass
                else:
                    raise IndyHolderError("Error deleting credential") from err
            except Exception:
                # If err lacks a code, treat as unexpected
                raise IndyHolderError("Error deleting credential") from err

    async def get_mime_type(
        self, credential_id: str, attr: Optional[str] = None
    ) -> dict | str:
        """Get MIME type per attribute (or for all attributes).

        Args:
            credential_id: credential id
            attr: attribute of interest or omit for all

        Returns: Attribute MIME type or dict mapping attribute names to MIME types
            attr_meta_json = all_meta.tags.get(attr)

        """
        try:
            async with self._profile.session() as session:
                fetch_method = session.handle.fetch
                if inspect.iscoroutinefunction(fetch_method):
                    mime_types_record = await fetch_method(
                        IndyHolder.RECORD_TYPE_MIME_TYPES,
                        credential_id,
                    )
                else:
                    mime_types_record = fetch_method(
                        IndyHolder.RECORD_TYPE_MIME_TYPES,
                        credential_id,
                    )
        except DBError as err:
            raise IndyHolderError(ERR_RETRIEVING_CRED_MIME_TYPES) from err
        values = mime_types_record and mime_types_record.value_json
        if values:
            return values.get(attr) if attr else values

    async def create_presentation(
        self,
        presentation_request: dict,
        requested_credentials: dict,
        schemas: dict,
        credential_definitions: dict,
        rev_states: Optional[dict] = None,
    ) -> str:
        """Get credentials stored in the wallet.

        Args:
            presentation_request: Valid indy format presentation request
            requested_credentials: Indy format requested credentials
            schemas: Indy formatted schemas JSON
            credential_definitions: Indy formatted credential definitions JSON
            rev_states: Indy format revocation states JSON

        """
        creds: Dict[str, Credential] = {}
        present_creds = PresentCredentials()

        await self._process_requested_attributes(
            requested_credentials, creds, present_creds, rev_states
        )
        await self._process_requested_predicates(
            requested_credentials, creds, present_creds, rev_states
        )

        return await self._create_final_presentation(
            presentation_request,
            requested_credentials,
            present_creds,
            schemas,
            credential_definitions,
        )

    async def _process_requested_attributes(
        self, requested_credentials: dict, creds: dict, present_creds, rev_states: dict
    ):
        """Process requested attributes for presentation."""
        req_attrs = requested_credentials.get("requested_attributes") or {}
        for reft, detail in req_attrs.items():
            cred_id = detail["cred_id"]
            if cred_id not in creds:
                creds[cred_id] = await self._get_credential(cred_id)

            timestamp, rev_state = self._get_rev_state(cred_id, detail, creds, rev_states)
            present_creds.add_attributes(
                creds[cred_id],
                reft,
                reveal=detail["revealed"],
                timestamp=timestamp,
                rev_state=rev_state,
            )

    async def _process_requested_predicates(
        self, requested_credentials: dict, creds: dict, present_creds, rev_states: dict
    ):
        """Process requested predicates for presentation."""
        req_preds = requested_credentials.get("requested_predicates") or {}
        for reft, detail in req_preds.items():
            cred_id = detail["cred_id"]
            if cred_id not in creds:
                creds[cred_id] = await self._get_credential(cred_id)

            timestamp, rev_state = self._get_rev_state(cred_id, detail, creds, rev_states)
            present_creds.add_predicates(
                creds[cred_id],
                reft,
                timestamp=timestamp,
                rev_state=rev_state,
            )

    def _get_rev_state(
        self, cred_id: str, detail: dict, creds: dict, rev_states: dict
    ) -> tuple:
        """Get revocation state for a credential."""
        cred = creds[cred_id]
        rev_reg_id = cred.rev_reg_id
        timestamp = detail.get("timestamp") if rev_reg_id else None
        rev_state = None

        if timestamp:
            self._validate_rev_states(rev_states, rev_reg_id, cred_id)
            rev_state = rev_states[rev_reg_id].get(timestamp)
            if not rev_state:
                raise IndyHolderError(
                    f"No revocation states provided for credential '{cred_id}' "
                    f"with rev_reg_id '{rev_reg_id}' at timestamp {timestamp}"
                )

        return timestamp, rev_state

    def _validate_rev_states(self, rev_states: dict, rev_reg_id: str, cred_id: str):
        """Validate that revocation states are available."""
        if not rev_states or rev_reg_id not in rev_states:
            raise IndyHolderError(
                f"No revocation states provided for credential '{cred_id}' "
                f"with rev_reg_id '{rev_reg_id}'"
            )

    async def _create_final_presentation(
        self,
        presentation_request: dict,
        requested_credentials: dict,
        present_creds,
        schemas: dict,
        credential_definitions: dict,
    ) -> str:
        """Create the final presentation."""
        self_attest = requested_credentials.get("self_attested_attributes") or {}

        try:
            get_ls = self.get_link_secret
            if inspect.iscoroutinefunction(get_ls):
                secret = await get_ls()
            else:
                secret = get_ls()
            presentation = await asyncio.get_event_loop().run_in_executor(
                None,
                Presentation.create,
                presentation_request,
                present_creds,
                self_attest,
                secret,
                schemas.values(),
                credential_definitions.values(),
            )
        except CredxError as err:
            raise IndyHolderError(ERR_CREATE_PRESENTATION) from err

        return presentation.to_json()

    async def create_revocation_state(
        self,
        cred_rev_id: str,
        rev_reg_def: dict,
        rev_reg_delta: dict,
        timestamp: int,
        tails_file_path: str,
    ) -> str:
        """Create current revocation state for a received credential.

        This method creates the current revocation state for a received credential.
        It takes the credential revocation ID, revocation registry definition,
        revocation delta, delta timestamp, and tails file path as input parameters.

        Args:
            cred_rev_id (str): The credential revocation ID in the revocation registry.
            rev_reg_def (dict): The revocation registry definition.
            rev_reg_delta (dict): The revocation delta.
            timestamp (int): The delta timestamp.
            tails_file_path (str): The path to the tails file.

        Returns:
            str: The revocation state.

        Raises:
            IndyHolderError: If there is an error creating the revocation state.

        """
        try:
            rev_state = await asyncio.get_event_loop().run_in_executor(
                None,
                CredentialRevocationState.create,
                rev_reg_def,
                rev_reg_delta,
                int(cred_rev_id),
                timestamp,
                tails_file_path,
            )
        except CredxError as err:
            raise IndyHolderError(ERR_CREATE_REV_STATE) from err
        return rev_state.to_json()
