"""Indy implementation of BaseStorage interface."""

import asyncio
import json
import logging
from typing import Mapping, Sequence

from indy import non_secrets
from indy.error import IndyError, ErrorCode

from .base import (
    DEFAULT_PAGE_SIZE,
    BaseStorage,
    BaseStorageSearch,
    BaseStorageSearchSession,
    validate_record,
)
from .error import (
    StorageError,
    StorageDuplicateError,
    StorageNotFoundError,
    StorageSearchError,
)
from .record import StorageRecord
from ..indy.sdk.wallet_setup import IndyOpenWallet

LOGGER = logging.getLogger(__name__)


class IndySdkStorage(BaseStorage, BaseStorageSearch):
    """Indy Non-Secrets interface."""

    def __init__(self, wallet: IndyOpenWallet):
        """
        Initialize an `IndySdkStorage` instance.

        Args:
            wallet: The indy wallet instance to use

        """
        self._wallet = wallet

    @property
    def wallet(self) -> IndyOpenWallet:
        """Accessor for IndyOpenWallet instance."""
        return self._wallet

    async def add_record(self, record: StorageRecord):
        """
        Add a new record to the store.

        Args:
            record: `StorageRecord` to be stored

        """
        validate_record(record)
        tags_json = json.dumps(record.tags) if record.tags else None
        try:
            await non_secrets.add_wallet_record(
                self._wallet.handle, record.type, record.id, record.value, tags_json
            )
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemAlreadyExists:
                raise StorageDuplicateError(
                    "Duplicate record ID: {}".format(record.id)
                ) from x_indy
            raise StorageError(str(x_indy)) from x_indy

    async def get_record(
        self, record_type: str, record_id: str, options: Mapping = None
    ) -> StorageRecord:
        """
        Fetch a record from the store by type and ID.

        Args:
            record_type: The record type
            record_id: The record id
            options: A dictionary of backend-specific options

        Returns:
            A `StorageRecord` instance

        Raises:
            StorageError: If the record is not provided
            StorageError: If the record ID not provided
            StorageNotFoundError: If the record is not found
            StorageError: If record not found

        """
        if not record_type:
            raise StorageError("Record type not provided")
        if not record_id:
            raise StorageError("Record ID not provided")
        if not options:
            options = {}
        options_json = json.dumps(
            {
                "retrieveType": False,
                "retrieveValue": True,
                "retrieveTags": options.get("retrieveTags", True),
            }
        )
        try:
            result_json = await non_secrets.get_wallet_record(
                self._wallet.handle, record_type, record_id, options_json
            )
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise StorageNotFoundError(
                    f"{record_type} record not found: {record_id}"
                ) from x_indy
            raise StorageError(str(x_indy)) from x_indy
        result = json.loads(result_json)
        return StorageRecord(
            type=record_type,
            id=result["id"],
            value=result["value"],
            tags=result["tags"] or {},
        )

    async def update_record(self, record: StorageRecord, value: str, tags: Mapping):
        """
        Update an existing stored record's value and tags.

        Args:
            record: `StorageRecord` to update
            value: The new value
            tags: The new tags

        Raises:
            StorageNotFoundError: If record not found
            StorageError: If a libindy error occurs

        """
        validate_record(record)
        tags_json = json.dumps(tags) if tags else "{}"
        try:
            await non_secrets.update_wallet_record_value(
                self._wallet.handle, record.type, record.id, value
            )
            await non_secrets.update_wallet_record_tags(
                self._wallet.handle, record.type, record.id, tags_json
            )
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise StorageNotFoundError(f"Record not found: {record.id}")
            raise StorageError(str(x_indy))

    async def delete_record(self, record: StorageRecord):
        """
        Delete a record.

        Args:
            record: `StorageRecord` to delete

        Raises:
            StorageNotFoundError: If record not found
            StorageError: If a libindy error occurs

        """
        validate_record(record, delete=True)
        try:
            await non_secrets.delete_wallet_record(
                self._wallet.handle, record.type, record.id
            )
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise StorageNotFoundError(f"Record not found: {record.id}")
            raise StorageError(str(x_indy))

    async def find_all_records(
        self,
        type_filter: str,
        tag_query: Mapping = None,
        options: Mapping = None,
    ):
        """Retrieve all records matching a particular type filter and tag query."""
        results = []
        search = self.search_records(type_filter, tag_query, options=options)
        while True:
            buf = await search.fetch()
            if buf:
                results.extend(buf)
            else:
                break
        return results

    async def delete_all_records(
        self,
        type_filter: str,
        tag_query: Mapping = None,
    ):
        """Remove all records matching a particular type filter and tag query."""
        async for row in self.search_records(
            type_filter, tag_query, options={"retrieveTags": False}
        ):
            await self.delete_record(row)

    def search_records(
        self,
        type_filter: str,
        tag_query: Mapping = None,
        page_size: int = None,
        options: Mapping = None,
    ) -> "IndySdkStorageSearch":
        """
        Search stored records.

        Args:
            type_filter: Filter string
            tag_query: Tags to query
            page_size: Page size
            options: Dictionary of backend-specific options

        Returns:
            An instance of `IndySdkStorageSearch`

        """
        return IndySdkStorageSearch(self, type_filter, tag_query, page_size, options)


