"""Indy implementation of BaseStorage interface."""

import json
from typing import Mapping, Sequence

from indy import non_secrets
from indy.error import IndyError, ErrorCode

from .base import BaseStorage, BaseStorageRecordSearch
from .error import (
    StorageError,
    StorageDuplicateError,
    StorageNotFoundError,
    StorageSearchError,
)
from .record import StorageRecord
from ..wallet.indy import IndyWallet


def _validate_record(record: StorageRecord):
    if not record:
        raise StorageError("No record provided")
    if not record.id:
        raise StorageError("Record has no ID")
    if not record.type:
        raise StorageError("Record has no type")
    if not record.value:
        raise StorageError("Record must have a non-empty value")


class IndyStorage(BaseStorage):
    """Indy Non-Secrets interface."""

    def __init__(self, wallet: IndyWallet):
        """
        Initialize a `BasicStorage` instance.

        Args:
            wallet: The indy wallet instance to use

        """
        self._wallet = wallet

    @property
    def wallet(self) -> IndyWallet:
        """Accessor for IndyWallet instance."""
        return self._wallet

    async def add_record(self, record: StorageRecord):
        """
        Add a new record to the store.

        Args:
            record: `StorageRecord` to be stored

        """
        _validate_record(record)
        tags_json = json.dumps(record.tags) if record.tags else None
        try:
            await non_secrets.add_wallet_record(
                self._wallet.handle, record.type, record.id, record.value, tags_json
            )
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemAlreadyExists:
                raise StorageDuplicateError("Duplicate record ID: {}".format(record.id))
            raise StorageError(str(x_indy))

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
                raise StorageNotFoundError("Record not found: {}".format(record_id))
            raise StorageError(str(x_indy))
        result = json.loads(result_json)
        return StorageRecord(
            type=record_type,
            id=result["id"],
            value=result["value"],
            tags=result["tags"] or {},
        )

    async def update_record_value(self, record: StorageRecord, value: str):
        """
        Update an existing stored record's value.

        Args:
            record: `StorageRecord` to update
            value: The new value

        Raises:
            StorageNotFoundError: If record not found
            StorageError: If a libindy error occurs

        """
        _validate_record(record)
        try:
            await non_secrets.update_wallet_record_value(
                self._wallet.handle, record.type, record.id, value
            )
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise StorageNotFoundError("Record not found: {}".format(record.id))
            raise StorageError(str(x_indy))

    async def update_record_tags(self, record: StorageRecord, tags: Mapping):
        """
        Update an existing stored record's tags.

        Args:
            record: `StorageRecord` to update
            tags: New tags

        Raises:
            StorageNotFoundError: If record not found
            StorageError: If a libindy error occurs

        """
        _validate_record(record)
        tags_json = json.dumps(tags) if tags else "{}"
        try:
            await non_secrets.update_wallet_record_tags(
                self._wallet.handle, record.type, record.id, tags_json
            )
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise StorageNotFoundError("Record not found: {}".format(record.id))
            raise StorageError(str(x_indy))

    async def delete_record_tags(
        self, record: StorageRecord, tags: (Sequence, Mapping)
    ):
        """
        Update an existing stored record's tags.

        Args:
            record: `StorageRecord` to delete
            tags: Tags

        """
        _validate_record(record)
        if tags:
            # check existence of record first (otherwise no exception thrown)
            await self.get_record(record.type, record.id)

            tag_names_json = json.dumps(list(tags))
            await non_secrets.delete_wallet_record_tags(
                self._wallet.handle, record.type, record.id, tag_names_json
            )

    async def delete_record(self, record: StorageRecord):
        """
        Delete a record.

        Args:
            record: `StorageRecord` to delete

        Raises:
            StorageNotFoundError: If record not found
            StorageError: If a libindy error occurs

        """
        _validate_record(record)
        try:
            await non_secrets.delete_wallet_record(
                self._wallet.handle, record.type, record.id
            )
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise StorageNotFoundError("Record not found: {}".format(record.id))
            raise StorageError(str(x_indy))

    def search_records(
        self,
        type_filter: str,
        tag_query: Mapping = None,
        page_size: int = None,
        options: Mapping = None,
    ) -> "IndyStorageRecordSearch":
        """
        Search stored records.

        Args:
            type_filter: Filter string
            tag_query: Tags to query
            page_size: Page size
            options: Dictionary of backend-specific options

        Returns:
            An instance of `IndyStorageRecordSearch`

        """
        return IndyStorageRecordSearch(self, type_filter, tag_query, page_size, options)


class IndyStorageRecordSearch(BaseStorageRecordSearch):
    """Represent an active stored records search."""

    def __init__(
        self,
        store: IndyStorage,
        type_filter: str,
        tag_query: Mapping,
        page_size: int = None,
        options: Mapping = None,
    ):
        """
        Initialize a `IndyStorageRecordSearch` instance.

        Args:
            store: `BaseStorage` to search
            type_filter: Filter string
            tag_query: Tags to search
            page_size: Size of page to return

        """
        super(IndyStorageRecordSearch, self).__init__(
            store, type_filter, tag_query, page_size, options
        )
        self._handle = None

    @property
    def opened(self) -> bool:
        """
        Accessor for open state.

        Returns:
            True if opened, else False

        """
        return self._handle is not None

    @property
    def handle(self):
        """
        Accessor for search handle.

        Returns:
            The handle

        """
        return self._handle

    async def fetch(self, max_count: int) -> Sequence[StorageRecord]:
        """
        Fetch the next list of results from the store.

        Args:
            max_count: Max number of records to return

        Returns:
            A list of `StorageRecord`

        Raises:
            StorageSearchError: If the search query has not been opened

        """
        if not self.opened:
            raise StorageSearchError("Search query has not been opened")
        result_json = await non_secrets.fetch_wallet_search_next_records(
            self.store.wallet.handle, self._handle, max_count
        )
        results = json.loads(result_json)
        ret = []
        if results["records"]:
            for row in results["records"]:
                ret.append(
                    StorageRecord(
                        type=self._type_filter,
                        id=row["id"],
                        value=row["value"],
                        tags=row["tags"],
                    )
                )
        return ret

    async def open(self):
        """Start the search query."""
        query_json = json.dumps(self.tag_query or {})
        options_json = json.dumps(
            {
                "retrieveRecords": True,
                "retrieveTotalCount": False,
                "retrieveType": False,
                "retrieveValue": True,
                "retrieveTags": self.option("retrieveTags", True),
            }
        )
        self._handle = await non_secrets.open_wallet_search(
            self.store.wallet.handle, self.type_filter, query_json, options_json
        )

    async def close(self):
        """Dispose of the search query."""
        if self._handle:
            await non_secrets.close_wallet_search(self._handle)
            self._handle = None
