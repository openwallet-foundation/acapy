"""Indy-SDK storage implementation of VC holder interface."""

from aries_cloudagent.storage.record import StorageRecord
from typing import Mapping, Sequence

from ...indy.sdk.wallet_setup import IndyOpenWallet

from ..indy import IndySdkStorage, IndySdkStorageSearch

from .base import VCHolder, VCRecordSearch
from .vc_record import VCRecord

VC_CRED_RECORD_TYPE = "vc_cred"


def load_credential(record: StorageRecord) -> VCRecord:
    """Convert an Indy-SDK stored record into a VC record."""
    tags = {}
    contexts = []
    types = []
    schema_ids = []
    subject_ids = []
    issuer_id = None
    given_id = None
    for tagname, tagval in (record.tags or {}).items():
        if tagname.startswith("ctxt:"):
            contexts.append(tagname[5:])
        elif tagname.startswith("type:"):
            types.append(tagname[5:])
        elif tagname.startswith("schm:"):
            schema_ids.append(tagname[5:])
        elif tagname.startswith("subj:"):
            subject_ids.append(tagname[5:])
        elif tagname == "issuer_id":
            issuer_id = tagval
        elif tagname == "given_id":
            given_id = tagval
        else:
            tags[tagname] = tagval
    return VCRecord(
        contexts=contexts,
        types=types,
        schema_ids=schema_ids,
        issuer_id=issuer_id,
        subject_ids=subject_ids,
        value=record.value,
        given_id=given_id,
        tags=tags,
        record_id=record.id,
    )


def serialize_credential(cred: VCRecord) -> StorageRecord:
    """Convert a VC record into an in-memory stored record."""
    tags = {}
    for ctx_val in cred.contexts:
        tags[f"ctxt:{ctx_val}"] = "1"
    for type_val in cred.types:
        tags[f"type:{type_val}"] = "1"
    for schema_val in cred.schema_ids:
        tags[f"schm:{schema_val}"] = "1"
    for subj_id in cred.subject_ids:
        tags[f"subj:{subj_id}"] = "1"
    if cred.issuer_id:
        tags["issuer_id"] = cred.issuer_id
    if cred.given_id:
        tags["given_id"] = cred.given_id
    if cred.tags:
        tags.update(cred.tags)
    return StorageRecord(VC_CRED_RECORD_TYPE, cred.value, tags, cred.record_id)


class IndySdkVCHolder(VCHolder):
    """Indy-SDK in-memory storage class."""

    def __init__(self, wallet: IndyOpenWallet):
        """Initialize the Indy-SDK VC holder instance."""
        self._wallet = wallet
        self._store = IndySdkStorage(wallet)

    async def store_credential(self, cred: VCRecord):
        """
        Add a new VC record to the store.

        Args:
            cred: The VCRecord instance to store
        Raises:
            StorageDuplicateError: If the record_id is not unique

        """
        record = serialize_credential(cred)
        await self._store.add_record(record)

    async def retrieve_credential_by_id(self, record_id: str) -> VCRecord:
        """
        Fetch a VC record by its record ID.

        Raises:
            StorageNotFoundError: If the record is not found

        """
        record = await self._store.get_record(VC_CRED_RECORD_TYPE, record_id)
        return load_credential(record)

    async def retrieve_credential_by_given_id(self, given_id: str) -> VCRecord:
        """
        Fetch a VC record by its given ID ('id' property).

        Raises:
            StorageNotFoundError: If the record is not found

        """
        record = await self._store.find_record(
            VC_CRED_RECORD_TYPE, {"given_id": given_id}
        )
        return load_credential(record)

    async def delete_credential(self, cred: VCRecord):
        """
        Remove a previously-stored VC record.

        Raises:
            StorageNotFoundError: If the record is not found

        """
        await self._store.delete_record(serialize_credential(cred))

    def search_credentials(
        self,
        contexts: Sequence[str] = None,
        types: Sequence[str] = None,
        schema_ids: str = None,
        issuer_id: str = None,
        subject_id: str = None,
        tag_query: Mapping = None,
    ) -> "VCRecordSearch":
        """
        Start a new VC record search.

        Args:
            contexts: An inclusive list of JSON-LD contexts to filter for
            types: An inclusive list of JSON-LD types to filter for
            schema_ids: An inclusive list of credential schema identifiers
            issuer_id: The ID of the credential issuer
            subject_id: The ID of one of the credential subjects
            tag_query: A tag filter clause

        """
        query = {}
        if contexts:
            for ctx_val in contexts:
                query[f"ctxt:{ctx_val}"] = "1"
        if types:
            for type_val in types:
                query[f"type:{type_val}"] = "1"
        if schema_ids:
            for schema_val in schema_ids:
                query[f"schm:{schema_val}"] = "1"
        if subject_id:
            query[f"subj:{subject_id}"] = "1"
        if issuer_id:
            query["issuer_id"] = issuer_id
        if tag_query:
            query.update(tag_query)
        search = self._store.search_records(VC_CRED_RECORD_TYPE, query)
        return IndySdkVCRecordSearch(search)


class IndySdkVCRecordSearch(VCRecordSearch):
    """Indy-SDK storage search for VC records."""

    def __init__(self, search: IndySdkStorageSearch):
        """Initialize the Indy-SDK VC record search."""
        self._search = search

    async def close(self):
        """Dispose of the search query."""
        await self._search.close()

    async def fetch(self, max_count: int = None) -> Sequence[VCRecord]:
        """
        Fetch the next list of VC records from the store.

        Args:
            max_count: Max number of records to return. If not provided,
              defaults to the backend's preferred page size

        Returns:
            A list of `VCRecord` instances

        """
        rows = await self._search.fetch(max_count)
        return [load_credential(r) for r in rows]