class IndySdkStorageSearch(BaseStorageSearchSession):
    """Represent an active stored records search."""

    def __init__(
        self,
        store: IndySdkStorage,
        type_filter: str,
        tag_query: Mapping,
        page_size: int = None,
        options: Mapping = None,
    ):
        """
        Initialize a `IndySdkStorageSearch` instance.

        Args:
            store: `BaseStorage` to search
            type_filter: Filter string
            tag_query: Tags to search
            page_size: Size of page to return

        """
        self._handle = None
        self._done = False
        self.store = store
        self.options = options or {}
        self.page_size = page_size or DEFAULT_PAGE_SIZE
        self.tag_query = tag_query
        self.type_filter = type_filter

    async def fetch(self, max_count: int = None) -> Sequence[StorageRecord]:
        """
        Fetch the next list of results from the store.

        Args:
            max_count: Max number of records to return. If not provided,
              defaults to the backend's preferred page size

        Returns:
            A list of `StorageRecord` instances

        Raises:
            StorageSearchError: If the search query has not been opened

        """
        if self._done:
            raise StorageSearchError("Search query is complete")
        await self._open()

        try:
            result_json = await non_secrets.fetch_wallet_search_next_records(
                self.store.wallet.handle, self._handle, max_count or self.page_size
            )
        except IndyError as x_indy:
            raise StorageSearchError(str(x_indy)) from x_indy

        results = json.loads(result_json)
        ret = []
        if results["records"]:
            for row in results["records"]:
                ret.append(
                    StorageRecord(
                        type=self.type_filter,
                        id=row["id"],
                        value=row["value"],
                        tags=row["tags"],
                    )
                )

        if not ret:
            await self.close()

        return ret

    async def _open(self):
        """Start the search query."""
        if self._handle:
            return

        query_json = json.dumps(self.tag_query or {})
        options_json = json.dumps(
            {
                "retrieveRecords": True,
                "retrieveTotalCount": False,
                "retrieveType": False,
                "retrieveValue": True,
                "retrieveTags": self.options.get("retrieveTags", True),
            }
        )
        try:
            self._handle = await non_secrets.open_wallet_search(
                self.store.wallet.handle, self.type_filter, query_json, options_json
            )
        except IndyError as x_indy:
            raise StorageSearchError(str(x_indy)) from x_indy

    async def close(self):
        """Dispose of the search query."""
        try:
            if self._handle:
                await non_secrets.close_wallet_search(self._handle)
                self._handle = None
                self.store = None
            self._done = True
        except IndyError as x_indy:
            raise StorageSearchError(str(x_indy)) from x_indy

    def __del__(self):
        """Ensure the search is closed."""
        if self._handle:

            async def cleanup(handle):
                LOGGER.warning("Indy wallet search was not closed manually")
                try:
                    await non_secrets.close_wallet_search(handle)
                except Exception:
                    LOGGER.exception("Exception when auto-closing Indy wallet search")

            loop = asyncio.get_event_loop()
            task = loop.create_task(cleanup(self._handle))
            if not loop.is_running():
                loop.run_until_complete(task)
