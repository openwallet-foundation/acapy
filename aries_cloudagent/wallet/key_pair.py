"""Key pair storage manager."""

import json
from typing import List, Mapping, Optional, Sequence
import uuid

from ..storage.base import BaseStorage
from ..storage.record import StorageRecord
from .util import bytes_to_b58
from .key_type import KeyType

KEY_PAIR_STORAGE_TYPE = "key_pair"


class KeyPairStorageManager:
    """Key pair storage manager."""

    def __init__(self, store: BaseStorage) -> None:
        """Create new KeyPairStorageManager instance.

        Args:
            store (BaseStorage): The storage to use for the key pairs.
        """
        self._store = store

    async def store_key_pair(
        self,
        public_key: bytes,
        secret_key: bytes,
        key_type: KeyType,
        metadata: dict = {},
        tags: dict = {},
    ):
        """Store signing key pair in storage.

        Args:
            public_key (bytes): The public key
            secret_key (bytes): The secret key
            key_type (KeyType): The key type
            metadata (dict, optional): The metadata
            tags (dict, optional): The tags.
        """
        verkey = bytes_to_b58(public_key)
        data = {
            "verkey": verkey,
            "secret_key": bytes_to_b58(secret_key),
            "key_type": key_type.key_type,
            "metadata": metadata,
        }
        record = StorageRecord(
            KEY_PAIR_STORAGE_TYPE,
            json.dumps(data),
            {**tags, "verkey": verkey, "key_type": key_type.key_type},
            uuid.uuid4().hex,
        )

        await self._store.add_record(record)

    async def get_key_pair(self, verkey: str) -> dict:
        """Retrieve signing key pair from storage by verkey.

        Args:
            storage (BaseStorage): The storage to use for querying
            verkey (str): The verkey to query for

        Raises:
            StorageDuplicateError: If more than one key pair is found for this verkey
            StorageNotFoundError: If no key pair is found for this verkey

        Returns
            dict: The key pair data

        """

        record = await self._store.find_record(
            KEY_PAIR_STORAGE_TYPE, {"verkey": verkey}
        )
        data = json.loads(record.value)

        return data

    async def find_key_pairs(self, tag_query: Optional[Mapping] = None) -> List[dict]:
        """Find key pairs by tag query."""
        records: Sequence[StorageRecord] = await self._store.find_all_records(
            KEY_PAIR_STORAGE_TYPE, tag_query
        )

        return [json.loads(record.value) for record in records]

    async def delete_key_pair(self, verkey: str):
        """
        Remove a previously-stored key pair record.

        Raises:
            StorageNotFoundError: If the record is not found

        """
        record = await self._store.find_record(
            KEY_PAIR_STORAGE_TYPE, {"verkey": verkey}
        )
        await self._store.delete_record(record)

    async def update_key_pair_metadata(self, verkey: str, metadata: dict):
        """
        Update the metadata of a key pair record by verkey.

        Raises:
            StorageNotFoundError: If the record is not found.

        """
        record = await self._store.find_record(
            KEY_PAIR_STORAGE_TYPE, {"verkey": verkey}
        )
        data = json.loads(record.value)
        data["metadata"] = metadata

        await self._store.update_record(record, json.dumps(data), record.tags)
