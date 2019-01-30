"""
Indy implementation of BaseStorage interface
"""

import json
from typing import Mapping, Sequence

from indy import non_secrets
from indy.error import IndyError, ErrorCode

from .base import BaseStorage, BaseStorageRecordSearch
from .error import StorageException, StorageNotFoundException, StorageSearchException
from .record import StorageRecord
from ..wallet.indy import IndyWallet


def _validate_record(record: StorageRecord):
        if not record:
            raise StorageException("No record provided")
        if not record.id:
            raise StorageException("Record has no ID")
        if not record.type:
            raise StorageException("Record has no type")


class IndyStorage(BaseStorage):
    """
    Abstract Non-Secrets interface
    """

    def __init__(self, wallet: IndyWallet):
        self._wallet = wallet

    @property
    def wallet(self) -> IndyWallet:
        """
        Accessor for IndyWallet instance
        """
        return self._wallet

    async def add_record(self, record: StorageRecord):
        """
        Add a new record to the store
        """
        _validate_record(record)
        tags_json = json.dumps(record.tags) if record.tags else None
        await non_secrets.add_wallet_record(
            self._wallet.handle,
            record.type,
            record.id,
            record.value,
            tags_json)

    async def get_record(self, record_type: str, record_id: str) -> StorageRecord:
        """
        Fetch a record from the store by type and ID
        """
        if not record_type:
            raise StorageException("Record type not provided")
        if not record_id:
            raise StorageException("Record ID not provided")
        options_json = json.dumps({
            "retrieveType": True,
            "retrieveValue": True,
            "retrieveTags": True,
        })
        try:
            result_json = await non_secrets.get_wallet_record(
                self._wallet.handle,
                record_type,
                record_id,
                options_json)
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise StorageNotFoundException("Record not found: {}".format(record_id))
            raise StorageException(str(x_indy))
        result = json.loads(result_json)
        return StorageRecord(
            type=result["type"],
            id=result["id"],
            value=result["value"],
            tags=result["tags"] or {},
        )

    async def update_record_value(self, record: StorageRecord, value: str):
        """
        Update an existing stored record's value
        """
        _validate_record(record)
        try:
            await non_secrets.update_wallet_record_value(
                self._wallet.handle,
                record.type,
                record.id,
                value)
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise StorageNotFoundException("Record not found: {}".format(record.id))
            raise StorageException(str(x_indy))

    async def update_record_tags(self, record: StorageRecord, tags: Mapping):
        """
        Update an existing stored record's tags
        """
        _validate_record(record)
        tags_json = json.dumps(tags) if tags else "{}"
        try:
            await non_secrets.update_wallet_record_tags(
                self._wallet.handle,
                record.type,
                record.id,
                tags_json)
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise StorageNotFoundException("Record not found: {}".format(record.id))
            raise StorageException(str(x_indy))

    async def delete_record_tags(self, record: StorageRecord, tags: (Sequence, Mapping)):
        """
        Update an existing stored record's tags
        """
        _validate_record(record)
        if tags:
            # check existence of record first (otherwise no exception thrown)
            await self.get_record(record.type, record.id)

            tag_names_json = json.dumps(list(tags))
            await non_secrets.delete_wallet_record_tags(
                self._wallet.handle,
                record.type,
                record.id,
                tag_names_json)

    async def delete_record(self, record: StorageRecord):
        _validate_record(record)
        try:
            await non_secrets.delete_wallet_record(
                self._wallet.handle,
                record.type,
                record.id)
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise StorageNotFoundException("Record not found: {}".format(record.id))
            raise StorageException(str(x_indy))

    def search_records(self, type_filter: str, tag_query: Mapping = None, page_size: int = None) \
            -> 'BasicStorageRecordSearch':
        return IndyStorageRecordSearch(self, type_filter, tag_query, page_size)


class IndyStorageRecordSearch(BaseStorageRecordSearch):
    def __init__(self, store: IndyStorage,
                 type_filter: str, tag_query: Mapping,
                 page_size: int = None):
        super(IndyStorageRecordSearch, self).__init__(store, type_filter, tag_query, page_size)
        self._handle = None

    @property
    def opened(self) -> bool:
        """
        Accessor for open state
        """
        return self._handle is not None

    @property
    def handle(self):
        """
        Return handle to active storage search
        """
        return self._handle

    async def fetch(self, max_count: int) -> Sequence[StorageRecord]:
        """
        Fetch the next list of results from the store
        """
        if not self.opened:
            raise StorageSearchException("Search query has not been opened")
        result_json = await non_secrets.fetch_wallet_search_next_records(
            self.store.wallet.handle,
            self._handle,
            max_count)
        results = json.loads(result_json)
        ret = []
        if results["records"]:
            for row in results["records"]:
                ret.append(StorageRecord(
                    type=row["type"],
                    id=row["id"],
                    value=row["value"],
                    tags=row["tags"],
                ))
        return ret

    async def open(self):
        """
        Start the search query
        """
        query_json = json.dumps(self.tag_query or {})
        options_json = json.dumps({
            "retrieveRecords": True,
            "retrieveTotalCount": True,
            "retrieveType": True,
            "retrieveValue": True,
            "retrieveTags": True,
        })
        self._handle = await non_secrets.open_wallet_search(
            self.store.wallet.handle,
            self.type_filter,
            query_json,
            options_json)

    async def close(self):
        """
        Dispose of the search query
        """
        if self._handle:
            await non_secrets.close_wallet_search(self._handle)
            self._handle = None
