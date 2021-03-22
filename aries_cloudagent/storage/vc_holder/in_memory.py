"""Basic in-memory storage implementation of VC holder interface."""

from typing import Mapping, Sequence

from ...core.in_memory import InMemoryProfile

from ..in_memory import InMemoryStorage, InMemoryStorageSearch

from .base import VCHolder, VCRecordSearch
from .deser import load_credential, serialize_credential, VC_CRED_RECORD_TYPE
from .vc_record import VCRecord


class InMemoryVCHolder(VCHolder):
    """Basic in-memory storage class."""

    def __init__(self, profile: InMemoryProfile):
        """Initialize the in-memory VC holder instance."""
        self._profile = profile
        self._store = InMemoryStorage(profile)

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
        return InMemoryVCRecordSearch(search)


class InMemoryVCRecordSearch(VCRecordSearch):
    """In-memory search for VC records."""

    def __init__(self, search: InMemoryStorageSearch):
        """Initialize the in-memory VC record search."""
        self._search = search

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
