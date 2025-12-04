"""Module docstring."""

import asyncio
import inspect
import json
import logging
from typing import List, Optional, Sequence, Tuple, cast

from aries_askar import AskarError, AskarErrorCode, Entry, Key, KeyAlg, SeedMethod

from ..database_manager.dbstore import DBStoreError, DBStoreSession
from ..kanon.didcomm.v1 import pack_message, unpack_message
from ..kanon.profile_anon_kanon import KanonAnonCredsProfileSession
from ..ledger.base import BaseLedger
from ..ledger.endpoint_type import EndpointType
from ..ledger.error import LedgerConfigError
from ..storage.base import StorageDuplicateError, StorageNotFoundError, StorageRecord
from ..storage.kanon_storage import KanonStorage
from .base import BaseWallet, DIDInfo, KeyInfo
from .crypto import sign_message, validate_seed, verify_signed_message
from .did_info import INVITATION_REUSE_KEY
from .did_method import INDY, SOV, DIDMethod, DIDMethods
from .did_parameters_validation import DIDParametersValidation
from .error import WalletDuplicateError, WalletError, WalletNotFoundError
from .key_type import BLS12381G2, ED25519, P256, X25519, KeyType, KeyTypes
from .util import b58_to_bytes, bytes_to_b58

CATEGORY_DID = "did"
CATEGORY_CONFIG = "config"
RECORD_NAME_PUBLIC_DID = "default_public_did"

LOGGER = logging.getLogger(__name__)

ERR_MSG_NOT_PROVIDED = "Message not provided"
ERR_VERKEY_NOT_PROVIDED = "Verkey not provided"
ERR_UNKNOWN_KEY_TYPE = "Unknown key type {}"
LOG_FETCH_KEY = "Fetching key entry for verkey: %s"
LOG_FETCH_DID = "Fetching DID entry for: %s"
LOG_DID_NOT_FOUND = "DID not found: %s"
LOG_VERIFY_RESULT = "Verification result: %s"


