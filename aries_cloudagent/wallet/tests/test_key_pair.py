from asynctest import TestCase as AsyncTestCase

import json

from ...storage.error import StorageNotFoundError
from ..util import bytes_to_b58
from ..key_type import ED25519
from ...core.in_memory import InMemoryProfile
from ...storage.in_memory import InMemoryStorage
from ..key_pair import KeyPairStorageManager, KEY_PAIR_STORAGE_TYPE


class TestKeyPairStorageManager(AsyncTestCase):
    test_public_key = b"somepublickeybytes"
    test_secret = b"verysecretkey"

    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.store = InMemoryStorage(self.profile)
        self.key_pair_mgr = KeyPairStorageManager(self.store)

    async def test_create_key_pair(self):
        await self.key_pair_mgr.store_key_pair(
            public_key=self.test_public_key,
            secret_key=self.test_secret,
            key_type=ED25519,
        )

        verkey = bytes_to_b58(self.test_public_key)

        record = await self.store.find_record(KEY_PAIR_STORAGE_TYPE, {"verkey": verkey})

        assert record

        value = json.loads(record.value)

        assert record.tags == {"verkey": verkey, "key_type": ED25519.key_type}
        assert value["verkey"] == verkey
        assert value["secret_key"] == bytes_to_b58(self.test_secret)
        assert value["metadata"] == {}
        assert value["key_type"] == ED25519.key_type

    async def test_get_key_pair(self):
        await self.key_pair_mgr.store_key_pair(
            public_key=self.test_public_key,
            secret_key=self.test_secret,
            key_type=ED25519,
        )

        verkey = bytes_to_b58(self.test_public_key)

        key_pair = await self.key_pair_mgr.get_key_pair(verkey)

        assert key_pair["verkey"] == verkey
        assert key_pair["secret_key"] == bytes_to_b58(self.test_secret)
        assert key_pair["metadata"] == {}
        assert key_pair["key_type"] == ED25519.key_type

    async def test_get_key_pair_x_not_found(self):
        with self.assertRaises(StorageNotFoundError):
            await self.key_pair_mgr.get_key_pair("not_existing_verkey")

    async def test_delete_key_pair(self):
        await self.key_pair_mgr.store_key_pair(
            public_key=self.test_public_key,
            secret_key=self.test_secret,
            key_type=ED25519,
        )

        verkey = bytes_to_b58(self.test_public_key)

        record = await self.store.find_record(KEY_PAIR_STORAGE_TYPE, {"verkey": verkey})
        assert record

        await self.key_pair_mgr.delete_key_pair(verkey)

        # should be deleted now
        with self.assertRaises(StorageNotFoundError):
            await self.key_pair_mgr.delete_key_pair(verkey)

    async def test_delete_key_pair_x_not_found(self):
        with self.assertRaises(StorageNotFoundError):
            await self.key_pair_mgr.delete_key_pair("non_existing_verkey")

    async def test_update_key_pair_metadata(self):
        await self.key_pair_mgr.store_key_pair(
            public_key=self.test_public_key,
            secret_key=self.test_secret,
            key_type=ED25519,
            metadata={"some": "data"},
        )

        verkey = bytes_to_b58(self.test_public_key)

        record = await self.store.find_record(KEY_PAIR_STORAGE_TYPE, {"verkey": verkey})
        assert record
        value = json.loads(record.value)

        assert value["metadata"] == {"some": "data"}

        await self.key_pair_mgr.update_key_pair_metadata(verkey, {"some_other": "data"})

        record = await self.store.find_record(KEY_PAIR_STORAGE_TYPE, {"verkey": verkey})
        assert record
        value = json.loads(record.value)

        assert value["metadata"] == {"some_other": "data"}

    async def test_update_key_pair_metadata_x_not_found(self):
        with self.assertRaises(StorageNotFoundError):
            await self.key_pair_mgr.update_key_pair_metadata("non_existing_verkey", {})
