"""Abstract interfaces for VC holder implementations."""

from abc import ABC, abstractmethod
from typing import Mapping, Sequence

from .vc_record import VCRecord


class VCHolder(ABC):
    """Abstract base class for a verifiable credential holder."""

    @abstractmethod
    async def store_credential(self, cred: VCRecord):
        """
        Add a new VC record to the store.

        Args:
            cred: The VCRecord instance to store
        Raises:
            StorageDuplicateError: If the record_id is not unique

        """

    @abstractmethod
    async def retrieve_credential_by_id(self, record_id: str) -> VCRecord:
        """
        Fetch a VC record by its record ID.

        Raises:
            StorageNotFoundError: If the record is not found

        """

    @abstractmethod
    async def retrieve_credential_by_given_id(self, given_id: str) -> VCRecord:
        """
        Fetch a VC record by its given ID ('id' property).

        Raises:
            StorageNotFoundError: If the record is not found

        """

    @abstractmethod
    async def delete_credential(self, cred: VCRecord):
        """
        Remove a previously-stored VC record.

        Raises:
            StorageNotFoundError: If the record is not found

        """

    @abstractmethod
    def build_type_or_schema_query(self, uri_list: Sequence[str]) -> dict:
        """
        Build and return backend-specific type_or_schema_query.

        Args:
            uri_list: List of schema uri from input_descriptor
        """

    @abstractmethod
    def search_credentials(
        self,
        contexts: Sequence[str] = None,
        types: Sequence[str] = None,
        schema_ids: Sequence[str] = None,
        issuer_id: str = None,
        subject_ids: Sequence[str] = None,
        proof_types: Sequence[str] = None,
        given_id: str = None,
        tag_query: Mapping = None,
    ) -> "VCRecordSearch":
        """
        Start a new VC record search.

        Args:
            contexts: An inclusive list of JSON-LD contexts to match
            types: An inclusive list of JSON-LD types to match
            schema_ids: An inclusive list of credential schema identifiers
            issuer_id: The ID of the credential issuer
            subject_ids: The IDs of any credential subjects all of which to match
            proof_types: The signature suite types used for the proof objects.
            given_id: The given id of the credential
            tag_query: A tag filter clause

        """

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        return "<{}>".format(self.__class__.__name__)


class VCRecordSearch(ABC):
    """A VC record search in progress."""

    @abstractmethod
    async def fetch(self, max_count: int = None) -> Sequence[VCRecord]:
        """
        Fetch the next list of VC records from the store.

        Args:
            max_count: Max number of records to return. If not provided,
              defaults to the backend's preferred page size

        Returns:
            A list of `VCRecord` instances

        """

    async def close(self):
        """Dispose of the search query."""

    def __aiter__(self):
        """Async iterator magic method."""
        return IterVCRecordSearch(self)

    def __repr__(self) -> str:
        """Human readable representation of this instance."""
        return "<{}>".format(self.__class__.__name__)


class IterVCRecordSearch:
    """A generic record search async iterator."""

    def __init__(self, search: VCRecordSearch, page_size: int = None):
        """Instantiate a new `IterVCRecordSearch` instance."""
        self._buffer = None
        self._page_size = page_size
        self._search = search

    async def __anext__(self):
        """Async iterator magic method."""
        if not self._buffer:
            self._buffer = await self._search.fetch(self._page_size) or []
        try:
            return self._buffer.pop(0)
        except IndexError:
            raise StopAsyncIteration