class KanonWallet(BaseWallet):
    """Kanon wallet implementation."""

    def __init__(self, session: KanonAnonCredsProfileSession):
        """Initialize a new `KanonWallet` instance."""
        LOGGER.debug("Initializing KanonWallet with session: %s", session)
        self._session = session

    @property
    def session(self) -> KanonAnonCredsProfileSession:
        """Accessor for Kanon profile session instance."""
        LOGGER.debug("Accessing session property")
        return self._session

    def _get_dbstore_session(self) -> Optional[DBStoreSession]:
        """Get existing DBStore session from ProfileSession if available.

        This avoids creating new DBStore sessions when the ProfileSession
        already has one open, which prevents connection pool exhaustion.
        """
        if hasattr(self._session, "dbstore_handle") and self._session.dbstore_handle:
            handle = self._session.dbstore_handle
            # Verify it's actually a DBStoreSession, not an Askar Session
            if isinstance(handle, DBStoreSession):
                return handle
            LOGGER.warning(
                "dbstore_handle is not a DBStoreSession: %s", type(handle).__name__
            )
        return None

    async def create_signing_key(
        self,
        key_type: KeyType,
        seed: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> KeyInfo:
        """Create a new public/private signing keypair."""
        LOGGER.debug(
            "Entering create_signing_key with key_type: %s, seed: %s, metadata: %s",
            key_type,
            seed,
            metadata,
        )
        result = await self.create_key(key_type, seed, metadata)
        LOGGER.debug("create_signing_key completed with result: %s", result)
        return result

    async def create_key(
        self,
        key_type: KeyType,
        seed: Optional[str] = None,
        metadata: Optional[dict] = None,
        kid: Optional[str] = None,
    ) -> KeyInfo:
        """Create a new public/private keypair."""
        LOGGER.debug(
            "Entering create_key with key_type: %s, seed: %s, metadata: %s, kid: %s",
            key_type,
            seed,
            metadata,
            kid,
        )
        if metadata is None:
            metadata = {}
            LOGGER.debug("Metadata set to empty dict")

        tags = {"kid": kid} if kid else None
        LOGGER.debug("Tags set: %s", tags)

        try:
            LOGGER.debug("Creating keypair")
            keypair = _create_keypair(key_type, seed)
            verkey = bytes_to_b58(keypair.get_public_bytes())
            LOGGER.debug("Generated verkey: %s", verkey)
            LOGGER.debug("Inserting key into askar_handle")
            await _call_askar(
                self._session.askar_handle,
                "insert_key",
                verkey,
                keypair,
                metadata=json.dumps(metadata),
                tags=tags,
            )
            LOGGER.debug("Key inserted successfully")
        except AskarError as err:
            LOGGER.error("AskarError in create_key: %s", err)
            if err.code == AskarErrorCode.DUPLICATE:
                raise WalletDuplicateError(
                    "Verification key already present in wallet"
                ) from None
            raise WalletError("Error creating signing key") from err
        result = KeyInfo(verkey=verkey, metadata=metadata, key_type=key_type, kid=kid)
        LOGGER.debug("create_key completed with result: %s", result)
        return result

    async def assign_kid_to_key(self, verkey: str, kid: str) -> KeyInfo:
        """Assign a KID to a key."""
        LOGGER.debug("Entering assign_kid_to_key with verkey: %s, kid: %s", verkey, kid)
        try:
            LOGGER.debug(LOG_FETCH_KEY, verkey)
            key_entry = await _call_askar(
                self._session.askar_handle, "fetch_key", name=verkey, for_update=True
            )
            if not key_entry:
                LOGGER.error("Key entry not found for verkey: %s", verkey)
                raise WalletNotFoundError(f"No key entry found for verkey {verkey}")

            key = cast(Key, key_entry.key)
            metadata = cast(dict, key_entry.metadata)
            LOGGER.debug("Fetched key with metadata: %s", metadata)
            key_types = self.session.inject(KeyTypes)
            key_type = key_types.from_key_type(key.algorithm.value)
            if not key_type:
                LOGGER.error(f"{ERR_UNKNOWN_KEY_TYPE}".format(key.algorithm.value))
                raise WalletError(ERR_UNKNOWN_KEY_TYPE.format(key.algorithm.value))

            LOGGER.debug("Updating key with kid: %s", kid)
            await _call_askar(
                self._session.askar_handle, "update_key", name=verkey, tags={"kid": kid}
            )
            LOGGER.debug("Key updated successfully")
        except AskarError as err:
            LOGGER.error("AskarError in assign_kid_to_key: %s", err)
            raise WalletError("Error assigning kid to key") from err
        result = KeyInfo(verkey=verkey, metadata=metadata, key_type=key_type, kid=kid)
        LOGGER.debug("assign_kid_to_key completed with result: %s", result)
        return result

    async def get_key_by_kid(self, kid: str) -> KeyInfo:
        """Fetch a key by looking up its kid."""
        LOGGER.debug("Entering get_key_by_kid with kid: %s", kid)
        try:
            LOGGER.debug("Fetching all keys with kid: %s", kid)
            key_entries = await _call_askar(
                self._session.askar_handle,
                "fetch_all_keys",
                tag_filter={"kid": kid},
                limit=2,
            )
            if len(key_entries) > 1:
                LOGGER.error("More than one key found for kid: %s", kid)
                raise WalletDuplicateError(f"More than one key found by kid {kid}")
            elif not key_entries:
                LOGGER.error("No key found for kid: %s", kid)
                raise WalletNotFoundError(f"No key found for kid {kid}")

            entry = key_entries[0]
            key = cast(Key, entry.key)
            verkey = bytes_to_b58(key.get_public_bytes())
            metadata = cast(dict, entry.metadata)
            LOGGER.debug("Fetched key with verkey: %s, metadata: %s", verkey, metadata)
            key_types = self.session.inject(KeyTypes)
            key_type = key_types.from_key_type(key.algorithm.value)
            if not key_type:
                LOGGER.error(f"{ERR_UNKNOWN_KEY_TYPE}".format(key.algorithm.value))
                raise WalletError(ERR_UNKNOWN_KEY_TYPE.format(key.algorithm.value))
        except AskarError as err:
            LOGGER.error("AskarError in get_key_by_kid: %s", err)
            raise WalletError("Error fetching key by kid") from err
        result = KeyInfo(verkey=verkey, metadata=metadata, key_type=key_type, kid=kid)
        LOGGER.debug("get_key_by_kid completed with result: %s", result)
        return result

    async def get_signing_key(self, verkey: str) -> KeyInfo:
        """Fetch info for a signing keypair."""
        LOGGER.debug("Entering get_signing_key with verkey: %s", verkey)
        if not verkey:
            LOGGER.error("No verkey provided")
            raise WalletNotFoundError("No key identifier provided")
        try:
            LOGGER.debug(LOG_FETCH_KEY, verkey)
            key_entry = await _call_askar(self._session.askar_handle, "fetch_key", verkey)
            if not key_entry:
                LOGGER.error("Key not found for verkey: %s", verkey)
                raise WalletNotFoundError("Unknown key: {}".format(verkey))
            metadata = json.loads(key_entry.metadata or "{}")
            LOGGER.debug("Fetched metadata: %s", metadata)

            try:
                kid = key_entry.tags.get("kid")
                LOGGER.debug("Fetched kid: %s", kid)
            except Exception:
                kid = None
                LOGGER.debug("No kid found in tags")

            key = cast(Key, key_entry.key)
            key_types = self.session.inject(KeyTypes)
            key_type = key_types.from_key_type(key.algorithm.value)
            if not key_type:
                LOGGER.error(f"{ERR_UNKNOWN_KEY_TYPE}".format(key.algorithm.value))
                raise WalletError(ERR_UNKNOWN_KEY_TYPE.format(key.algorithm.value))
        except AskarError as err:
            LOGGER.error("AskarError in get_signing_key: %s", err)
            raise WalletError("Error fetching signing key") from err
        result = KeyInfo(verkey=verkey, metadata=metadata, key_type=key_type, kid=kid)
        LOGGER.debug("get_signing_key completed with result: %s", result)
        return result

    async def replace_signing_key_metadata(self, verkey: str, metadata: dict):
        """Replace the metadata associated with a signing keypair."""
        LOGGER.debug(
            "Entering replace_signing_key_metadata with verkey: %s, metadata: %s",
            verkey,
            metadata,
        )
        if not verkey:
            LOGGER.error("No verkey provided")
            raise WalletNotFoundError("No key identifier provided")

        try:
            LOGGER.debug(LOG_FETCH_KEY, verkey)
            key_entry = await _call_askar(
                self._session.askar_handle, "fetch_key", verkey, for_update=True
            )
            if not key_entry:
                LOGGER.error("Keypair not found for verkey: %s", verkey)
                raise WalletNotFoundError("Keypair not found")
            LOGGER.debug("Updating key metadata")
            await _call_askar(
                self._session.askar_handle,
                "update_key",
                verkey,
                metadata=json.dumps(metadata or {}),
                tags=key_entry.tags,
            )
            LOGGER.debug("Metadata updated successfully")
        except AskarError as err:
            LOGGER.error("AskarError in replace_signing_key_metadata: %s", err)
            raise WalletError("Error updating signing key metadata") from err
        LOGGER.debug("replace_signing_key_metadata completed")

    async def create_local_did(
        self,
        method: DIDMethod,
        key_type: KeyType,
        seed: Optional[str] = None,
        did: Optional[str] = None,
        metadata: Optional[dict] = None,
        session: Optional[DBStoreSession] = None,
    ) -> DIDInfo:
        """Create and store a new local DID.

        Args:
            method: The DID method to use
            key_type: The key type to use
            seed: Optional seed for key generation
            did: Optional DID to use
            metadata: Optional metadata to associate with the DID
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug(
            "create_local_did: method=%s, key_type=%s, seed=%s, did=%s, metadata=%s",
            method,
            key_type,
            seed,
            did,
            metadata,
        )
        did_validation = DIDParametersValidation(self._session.context.inject(DIDMethods))
        LOGGER.debug("Validating key type for method: %s", method)
        did_validation.validate_key_type(method, key_type)

        if not metadata:
            metadata = {}
            LOGGER.debug("Metadata set to empty dict")

        LOGGER.debug("Creating keypair")
        keypair = _create_keypair(key_type, seed)
        verkey_bytes = keypair.get_public_bytes()
        verkey = bytes_to_b58(verkey_bytes)
        LOGGER.debug("Generated verkey: %s", verkey)

        LOGGER.debug("Validating or deriving DID")
        did = did_validation.validate_or_derive_did(method, key_type, verkey_bytes, did)
        LOGGER.debug("Resulting DID: %s", did)

        try:
            LOGGER.debug("Inserting key into askar_handle")
            await _call_askar(
                self._session.askar_handle,
                "insert_key",
                verkey,
                keypair,
                metadata=json.dumps(metadata),
            )
            LOGGER.debug("Key inserted successfully")
        except AskarError as err:
            LOGGER.error("AskarError in create_local_did: %s", err)
            if err.code != AskarErrorCode.DUPLICATE:
                raise WalletError("Error inserting key") from err
            LOGGER.debug("Key already exists, proceeding")

        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._create_local_did_impl(
                    did, verkey, metadata, method, key_type, session
                )
        return await self._create_local_did_impl(
            did, verkey, metadata, method, key_type, session
        )

    async def _create_local_did_impl(
        self,
        did: str,
        verkey: str,
        metadata: dict,
        method: DIDMethod,
        key_type: KeyType,
        session: DBStoreSession,
    ) -> DIDInfo:
        """Internal implementation of create_local_did."""
        try:
            LOGGER.debug(LOG_FETCH_DID, did)
            item = await _call_store(session, "fetch", CATEGORY_DID, did, for_update=True)
            if item:
                did_info = item.value_json
                LOGGER.debug("Existing DID info: %s", did_info)
                if did_info.get("verkey") != verkey:
                    LOGGER.error("DID %s already present with different verkey", did)
                    raise WalletDuplicateError("DID already present in wallet")
                if did_info.get("metadata") != metadata:
                    LOGGER.debug("Updating metadata for existing DID")
                    did_info["metadata"] = metadata
                    await _call_store(
                        session,
                        "replace",
                        CATEGORY_DID,
                        did,
                        value_json=did_info,
                        tags=item.tags,
                    )
                    LOGGER.debug("Metadata updated")
            else:
                value_json = {
                    "did": did,
                    "method": method.method_name,
                    "verkey": verkey,
                    "verkey_type": key_type.key_type,
                    "metadata": metadata,
                }
                tags = {
                    "method": method.method_name,
                    "verkey": verkey,
                    "verkey_type": key_type.key_type,
                }
                if INVITATION_REUSE_KEY in metadata:
                    tags[INVITATION_REUSE_KEY] = "true"
                LOGGER.debug(
                    "Inserting new DID with value: %s, tags: %s", value_json, tags
                )
                await _call_store(
                    session,
                    "insert",
                    CATEGORY_DID,
                    did,
                    value_json=value_json,
                    tags=tags,
                )
                LOGGER.debug("New DID inserted")
        except DBStoreError as err:
            LOGGER.error("DBStoreError in create_local_did: %s", err)
            raise WalletError("Error when creating local DID") from err

        result = DIDInfo(
            did=did, verkey=verkey, metadata=metadata, method=method, key_type=key_type
        )
        LOGGER.debug("create_local_did completed with result: %s", result)
        return result

    async def store_did(
        self,
        did_info: DIDInfo,
        session: Optional[DBStoreSession] = None,
    ) -> DIDInfo:
        """Store a DID in the wallet.

        Args:
            did_info: The DID info to store
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug("Entering store_did with did_info: %s", did_info)
        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._store_did_impl(did_info, session)
        return await self._store_did_impl(did_info, session)

    async def _store_did_impl(
        self, did_info: DIDInfo, session: DBStoreSession
    ) -> DIDInfo:
        """Internal implementation of store_did."""
        try:
            LOGGER.debug("Checking if DID %s exists", did_info.did)
            item = await session.fetch(CATEGORY_DID, did_info.did, for_update=True)
            if item:
                LOGGER.error("DID %s already present", did_info.did)
                raise WalletDuplicateError("DID already present in wallet")
            else:
                value_json = {
                    "did": did_info.did,
                    "method": did_info.method.method_name,
                    "verkey": did_info.verkey,
                    "verkey_type": did_info.key_type.key_type,
                    "metadata": did_info.metadata,
                }
                tags = {
                    "method": did_info.method.method_name,
                    "verkey": did_info.verkey,
                    "verkey_type": did_info.key_type.key_type,
                }
                if INVITATION_REUSE_KEY in did_info.metadata:
                    tags[INVITATION_REUSE_KEY] = "true"
                LOGGER.debug("Inserting DID with value: %s, tags: %s", value_json, tags)
                await session.insert(
                    CATEGORY_DID,
                    did_info.did,
                    value_json=value_json,
                    tags=tags,
                )
                LOGGER.debug("DID stored successfully")
        except DBStoreError as err:
            LOGGER.error("DBStoreError in store_did: %s", err)
            raise WalletError("Error when storing DID") from err

        LOGGER.debug("store_did completed with result: %s", did_info)
        return did_info

    async def get_local_dids(
        self,
        session: Optional[DBStoreSession] = None,
    ) -> Sequence[DIDInfo]:
        """Get list of defined local DIDs.

        Args:
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug("Entering get_local_dids")
        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._get_local_dids_impl(session)
        return await self._get_local_dids_impl(session)

    async def _get_local_dids_impl(self, session: DBStoreSession) -> Sequence[DIDInfo]:
        """Internal implementation of get_local_dids."""
        ret = []
        try:
            LOGGER.debug("Fetching all DIDs")
            rows = await _call_store(session, "fetch_all", CATEGORY_DID)
            for item in rows:
                did_info = self._load_did_entry(item)
                ret.append(did_info)
                LOGGER.debug("Loaded DID: %s", did_info.did)
            LOGGER.debug("Fetched %d DIDs", len(ret))
        except DBStoreError as err:
            LOGGER.error("DBStoreError in get_local_dids: %s", err)
            raise WalletError("Error fetching local DIDs") from err
        LOGGER.debug("get_local_dids completed with %d results", len(ret))
        return ret

    async def get_local_did(
        self,
        did: str,
        session: Optional[DBStoreSession] = None,
    ) -> DIDInfo:
        """Find info for a local DID.

        Args:
            did: The DID to look up
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug("Entering get_local_did with did: %s", did)
        if not did:
            LOGGER.error("No DID provided")
            raise WalletNotFoundError("No identifier provided")
        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._get_local_did_impl(did, session)
        return await self._get_local_did_impl(did, session)

    async def _get_local_did_impl(self, did: str, session: DBStoreSession) -> DIDInfo:
        """Internal implementation of get_local_did."""
        try:
            LOGGER.debug(LOG_FETCH_DID, did)
            did_entry = await _call_store(session, "fetch", CATEGORY_DID, did)
        except DBStoreError as err:
            LOGGER.error("DBStoreError in get_local_did: %s", err)
            raise WalletError("Error when fetching local DID") from err
        if not did_entry:
            LOGGER.error(LOG_DID_NOT_FOUND, did)
            raise WalletNotFoundError("Unknown DID: {}".format(did))
        result = self._load_did_entry(did_entry)
        LOGGER.debug("get_local_did completed with result: %s", result)
        return result

    async def get_local_did_for_verkey(
        self,
        verkey: str,
        session: Optional[DBStoreSession] = None,
    ) -> DIDInfo:
        """Resolve a local DID from a verkey.

        Args:
            verkey: The verification key to look up
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug("Entering get_local_did_for_verkey with verkey: %s", verkey)
        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._get_local_did_for_verkey_impl(verkey, session)
        return await self._get_local_did_for_verkey_impl(verkey, session)

    async def _get_local_did_for_verkey_impl(
        self, verkey: str, session: DBStoreSession
    ) -> DIDInfo:
        """Internal implementation of get_local_did_for_verkey."""
        try:
            LOGGER.debug("Fetching DIDs for verkey: %s", verkey)
            dids = await _call_store(
                session, "fetch_all", CATEGORY_DID, {"verkey": verkey}
            )
        except DBStoreError as err:
            LOGGER.error("DBStoreError in get_local_did_for_verkey: %s", err)
            raise WalletError("Error when fetching local DID for verkey") from err
        if dids:
            ret_did = dids[0]
            ret_did_info = ret_did.value_json
            LOGGER.debug("Found DID info: %s", ret_did_info)
            if len(dids) > 1 and ret_did_info["did"].startswith("did:peer:4"):
                LOGGER.debug("Multiple DIDs found, checking for shorter did:peer:4")
                other_did = dids[1]  # Assume only 2
                other_did_info = other_did.value_json
                if len(other_did_info["did"]) < len(ret_did_info["did"]):
                    ret_did = other_did
                    ret_did_info = other_did.value_json
                    LOGGER.debug("Selected shorter DID: %s", ret_did_info["did"])
            result = self._load_did_entry(ret_did)
            LOGGER.debug("get_local_did_for_verkey completed with result: %s", result)
            return result
        LOGGER.error("No DID found for verkey: %s", verkey)
        raise WalletNotFoundError("No DID defined for verkey: {}".format(verkey))

    async def replace_local_did_metadata(
        self,
        did: str,
        metadata: dict,
        session: Optional[DBStoreSession] = None,
    ):
        """Replace metadata for a local DID.

        Args:
            did: The DID to update
            metadata: The new metadata
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug(
            "Entering replace_local_did_metadata with did: %s, metadata: %s",
            did,
            metadata,
        )
        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._replace_local_did_metadata_impl(did, metadata, session)
        return await self._replace_local_did_metadata_impl(did, metadata, session)

    async def _replace_local_did_metadata_impl(
        self, did: str, metadata: dict, session: DBStoreSession
    ):
        """Internal implementation of replace_local_did_metadata."""
        try:
            LOGGER.debug(LOG_FETCH_DID, did)
            item = await session.fetch(CATEGORY_DID, did, for_update=True)
            if not item:
                LOGGER.error(LOG_DID_NOT_FOUND, did)
                raise WalletNotFoundError("Unknown DID: {}".format(did)) from None
            entry_val = item.value_json
            LOGGER.debug("Current DID value: %s", entry_val)
            if entry_val["metadata"] != metadata:
                LOGGER.debug("Updating metadata")
                entry_val["metadata"] = metadata
                await session.replace(
                    CATEGORY_DID, did, value_json=entry_val, tags=item.tags
                )
                LOGGER.debug("Metadata replaced successfully")
        except DBStoreError as err:
            LOGGER.error("DBStoreError in replace_local_did_metadata: %s", err)
            raise WalletError("Error updating DID metadata") from err
        LOGGER.debug("replace_local_did_metadata completed")

    async def get_public_did(
        self,
        session: Optional[DBStoreSession] = None,
    ) -> DIDInfo:
        """Retrieve the public DID.

        Args:
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug("Entering get_public_did")
        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._get_public_did_impl(session)
        return await self._get_public_did_impl(session)

    async def _get_public_did_impl(self, session: DBStoreSession) -> DIDInfo:
        """Internal implementation of get_public_did."""
        public_did = None
        public_info = None
        public_item = None
        storage = KanonStorage(self._session)
        try:
            LOGGER.debug("Fetching public DID record")
            public_item = await storage.get_record(
                CATEGORY_CONFIG, RECORD_NAME_PUBLIC_DID, session=session
            )
            LOGGER.debug("Public DID record found")
        except StorageNotFoundError:
            LOGGER.debug("Public DID record not found, populating")
            dids = await self.get_local_dids(session=session)
            for info in dids:
                if info.metadata.get("public"):
                    public_did = info.did
                    public_info = info
                    LOGGER.debug("Found public DID in local DIDs: %s", public_did)
                    break
            try:
                LOGGER.debug("Adding public DID record with did: %s", public_did)
                await storage.add_record(
                    StorageRecord(
                        type=CATEGORY_CONFIG,
                        id=RECORD_NAME_PUBLIC_DID,
                        value=json.dumps({"did": public_did}),
                    ),
                    session=session,
                )
                LOGGER.debug("Public DID record added")
            except StorageDuplicateError:
                LOGGER.debug("Public DID record already exists, fetching")
                public_item = await storage.get_record(
                    CATEGORY_CONFIG, RECORD_NAME_PUBLIC_DID, session=session
                )
        if public_item:
            public_did = json.loads(public_item.value)["did"]
            LOGGER.debug("Public DID from record: %s", public_did)
            if public_did:
                try:
                    public_info = await self.get_local_did(public_did, session=session)
                    LOGGER.debug("Fetched public DID info: %s", public_info)
                except WalletNotFoundError:
                    LOGGER.warning("Public DID not found in local DIDs: %s", public_did)

        LOGGER.debug("get_public_did completed with result: %s", public_info)
        return public_info

    async def set_public_did(
        self,
        did: str | DIDInfo,
        session: Optional[DBStoreSession] = None,
    ) -> DIDInfo:
        """Assign the public DID.

        Args:
            did: The DID or DIDInfo to set as public
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug("Entering set_public_did with did: %s", did)
        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._set_public_did_impl(did, session)
        return await self._set_public_did_impl(did, session)

    async def _set_public_did_impl(
        self, did: str | DIDInfo, session: DBStoreSession
    ) -> DIDInfo:
        """Internal implementation of set_public_did."""
        if isinstance(did, str):
            try:
                LOGGER.debug("Fetching DID entry for: %s", did)
                item = await _call_store(
                    session, "fetch", CATEGORY_DID, did, for_update=True
                )
            except DBStoreError as err:
                LOGGER.error("DBStoreError in set_public_did: %s", err)
                raise WalletError("Error when fetching local DID") from err
            if not item:
                LOGGER.error("DID not found: %s", did)
                raise WalletNotFoundError("Unknown DID: {}".format(did))
            info = self._load_did_entry(item)
            LOGGER.debug("Loaded DID info: %s", info)
        else:
            info = did
            item = None
            LOGGER.debug("Using provided DIDInfo: %s", info)

        public = await self.get_public_did(session=session)
        LOGGER.debug("Current public DID: %s", public)
        if not public or public.did != info.did:
            storage = KanonStorage(self._session)
            if not info.metadata.get("posted"):
                metadata = {**info.metadata, "posted": True}
                LOGGER.debug("Updating metadata with posted=True: %s", metadata)
                if item:
                    entry_val = item.value_json
                    entry_val["metadata"] = metadata
                    try:
                        LOGGER.debug("Replacing DID entry")
                        await _call_store(
                            session,
                            "replace",
                            CATEGORY_DID,
                            did,
                            value_json=entry_val,
                            tags=item.tags,
                        )
                        LOGGER.debug("DID entry replaced")
                    except DBStoreError as err:
                        LOGGER.error("DBStoreError in set_public_did: %s", err)
                        raise WalletError("Error updating DID metadata") from err
                else:
                    LOGGER.debug("Replacing metadata via replace_local_did_metadata")
                    await self.replace_local_did_metadata(
                        info.did, metadata, session=session
                    )
                info = info._replace(metadata=metadata)
            LOGGER.debug("Updating public DID record to: %s", info.did)
            await storage.update_record(
                StorageRecord(
                    type=CATEGORY_CONFIG,
                    id=RECORD_NAME_PUBLIC_DID,
                    value="{}",
                ),
                value=json.dumps({"did": info.did}),
                tags={},
                session=session,
            )
            LOGGER.debug("Public DID set")
            public = info

        LOGGER.debug("set_public_did completed with result: %s", public)
        return public

    async def set_did_endpoint(
        self,
        did: str,
        endpoint: str,
        ledger: BaseLedger,
        endpoint_type: Optional[EndpointType] = None,
        write_ledger: bool = True,
        endorser_did: Optional[str] = None,
        routing_keys: Optional[List[str]] = None,
        session: Optional[DBStoreSession] = None,
    ):
        """Update the endpoint for a DID.

        Args:
            did: The DID to update
            endpoint: The new endpoint
            ledger: The ledger to update
            endpoint_type: The type of endpoint
            write_ledger: Whether to write to ledger
            endorser_did: Optional endorser DID
            routing_keys: Optional routing keys
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug(
            "Entering set_did_endpoint with did: %s, endpoint: %s", did, endpoint
        )

        # Create session if not provided for consistency across all operations
        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._set_did_endpoint_impl(
                    did,
                    endpoint,
                    ledger,
                    endpoint_type,
                    write_ledger,
                    endorser_did,
                    routing_keys,
                    session,
                )
        return await self._set_did_endpoint_impl(
            did,
            endpoint,
            ledger,
            endpoint_type,
            write_ledger,
            endorser_did,
            routing_keys,
            session,
        )

    async def _set_did_endpoint_impl(
        self,
        did: str,
        endpoint: str,
        ledger: BaseLedger,
        endpoint_type: Optional[EndpointType],
        write_ledger: bool,
        endorser_did: Optional[str],
        routing_keys: Optional[List[str]],
        session: DBStoreSession,
    ):
        """Internal implementation of set_did_endpoint."""
        LOGGER.debug("Fetching DID info for: %s", did)
        did_info = await self.get_local_did(did, session=session)
        if did_info.method not in (SOV, INDY):
            LOGGER.error("Invalid DID method: %s", did_info.method)
            raise WalletError(
                "Setting DID endpoint is only allowed for did:sov or did:indy DIDs"
            )
        metadata = {**did_info.metadata}
        if not endpoint_type:
            endpoint_type = EndpointType.ENDPOINT
            LOGGER.debug("Default endpoint_type set to ENDPOINT")
        if endpoint_type == EndpointType.ENDPOINT:
            metadata[endpoint_type.indy] = endpoint
            LOGGER.debug("Updated metadata with endpoint: %s", endpoint)

        wallet_public_didinfo = await self.get_public_did(session=session)
        LOGGER.debug("Public DID info: %s", wallet_public_didinfo)
        if (
            wallet_public_didinfo and wallet_public_didinfo.did == did
        ) or did_info.metadata.get("posted"):
            if not ledger:
                LOGGER.error("No ledger available for DID: %s", did)
                raise LedgerConfigError(f"No ledger available but DID {did} is public")
            if not ledger.read_only:
                LOGGER.debug("Updating endpoint on ledger")
                async with ledger:
                    attrib_def = await ledger.update_endpoint_for_did(
                        did,
                        endpoint,
                        endpoint_type,
                        write_ledger=write_ledger,
                        endorser_did=endorser_did,
                        routing_keys=routing_keys,
                    )
                    LOGGER.debug("Ledger update result: %s", attrib_def)
                    if not write_ledger:
                        LOGGER.debug(
                            "set_did_endpoint returning attrib_def: %s", attrib_def
                        )
                        return attrib_def

        LOGGER.debug("Replacing local DID metadata")
        await self.replace_local_did_metadata(did, metadata, session=session)
        LOGGER.debug("set_did_endpoint completed")

    async def rotate_did_keypair_start(
        self,
        did: str,
        next_seed: Optional[str] = None,
        session: Optional[DBStoreSession] = None,
    ) -> str:
        """Begin key rotation for DID.

        Args:
            did: The DID to rotate
            next_seed: Optional seed for the new key
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug(
            "Entering rotate_did_keypair_start with did: %s, next_seed: %s",
            did,
            next_seed,
        )
        did_methods = self._session.inject(DIDMethods)
        did_method = did_methods.from_did(did)
        if not did_method.supports_rotation:
            LOGGER.error(
                "DID method %s does not support rotation", did_method.method_name
            )
            raise WalletError(
                f"DID method '{did_method.method_name}' does not support key rotation"
            )

        LOGGER.debug("Creating new keypair")
        keypair = _create_keypair(ED25519, next_seed)
        verkey = bytes_to_b58(keypair.get_public_bytes())
        LOGGER.debug("Generated new verkey: %s", verkey)
        try:
            LOGGER.debug("Inserting new key")
            await _call_askar(self._session.askar_handle, "insert_key", verkey, keypair)
            LOGGER.debug("New key inserted")
        except AskarError as err:
            LOGGER.error("AskarError in rotate_did_keypair_start: %s", err)
            if err.code != AskarErrorCode.DUPLICATE:
                raise WalletError(
                    "Error when creating new keypair for local DID"
                ) from err
            LOGGER.debug("Key already exists, proceeding")

        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._rotate_did_keypair_start_impl(did, verkey, session)
        return await self._rotate_did_keypair_start_impl(did, verkey, session)

    async def _rotate_did_keypair_start_impl(
        self, did: str, verkey: str, session: DBStoreSession
    ) -> str:
        """Internal implementation of rotate_did_keypair_start."""
        try:
            LOGGER.debug(LOG_FETCH_DID, did)
            item = await _call_store(session, "fetch", CATEGORY_DID, did, for_update=True)
            if not item:
                LOGGER.error(LOG_DID_NOT_FOUND, did)
                raise WalletNotFoundError("Unknown DID: {}".format(did)) from None
            entry_val = item.value_json
            metadata = entry_val.get("metadata", {})
            metadata["next_verkey"] = verkey
            entry_val["metadata"] = metadata
            LOGGER.debug("Updating DID with next_verkey: %s", verkey)
            await _call_store(
                session,
                "replace",
                CATEGORY_DID,
                did,
                value_json=entry_val,
                tags=item.tags,
            )
            LOGGER.debug("DID updated")
        except DBStoreError as err:
            LOGGER.error("DBStoreError in rotate_did_keypair_start: %s", err)
            raise WalletError("Error updating DID metadata") from err

        LOGGER.debug("rotate_did_keypair_start completed with verkey: %s", verkey)
        return verkey

    async def rotate_did_keypair_apply(
        self,
        did: str,
        session: Optional[DBStoreSession] = None,
    ) -> DIDInfo:
        """Apply temporary keypair as main for DID.

        Args:
            did: The DID to apply key rotation for
            session: Optional existing session to reuse (avoids nested session creation)

        """
        LOGGER.debug("Entering rotate_did_keypair_apply with did: %s", did)
        if session is None:
            session = self._get_dbstore_session()
        if session is None:
            async with self._session.store.session() as session:
                return await self._rotate_did_keypair_apply_impl(did, session)
        return await self._rotate_did_keypair_apply_impl(did, session)

    async def _rotate_did_keypair_apply_impl(
        self, did: str, session: DBStoreSession
    ) -> DIDInfo:
        """Internal implementation of rotate_did_keypair_apply."""
        try:
            LOGGER.debug(LOG_FETCH_DID, did)
            item = await _call_store(session, "fetch", CATEGORY_DID, did, for_update=True)
            if not item:
                LOGGER.error(LOG_DID_NOT_FOUND, did)
                raise WalletNotFoundError("Unknown DID: {}".format(did)) from None
            entry_val = item.value_json
            metadata = entry_val.get("metadata", {})
            next_verkey = metadata.get("next_verkey")
            if not next_verkey:
                LOGGER.error("No next_verkey found for DID: %s", did)
                raise WalletError("Cannot rotate DID key: no next key established")
            LOGGER.debug("Applying next_verkey: %s", next_verkey)
            del metadata["next_verkey"]

            # Preserve the method and key_type from the stored DID entry
            method_name = entry_val.get("method")
            key_type_name = entry_val.get("verkey_type", "ed25519")

            entry_val["verkey"] = next_verkey
            item.tags["verkey"] = next_verkey
            await _call_store(
                session,
                "replace",
                CATEGORY_DID,
                did,
                value_json=entry_val,
                tags=item.tags,
            )
            LOGGER.debug("Key rotation applied")
        except DBStoreError as err:
            LOGGER.error("DBStoreError in rotate_did_keypair_apply: %s", err)
            raise WalletError("Error updating DID metadata") from err

        # Convert method and key_type strings to their respective objects
        did_methods: DIDMethods = self._session.inject(DIDMethods)
        key_types: KeyTypes = self._session.inject(KeyTypes)

        method = did_methods.from_method(method_name) if method_name else SOV
        key_type = key_types.from_key_type(key_type_name) or ED25519

        result = DIDInfo(
            did=did,
            verkey=next_verkey,
            metadata=metadata,
            method=method,
            key_type=key_type,
        )
        LOGGER.debug("rotate_did_keypair_apply completed with result: %s", result)
        return result

    async def sign_message(self, message: List[bytes] | bytes, from_verkey: str) -> bytes:
        """Sign message(s) using the private key."""
        LOGGER.debug("Entering sign_message with from_verkey: %s", from_verkey)
        if not message:
            LOGGER.error(ERR_MSG_NOT_PROVIDED)
            raise WalletError(ERR_MSG_NOT_PROVIDED)
        if not from_verkey:
            LOGGER.error(ERR_VERKEY_NOT_PROVIDED)
            raise WalletError(ERR_VERKEY_NOT_PROVIDED)
        try:
            LOGGER.debug("Fetching key for verkey: %s", from_verkey)
            keypair = await _call_askar(
                self._session.askar_handle, "fetch_key", from_verkey
            )
            if not keypair:
                LOGGER.error("Key not found: %s", from_verkey)
                raise WalletNotFoundError("Missing key for sign operation")
            key = keypair.key
            if key.algorithm == KeyAlg.BLS12_381_G2:
                LOGGER.debug("Signing with BLS12_381_G2")
                signature = sign_message(
                    message=message,
                    secret=key.get_secret_bytes(),
                    key_type=BLS12381G2,
                )
            else:
                LOGGER.debug("Signing with key algorithm: %s", key.algorithm)
                signature = key.sign_message(message)
            LOGGER.debug("Message signed successfully")
        except AskarError as err:
            LOGGER.error("AskarError in sign_message: %s", err)
            raise WalletError("Exception when signing message") from err
        LOGGER.debug("sign_message completed with signature length: %d", len(signature))
        return signature

    async def verify_message(
        self,
        message: List[bytes] | bytes,
        signature: bytes,
        from_verkey: str,
        key_type: KeyType,
    ) -> bool:
        """Verify a signature against the public key."""
        LOGGER.debug(
            "Entering verify_message with from_verkey: %s, key_type: %s",
            from_verkey,
            key_type,
        )
        if not from_verkey:
            LOGGER.error(ERR_VERKEY_NOT_PROVIDED)
            raise WalletError(ERR_VERKEY_NOT_PROVIDED)
        if not signature:
            LOGGER.error("Signature not provided")
            raise WalletError("Signature not provided")
        if not message:
            LOGGER.error(ERR_MSG_NOT_PROVIDED)
            raise WalletError(ERR_MSG_NOT_PROVIDED)

        verkey = b58_to_bytes(from_verkey)
        LOGGER.debug("Converted verkey to bytes")

        if key_type == ED25519:
            try:
                LOGGER.debug("Verifying with ED25519")
                pk = Key.from_public_bytes(KeyAlg.ED25519, verkey)
                verified = pk.verify_signature(message, signature)
                LOGGER.debug(LOG_VERIFY_RESULT, verified)
                return verified
            except AskarError as err:
                LOGGER.error("AskarError in verify_message: %s", err)
                raise WalletError("Exception when verifying message signature") from err
        elif key_type == P256:
            try:
                LOGGER.debug("Verifying with P256")
                pk = Key.from_public_bytes(KeyAlg.P256, verkey)
                verified = pk.verify_signature(message, signature)
                LOGGER.debug(LOG_VERIFY_RESULT, verified)
                return verified
            except AskarError as err:
                LOGGER.error("AskarError in verify_message: %s", err)
                raise WalletError("Exception when verifying message signature") from err

        LOGGER.debug("Verifying with generic method for key_type: %s", key_type)
        verified = verify_signed_message(
            message=message,
            signature=signature,
            verkey=verkey,
            key_type=key_type,
        )
        LOGGER.debug(LOG_VERIFY_RESULT, verified)
        return verified

    async def pack_message(
        self, message: str, to_verkeys: Sequence[str], from_verkey: Optional[str] = None
    ) -> bytes:
        """Pack a message for one or more recipients."""
        LOGGER.debug(
            "Entering pack_message with to_verkeys: %s, from_verkey: %s",
            to_verkeys,
            from_verkey,
        )
        if message is None:
            LOGGER.error(ERR_MSG_NOT_PROVIDED)
            raise WalletError(ERR_MSG_NOT_PROVIDED)
        try:
            if from_verkey:
                LOGGER.debug("Fetching key for from_verkey: %s", from_verkey)
                from_key_entry = await _call_askar(
                    self._session.askar_handle, "fetch_key", from_verkey
                )
                if not from_key_entry:
                    LOGGER.error("Key not found: %s", from_verkey)
                    raise WalletNotFoundError("Missing key for pack operation")
                from_key = from_key_entry.key
                LOGGER.debug("Fetched from_key")
            else:
                from_key = None
                LOGGER.debug("No from_verkey provided")
            LOGGER.debug("Packing message")
            packed_message = await asyncio.get_event_loop().run_in_executor(
                None, pack_message, to_verkeys, from_key, message
            )
            LOGGER.debug("Message packed successfully")
        except AskarError as err:
            LOGGER.error("AskarError in pack_message: %s", err)
            raise WalletError("Exception when packing message") from err
        LOGGER.debug("pack_message completed with packed length: %d", len(packed_message))
        return packed_message

    async def unpack_message(self, enc_message: bytes) -> Tuple[str, str, str]:
        """Unpack a message."""
        LOGGER.debug("Entering unpack_message")
        if not enc_message:
            LOGGER.error("Encoded message not provided")
            raise WalletError("Message not provided")
        try:
            LOGGER.debug("Unpacking message")
            result = unpack_message(self._session.askar_handle, enc_message)
            if inspect.isawaitable(result):
                unpacked_json, recipient, sender = await result
            else:
                unpacked_json, recipient, sender = result
            LOGGER.debug("Message unpacked: sender=%s, recipient=%s", sender, recipient)
        except AskarError as err:
            LOGGER.error("AskarError in unpack_message: %s", err)
            raise WalletError("Exception when unpacking message") from err
        result = (unpacked_json.decode("utf-8"), sender, recipient)
        LOGGER.debug("unpack_message completed with result: %s", result)
        return result

    def _load_did_entry(self, entry: Entry) -> DIDInfo:
        """Convert a DID record into DIDInfo format."""
        LOGGER.debug("Entering _load_did_entry")
        did_info = entry.value_json
        did_methods: DIDMethods = self._session.inject(DIDMethods)
        key_types: KeyTypes = self._session.inject(KeyTypes)
        result = DIDInfo(
            did=did_info["did"],
            verkey=did_info["verkey"],
            metadata=did_info.get("metadata"),
            method=did_methods.from_method(did_info.get("method", "sov")) or SOV,
            key_type=key_types.from_key_type(did_info.get("verkey_type", "ed25519"))
            or ED25519,
        )
        LOGGER.debug("_load_did_entry completed with result: %s", result)
        return result


def _create_keypair(key_type: KeyType, seed: str | bytes | None = None) -> Key:
    """Instantiate a new keypair with an optional seed value."""
    LOGGER.debug("Entering _create_keypair with key_type: %s", key_type)
    if key_type == ED25519:
        alg = KeyAlg.ED25519
        method = None
    elif key_type == X25519:
        alg = KeyAlg.X25519
        method = None
    elif key_type == P256:
        alg = KeyAlg.P256
        method = None
    elif key_type == BLS12381G2:
        alg = KeyAlg.BLS12_381_G2
        method = SeedMethod.BlsKeyGen
    else:
        LOGGER.error("Unsupported key algorithm: %s", key_type)
        raise WalletError(f"Unsupported key algorithm: {key_type}")
    LOGGER.debug("Selected algorithm: %s, method: %s", alg, method)

    if seed:
        try:
            if key_type in (ED25519, P256):
                LOGGER.debug("Using seed-derived key for %s", key_type)
                seed = validate_seed(seed)
                keypair = Key.from_secret_bytes(alg, seed)
            else:
                LOGGER.debug("Generating keypair from seed (method applied)")
                keypair = Key.from_seed(alg, seed, method=method)
            LOGGER.debug("Keypair created from seed")
        except AskarError as err:
            LOGGER.error("AskarError in _create_keypair: %s", err)
            if err.code == AskarErrorCode.INPUT:
                raise WalletError("Invalid seed for key generation") from err
            raise
    else:
        LOGGER.debug("Generating random keypair")
        keypair = Key.generate(alg)
        LOGGER.debug("Random keypair generated")
    LOGGER.debug("_create_keypair completed")
    return keypair


async def _call_askar(askar_handle, method_name: str, *args, **kwargs):
    method = getattr(askar_handle, method_name)
    if inspect.iscoroutinefunction(method):
        return await method(*args, **kwargs)
    return method(*args, **kwargs)


async def _call_store(session, method_name: str, *args, **kwargs):
    """Call DB session methods supporting both sync handle.* and async session.*.

    - For CRUD (insert, fetch, replace, remove) prefer synchronous handle methods.
    - For bulk ops (fetch_all, remove_all) prefer session method to allow test overrides.
    """
    prefer_session_first = method_name in {"fetch_all", "remove_all"}
    if prefer_session_first:
        smethod = getattr(session, method_name, None)
        if smethod is not None and callable(smethod):
            if inspect.iscoroutinefunction(smethod):
                handle = getattr(session, "handle", None)
                if handle is not None and hasattr(handle, method_name):
                    hmethod = getattr(handle, method_name)
                    if (
                        callable(hmethod)
                        and not inspect.iscoroutinefunction(hmethod)
                        and not inspect.isasyncgenfunction(hmethod)
                    ):
                        return hmethod(*args, **kwargs)
                return await smethod(*args, **kwargs)
            return smethod(*args, **kwargs)
    handle = getattr(session, "handle", None)
    if handle is not None and hasattr(handle, method_name):
        hmethod = getattr(handle, method_name)
        if callable(hmethod):
            if inspect.iscoroutinefunction(hmethod):
                return await hmethod(*args, **kwargs)
            return hmethod(*args, **kwargs)
    smethod = getattr(session, method_name)
    if inspect.iscoroutinefunction(smethod):
        return await smethod(*args, **kwargs)
    return smethod(*args, **kwargs)
