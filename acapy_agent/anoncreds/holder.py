"""Anoncreds holder implementation."""

import asyncio
import json
import logging
from typing import Dict, Optional, Sequence, Tuple, Union

from anoncreds import (
    AnoncredsError,
    Credential,
    CredentialRequest,
    CredentialRevocationState,
    Presentation,
    PresentCredentials,
    W3cCredential,
    W3cPresentation,
    create_link_secret,
)
from aries_askar import AskarError, AskarErrorCode
from marshmallow import INCLUDE
from pyld import jsonld
from pyld.jsonld import JsonLdProcessor
from uuid_utils import uuid4

from ..askar.profile_anon import AskarAnoncredsProfile
from ..core.error import BaseError
from ..core.profile import Profile
from ..storage.vc_holder.base import VCHolder
from ..storage.vc_holder.vc_record import VCRecord
from ..vc.ld_proofs import DocumentLoader
from ..vc.vc_ld import VerifiableCredential
from ..wallet.error import WalletNotFoundError
from .error_messages import ANONCREDS_PROFILE_REQUIRED_MSG
from .models.credential_definition import CredDef
from .models.schema import AnonCredsSchema
from .registry import AnonCredsRegistry

LOGGER = logging.getLogger(__name__)

CATEGORY_CREDENTIAL = "credential"
CATEGORY_MASTER_SECRET = "master_secret"


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


class AnonCredsHolderError(BaseError):
    """Base class for holder exceptions."""


