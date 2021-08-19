from aries_cloudagent.core.error import ProfileError
from asynctest import TestCase as AsyncTestCase

from ..store import AskarStoreConfig

class TestStoreConfig(AsyncTestCase):
    async def test_init_success(self):
        config = {
            "key_derivation_method": "RAW",
            "key": "key",
            "storage_type": "postgres"
        }

        askar_store = AskarStoreConfig(
            config
        )

        assert askar_store.key_derivation_method == "RAW"
        assert askar_store.key == "key"
        assert askar_store.storage_type == "postgres"

    async def test_init_should_fail_when_key_missing(self):
        config = {
            "key_derivation_method": "RAW",
            "storage_type": "postgres"
        }

        with self.assertRaises(ProfileError):
            askar_store = AskarStoreConfig(
                config
            )