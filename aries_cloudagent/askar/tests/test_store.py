from asynctest import TestCase as AsyncTestCase

from ...core.error import ProfileError

from ..store import AskarStoreConfig


class TestStoreConfig(AsyncTestCase):
    key_derivation_method = "Raw"
    key = "key"
    storage_type = "postgres"

    async def test_init_success(self):
        config = {
            "key_derivation_method": self.key_derivation_method,
            "key": self.key,
            "storage_type": self.storage_type,
        }

        askar_store = AskarStoreConfig(config)

        assert askar_store.key_derivation_method == self.key_derivation_method
        assert askar_store.key == self.key
        assert askar_store.storage_type == self.storage_type

    async def test_init_should_fail_when_key_missing(self):
        config = {
            "key_derivation_method": self.key_derivation_method,
            "storage_type": self.storage_type,
        }

        with self.assertRaises(ProfileError):
            askar_store = AskarStoreConfig(config)