class AnonCredsHolder:
    """AnonCreds holder class."""

    MASTER_SECRET_ID = "default"
    RECORD_TYPE_MIME_TYPES = "attribute-mime-types"

    def __init__(self, profile: Profile):
        """Initialize an AnonCredsHolder instance.

        Args:
            profile: The active profile instance

        """
        self._profile = profile

    @property
    def profile(self) -> AskarAnoncredsProfile:
        """Accessor for the profile instance."""
        if not isinstance(self._profile, AskarAnoncredsProfile):
            raise ValueError(ANONCREDS_PROFILE_REQUIRED_MSG)

        return self._profile

    async def get_master_secret(self) -> str:
        """Get or create the default master secret."""

        while True:
            async with self.profile.session() as session:
                try:
                    record = await session.handle.fetch(
                        CATEGORY_MASTER_SECRET, AnonCredsHolder.MASTER_SECRET_ID
                    )
                except AskarError as err:
                    raise AnonCredsHolderError("Error fetching master secret") from err
                if record:
                    try:
                        # TODO should be able to use raw_value but memoryview
                        # isn't accepted by cred.process
                        secret = record.value.decode("ascii")
                    except AnoncredsError as err:
                        raise AnonCredsHolderError("Error loading master secret") from err
                    break
                else:
                    try:
                        secret = create_link_secret()
                    except AnoncredsError as err:
                        raise AnonCredsHolderError(
                            "Error creating master secret"
                        ) from err
                    try:
                        await session.handle.insert(
                            CATEGORY_MASTER_SECRET,
                            AnonCredsHolder.MASTER_SECRET_ID,
                            secret,
                        )
                    except AskarError as err:
                        if err.code != AskarErrorCode.DUPLICATE:
                            raise AnonCredsHolderError(
                                "Error saving master secret"
                            ) from err
                        # else: lost race to create record, retry
                    else:
                        break
        return secret

    async def create_credential_request(
        self, credential_offer: dict, credential_definition: CredDef, holder_did: str
    ) -> Tuple[str, str]:
        """Create a credential request for the given credential offer.

        Args:
            credential_offer: The credential offer to create request for
            credential_definition: The credential definition to create an offer for
            holder_did: the DID of the agent making the request (may not be a real DID)

        Returns:
            A tuple of the credential request and credential request metadata

        """
        try:
            secret = await self.get_master_secret()
            (
                cred_req,
                cred_req_metadata,
            ) = await asyncio.get_event_loop().run_in_executor(
                None,
                CredentialRequest.create,
                holder_did,
                None,
                credential_definition.to_native(),
                secret,
                AnonCredsHolder.MASTER_SECRET_ID,
                credential_offer,
            )
        except AnoncredsError as err:
            raise AnonCredsHolderError("Error creating credential request") from err
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
            secret = await self.get_master_secret()
            cred = Credential.load(credential_data)
            cred_recvd = await asyncio.get_event_loop().run_in_executor(
                None,
                cred.process,
                credential_request_metadata,
                secret,
                credential_definition,
                rev_reg_def,
            )
        except AnoncredsError as err:
            raise AnonCredsHolderError("Error processing received credential") from err

        return await self._finish_store_credential(
            credential_definition,
            cred_recvd,
            credential_request_metadata,
            credential_attr_mime_types,
            credential_id,
            rev_reg_def,
        )

    async def _finish_store_credential(
        self,
        credential_definition: dict,
        cred_recvd: Credential,
        credential_request_metadata: dict,
        credential_attr_mime_types: Optional[dict] = None,
        credential_id: Optional[str] = None,
        rev_reg_def: Optional[dict] = None,
    ) -> str:
        credential_data = cred_recvd.to_dict()
        registry = self.profile.inject(AnonCredsRegistry)
        schema_info = await registry.get_schema_info_by_id(
            self.profile, credential_data["schema_id"]
        )

        credential_id = credential_id or str(uuid4())
        tags = {
            "schema_id": credential_data["schema_id"],
            "schema_issuer_did": schema_info.issuer_id,
            "schema_name": schema_info.name,
            "schema_version": schema_info.version,
            "issuer_did": credential_definition["issuerId"],
            "cred_def_id": cred_recvd.cred_def_id,
            "rev_reg_id": cred_recvd.rev_reg_id or "None",
        }

        # FIXME - sdk has some special handling for fully qualified DIDs here

        mime_types = {}
        for k, attr_value in credential_data["values"].items():
            attr_name = _normalize_attr_name(k)
            # tags[f"attr::{attr_name}::marker"] = "1"
            tags[f"attr::{attr_name}::value"] = attr_value["raw"]
            if credential_attr_mime_types and k in credential_attr_mime_types:
                mime_types[k] = credential_attr_mime_types[k]

        try:
            async with self.profile.transaction() as txn:
                await txn.handle.insert(
                    CATEGORY_CREDENTIAL,
                    credential_id,
                    cred_recvd.to_json_buffer(),
                    tags=tags,
                )
                if mime_types:
                    await txn.handle.insert(
                        AnonCredsHolder.RECORD_TYPE_MIME_TYPES,
                        credential_id,
                        value_json=mime_types,
                    )
                await txn.commit()
        except AskarError as err:
            raise AnonCredsHolderError("Error storing credential") from err

        return credential_id

    async def store_credential_w3c(
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
            secret = await self.get_master_secret()
            cred_w3c = W3cCredential.load(credential_data)
            cred_w3c_recvd = await asyncio.get_event_loop().run_in_executor(
                None,
                cred_w3c.process,
                credential_request_metadata,
                secret,
                credential_definition,
                rev_reg_def,
            )
            cred_legacy = Credential.from_w3c(cred_w3c)
            cred_recvd = await asyncio.get_event_loop().run_in_executor(
                None,
                cred_legacy.process,
                credential_request_metadata,
                secret,
                credential_definition,
                rev_reg_def,
            )
        except AnoncredsError as err:
            raise AnonCredsHolderError("Error processing received credential") from err

        credential_id = await self._finish_store_credential(
            credential_definition,
            cred_recvd,
            credential_request_metadata,
            credential_attr_mime_types,
            credential_id,
            rev_reg_def,
        )

        # also store in W3C format
        # create VC record for storage
        cred_w3c_recvd_dict = cred_w3c_recvd.to_dict()
        cred_w3c_recvd_dict["proof"] = cred_w3c_recvd_dict["proof"][0]
        cred_w3c_recvd_vc = VerifiableCredential.deserialize(
            cred_w3c_recvd_dict, unknown=INCLUDE
        )

        # Saving expanded type as a cred_tag
        document_loader = self.profile.inject(DocumentLoader)
        expanded = jsonld.expand(
            cred_w3c_recvd_dict, options={"documentLoader": document_loader}
        )
        types = JsonLdProcessor.get_values(
            expanded[0],
            "@type",
        )

        vc_record = VCRecord(
            contexts=cred_w3c_recvd_vc.context_urls,
            expanded_types=types,
            issuer_id=cred_w3c_recvd_vc.issuer_id,
            subject_ids=cred_w3c_recvd_vc.credential_subject_ids,
            schema_ids=[],  # Schemas not supported yet
            proof_types=[cred_w3c_recvd_vc.proof.type],
            cred_value=cred_w3c_recvd_vc.serialize(),
            given_id=cred_w3c_recvd_vc.id,
            record_id=credential_id,
            cred_tags=None,  # Tags should be derived from credential values
        )

        # save credential in storage
        async with self.profile.session() as session:
            vc_holder = session.inject(VCHolder)

            await vc_holder.store_credential(vc_record)

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
            rows = self.profile.store.scan(
                category=CATEGORY_CREDENTIAL,
                tag_filter=wql,
                offset=offset,
                limit=limit,
                profile=self.profile.settings.get("wallet.askar_profile"),
            )
            async for row in rows:
                cred = Credential.load(row.raw_value)
                result.append(_make_cred_info(row.name, cred))
        except AskarError as err:
            raise AnonCredsHolderError("Error retrieving credentials") from err
        except AnoncredsError as err:
            raise AnonCredsHolderError("Error loading stored credential") from err

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
        if not referents:
            referents = (
                *presentation_request["requested_attributes"],
                *presentation_request["requested_predicates"],
            )
        extra_query = extra_query or {}
        creds = {}
        for reft in referents:
            names = set()
            if reft in presentation_request["requested_attributes"]:
                attr = presentation_request["requested_attributes"][reft]
                if "name" in attr:
                    names.add(_normalize_attr_name(attr["name"]))
                elif "names" in attr:
                    names.update(_normalize_attr_name(name) for name in attr["names"])
                # for name in names:
                #     tag_filter[f"attr::{_normalize_attr_name(name)}::marker"] = "1"
                restr = attr.get("restrictions")
            elif reft in presentation_request["requested_predicates"]:
                pred = presentation_request["requested_predicates"][reft]
                if "name" in pred:
                    names.add(_normalize_attr_name(pred["name"]))
                # tag_filter[f"attr::{_normalize_attr_name(name)}::marker"] = "1"
                restr = pred.get("restrictions")
            else:
                raise AnonCredsHolderError(
                    f"Unknown presentation request referent: {reft}"
                )

            tag_filter = {"$exist": [f"attr::{name}::value" for name in names]}
            if restr:
                # FIXME check if restr is a list or dict? validate WQL format
                tag_filter = {"$and": [tag_filter] + restr}
            if extra_query:
                tag_filter = {"$and": [tag_filter, extra_query]}

            rows = self.profile.store.scan(
                category=CATEGORY_CREDENTIAL,
                tag_filter=tag_filter,
                offset=offset,
                limit=limit,
                profile=self.profile.settings.get("wallet.askar_profile"),
            )
            async for row in rows:
                if row.name in creds:
                    creds[row.name]["presentation_referents"].add(reft)
                else:
                    cred_info = _make_cred_info(row.name, Credential.load(row.raw_value))
                    creds[row.name] = {
                        "cred_info": cred_info,
                        "interval": presentation_request.get("non_revoked"),
                        "presentation_referents": {reft},
                    }

        for cred in creds.values():
            cred["presentation_referents"] = list(cred["presentation_referents"])

        return list(creds.values())

    async def get_credential(self, credential_id: str) -> str:
        """Get a credential stored in the wallet.

        Args:
            credential_id: Credential id to retrieve

        """
        cred = await self._get_credential(credential_id)
        return json.dumps(_make_cred_info(credential_id, cred))

    async def _get_credential(self, credential_id: str) -> Credential:
        """Get an unencoded Credential instance from the store."""
        try:
            async with self.profile.session() as session:
                cred = await session.handle.fetch(CATEGORY_CREDENTIAL, credential_id)
        except AskarError as err:
            raise AnonCredsHolderError("Error retrieving credential") from err

        if not cred:
            raise WalletNotFoundError(
                f"Credential {credential_id} not found in wallet {self.profile.name}"
            )

        try:
            return Credential.load(cred.raw_value)
        except AnoncredsError as err:
            raise AnonCredsHolderError("Error loading requested credential") from err

    async def credential_revoked(
        self,
        credential_id: str,
        timestamp_from: Optional[int] = None,
        timestamp_to: Optional[int] = None,
    ) -> bool:
        """Check ledger for revocation status of credential by credential id.

        Args:
            ledger (BaseLedger): The ledger to check for revocation status.
            credential_id (str): The ID of the credential to check.
            timestamp_from (int, optional): The earliest timestamp to consider for
                revocation status. Defaults to None.
            timestamp_to (int, optional): The latest timestamp to consider for revocation
                status. Defaults to None.

        Returns:
            bool: True if the credential is revoked, False otherwise.
        """
        cred = await self._get_credential(credential_id)
        rev_reg_id = cred.rev_reg_id

        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        rev_list = (
            await anoncreds_registry.get_revocation_list(
                self.profile, rev_reg_id, timestamp_from, timestamp_to
            )
        ).revocation_list

        set_revoked = {
            index for index, value in enumerate(rev_list.revocation_list) if value == 1
        }

        return cred.rev_reg_index in set_revoked

    async def delete_credential(self, credential_id: str):
        """Remove a credential stored in the wallet.

        Args:
            credential_id: Credential id to remove

        """
        try:
            async with self.profile.session() as session:
                await session.handle.remove(CATEGORY_CREDENTIAL, credential_id)
                await session.handle.remove(
                    AnonCredsHolder.RECORD_TYPE_MIME_TYPES, credential_id
                )
        except AskarError as err:
            raise AnonCredsHolderError(
                "Error deleting credential", error_code=err.code
            ) from err  # noqa: E501

    async def get_mime_type(
        self, credential_id: str, attr: Optional[str] = None
    ) -> Union[dict, str]:
        """Get MIME type per attribute (or for all attributes).

        Args:
            credential_id: credential id
            attr: attribute of interest or omit for all

        Returns: Attribute MIME type or dict mapping attribute names to MIME types
            attr_meta_json = all_meta.tags.get(attr)

        """
        try:
            async with self.profile.session() as session:
                mime_types_record = await session.handle.fetch(
                    AnonCredsHolder.RECORD_TYPE_MIME_TYPES,
                    credential_id,
                )
        except AskarError as err:
            raise AnonCredsHolderError("Error retrieving credential mime types") from err
        values = mime_types_record and mime_types_record.value_json
        if values:
            return values.get(attr) if attr else values

    async def create_presentation(
        self,
        presentation_request: dict,
        requested_credentials: dict,
        schemas: Dict[str, AnonCredsSchema],
        credential_definitions: Dict[str, CredDef],
        rev_states: Optional[dict] = None,
    ) -> str:
        """Get credentials stored in the wallet.

        Args:
            presentation_request: Valid indy format presentation request
            requested_credentials: Anoncreds format requested credentials
            schemas: Anoncreds formatted schemas JSON
            credential_definitions: Anoncreds formatted credential definitions JSON
            rev_states: Anoncreds format revocation states JSON

        """

        creds: Dict[str, Credential] = {}

        def get_rev_state(cred_id: str, detail: dict):
            cred = creds[cred_id]
            rev_reg_id = cred.rev_reg_id
            timestamp = detail.get("timestamp") if rev_reg_id else None
            rev_state = None
            if timestamp:
                if not rev_states or rev_reg_id not in rev_states:
                    raise AnonCredsHolderError(
                        f"No revocation states provided for credential '{cred_id}' "
                        f"with rev_reg_id '{rev_reg_id}'"
                    )
                rev_state = rev_states[rev_reg_id].get(timestamp)
                if not rev_state:
                    raise AnonCredsHolderError(
                        f"No revocation states provided for credential '{cred_id}' "
                        f"with rev_reg_id '{rev_reg_id}' at timestamp {timestamp}"
                    )
            return timestamp, rev_state

        self_attest = requested_credentials.get("self_attested_attributes") or {}
        present_creds = PresentCredentials()
        req_attrs = requested_credentials.get("requested_attributes") or {}
        for reft, detail in req_attrs.items():
            cred_id = detail["cred_id"]
            if cred_id not in creds:
                # NOTE: could be optimized if multiple creds are requested
                creds[cred_id] = await self._get_credential(cred_id)
            timestamp, rev_state = get_rev_state(cred_id, detail)
            present_creds.add_attributes(
                creds[cred_id],
                reft,
                reveal=detail["revealed"],
                timestamp=timestamp,
                rev_state=rev_state,
            )
        req_preds = requested_credentials.get("requested_predicates") or {}
        for reft, detail in req_preds.items():
            cred_id = detail["cred_id"]
            if cred_id not in creds:
                # NOTE: could be optimized if multiple creds are requested
                creds[cred_id] = await self._get_credential(cred_id)
            timestamp, rev_state = get_rev_state(cred_id, detail)
            present_creds.add_predicates(
                creds[cred_id],
                reft,
                timestamp=timestamp,
                rev_state=rev_state,
            )

        try:
            secret = await self.get_master_secret()
            presentation = await asyncio.get_event_loop().run_in_executor(
                None,
                Presentation.create,
                presentation_request,
                present_creds,
                self_attest,
                secret,
                {schema_id: schema.to_native() for schema_id, schema in schemas.items()},
                {
                    cred_def_id: cred_def.to_native()
                    for cred_def_id, cred_def in credential_definitions.items()
                },
            )
        except AnoncredsError as err:
            raise AnonCredsHolderError("Error creating presentation") from err

        return presentation.to_json()

    async def create_presentation_w3c(
        self,
        presentation_request: dict,
        requested_credentials_w3c: list,
        credentials_w3c_metadata: list,
        schemas: Dict[str, AnonCredsSchema],
        credential_definitions: Dict[str, CredDef],
        rev_states: Optional[dict] = None,
    ) -> dict:
        """Get credentials stored in the wallet.

        Args:
            presentation_request: Valid indy format presentation request
            requested_credentials_w3c: W3C format requested credentials
            credentials_w3c_metadata: W3C format credential metadata
            schemas: Anoncreds formatted schemas JSON
            credential_definitions: Anoncreds formatted credential definitions JSON
            rev_states: Anoncreds format revocation states JSON

        """
        present_creds = PresentCredentials()
        for idx, cred in enumerate(requested_credentials_w3c):
            meta = credentials_w3c_metadata[idx]
            rev_state = rev_states.get(meta["rev_reg_id"]) if rev_states else None
            for attr in meta["proof_attrs"]:
                present_creds.add_attributes(
                    cred,
                    attr,
                    reveal=True,
                    timestamp=meta.get("timestamp"),
                    rev_state=rev_state,
                )

            for pred in meta["proof_preds"]:
                present_creds.add_predicates(
                    cred,
                    pred,
                    timestamp=meta.get("timestamp"),
                    rev_state=rev_state,
                )

        try:
            secret = await self.get_master_secret()
            presentation = W3cPresentation.create(
                presentation_request,
                present_creds,
                secret,
                schemas,
                credential_definitions,
            )
        except AnoncredsError as err:
            raise AnonCredsHolderError("Error creating presentation") from err

        return presentation.to_dict()

    async def create_revocation_state(
        self,
        cred_rev_id: str,
        rev_reg_def: dict,
        rev_list: dict,
        tails_file_path: str,
    ) -> str:
        """Create current revocation state for a received credential.

        Args:
            cred_rev_id: credential revocation id in revocation registry
            rev_reg_def: revocation registry definition
            rev_list: revocation registry
            tails_file_path: path to tails file

        Returns:
            the revocation state

        """

        try:
            rev_state = await asyncio.get_event_loop().run_in_executor(
                None,
                CredentialRevocationState.create,
                rev_reg_def,
                rev_list,
                int(cred_rev_id),
                tails_file_path,
            )
        except AnoncredsError as err:
            raise AnonCredsHolderError("Error creating revocation state") from err
        return rev_state.to_json()
