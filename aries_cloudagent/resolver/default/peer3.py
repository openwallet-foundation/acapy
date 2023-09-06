"""Peer DID Resolver.

Resolution is performed by converting did:peer:2 to did:peer:3 according to 
https://identity.foundation/peer-did-method-spec/#generation-method:~:text=Method%203%3A%20DID%20Shortening%20with%20SHA%2D256%20Hash
DID Document is just a did:peer:2 document (resolved by peer-did-python) where 
the did:peer:2 has been replaced with the did:peer:3.
"""

import re
from copy import deepcopy
from hashlib import sha256
from typing import Optional, Pattern, Sequence, Text, Union, Tuple, List
from multiformats import multibase, multicodec

from peerdid.dids import (
    DID,
    MalformedPeerDIDError,
    DIDDocument,
    DIDUrl,
)
from peerdid.keys import to_multibase, MultibaseFormat
from ...wallet.util import b64_to_bytes, bytes_to_b58

from ...connections.base_manager import BaseConnectionManager
from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ...storage.base import BaseStorage
from ...storage.error import StorageDuplicateError, StorageNotFoundError
from ...storage.record import StorageRecord

from ..base import BaseDIDResolver, DIDNotFound, ResolverType


class PeerDID3Resolver(BaseDIDResolver):
    """Peer DID Resolver."""

    def __init__(self):
        """Initialize Key Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Key DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Key DID Resolver."""
        return re.compile(r"^did:peer:3(.*)")

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a Key DID."""
        if did.startswith("did:peer:3"):
            # retrieve did_doc from storage using did:peer:3
            async with profile.session() as session:
                storage = session.inject(BaseStorage)
                record = await storage.find_record(
                    BaseConnectionManager.RECORD_TYPE_DID_DOCUMENT, {"did": did}
                )
                did_doc = DIDDocument.from_json(record.value)
        else:
            raise DIDNotFound(f"did is not a did:peer:3 {did}")

        return did_doc.dict()

    async def create_and_store_document(
        self, profile: Profile, peer_did_2_doc: DIDDocument
    ):
        if not peer_did_2_doc.id.startswith("did:peer:2"):
            raise MalformedPeerDIDError("did:peer:2 expected")

        dp3_doc = deepcopy(peer_did_2_doc)
        _convert_to_did_peer_3_document(dp3_doc)
        try:
            async with profile.session() as session:
                storage = session.inject(BaseStorage)
                record = await storage.find_record(
                    BaseConnectionManager.RECORD_TYPE_DID_DOCUMENT, {"did": dp3_doc.id}
                )
        except StorageNotFoundError:
            record = StorageRecord(
                BaseConnectionManager.RECORD_TYPE_DID_DOCUMENT,
                dp3_doc.to_json(),
                {"did": dp3_doc.id},
            )
            async with profile.session() as session:
                storage: BaseStorage = session.inject(BaseStorage)
                await storage.add_record(record)
        else:
            async with profile.session() as session:
                storage: BaseStorage = session.inject(BaseStorage)
                await storage.update_record(
                    record, dp3_doc.to_json(), {"did": dp3_doc.id}
                )
        await _reset_keys_from_did_doc(profile, dp3_doc)

        return dp3_doc


async def _reset_keys_from_did_doc(profile, did_doc):
    async with profile.session() as session:
        storage: BaseStorage = session.inject(BaseStorage)
        await storage.delete_all_records(
            BaseConnectionManager.RECORD_TYPE_DID_KEY, {"did": did_doc.id}
        )

    for vm in did_doc.verification_method or []:
        if vm.controller == did_doc.id:
            if vm.public_key_base58:
                await _add_key_for_did(profile, did_doc.id, vm.public_key_base58)
            if vm.public_key_multibase:
                pk = multibase.decode(vm.public_key_multibase)
                if len(pk) == 32:  # No multicodec prefix
                    pk = bytes_to_b58(pk)
                else:
                    codec, key = multicodec.unwrap(pk)
                    if codec == multicodec.multicodec("ed25519-pub"):
                        pk = bytes_to_b58(key)
                    else:
                        continue
                await _add_key_for_did(profile, did_doc.id, pk)


async def _add_key_for_did(profile, did: str, key: str):
    """Store a verkey for lookup against a DID.

    Args:
        did: The DID to associate with this key
        key: The verkey to be added
    """
    record = StorageRecord(
        BaseConnectionManager.RECORD_TYPE_DID_KEY, key, {"did": did, "key": key}
    )
    async with profile.session() as session:
        storage: BaseStorage = session.inject(BaseStorage)
        try:
            await storage.find_record(
                BaseConnectionManager.RECORD_TYPE_DID_KEY, {"key": key}
            )
        except StorageNotFoundError:
            await storage.add_record(record)
        except StorageDuplicateError:
            pass
            # "Key already associated with DID: %s; this is likely caused by "
            # "routing keys being erroneously stored in the past",


def _replace_all_values(input, org, new):
    for k, v in input.items():
        if isinstance(v, type(dict)):
            _replace_all_values(v, org, new)
        if isinstance(v, List):
            for i, item in enumerate(v):
                if isinstance(item, type(dict)):
                    _replace_all_values(item, org, new)
                elif (
                    isinstance(item, str)
                    or isinstance(item, DID)
                    or isinstance(item, DIDUrl)
                ):
                    v.pop(i)
                    v.append(item.replace(org, new, 1))
                elif hasattr(item, "__dict__"):
                    _replace_all_values(item.__dict__, org, new)
                else:
                    pass

        elif isinstance(v, str) or isinstance(v, DID) or isinstance(v, DIDUrl):
            input[k] = v.replace(org, new, 1)
        else:
            pass


def _convert_to_did_peer_3_document(dp2_document: DIDDocument) -> DIDDocument:
    content = to_multibase(
        sha256(dp2_document.id.lstrip("did:peer:2").encode()).digest(),
        MultibaseFormat.BASE58,
    )
    dp3 = DID("did:peer:3" + content)
    dp2 = dp2_document.id
    _replace_all_values(dp2_document.__dict__, dp2, dp3)

    # update document indexes
    new_indexes = {}
    for ind, val in dp2_document._index.items():
        new_indexes[ind.replace(dp2, dp3)] = val

    dp2_document._index = new_indexes
    return dp2_document
