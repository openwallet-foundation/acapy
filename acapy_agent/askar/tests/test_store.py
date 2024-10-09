from unittest import IsolatedAsyncioTestCase

from aries_askar import AskarError, AskarErrorCode, Store

from acapy_agent.tests import mock

from ...core.error import ProfileDuplicateError, ProfileError, ProfileNotFoundError
from ..store import AskarOpenStore, AskarStoreConfig


class TestStoreConfig(IsolatedAsyncioTestCase):
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


class TestStoreOpen(IsolatedAsyncioTestCase):
    key_derivation_method = "Raw"
    key = "key"
    storage_type = "default"

    @mock.patch.object(Store, "open", autospec=True)
    async def test_open_store(self, mock_store_open):
        config = {
            "key_derivation_method": self.key_derivation_method,
            "key": self.key,
            "storage_type": self.storage_type,
        }

        store = await AskarStoreConfig(config).open_store()
        assert isinstance(store, AskarOpenStore)
        assert mock_store_open.called

    @mock.patch.object(Store, "open")
    async def test_open_store_fails(self, mock_store_open):
        config = {
            "key_derivation_method": self.key_derivation_method,
            "key": self.key,
            "storage_type": self.storage_type,
        }

        mock_store_open.side_effect = [
            AskarError(AskarErrorCode.NOT_FOUND, message="testing"),
            AskarError(AskarErrorCode.DUPLICATE, message="testing"),
            AskarError(AskarErrorCode.ENCRYPTION, message="testing"),
        ]

        with self.assertRaises(ProfileNotFoundError):
            await AskarStoreConfig(config).open_store()
        with self.assertRaises(ProfileDuplicateError):
            await AskarStoreConfig(config).open_store()
        with self.assertRaises(ProfileError):
            await AskarStoreConfig(config).open_store()

    @mock.patch.object(Store, "open")
    @mock.patch.object(Store, "rekey")
    async def test_open_store_fail_retry_with_rekey(self, mock_store_open, mock_rekey):
        config = {
            "key_derivation_method": self.key_derivation_method,
            "key": self.key,
            "storage_type": self.storage_type,
            "rekey": "rekey",
        }

        mock_store_open.side_effect = [
            AskarError(AskarErrorCode.ENCRYPTION, message="testing"),
            mock.AsyncMock(auto_spec=True),
        ]

        store = await AskarStoreConfig(config).open_store()

        assert isinstance(store, AskarOpenStore)
        assert mock_rekey.called

    @mock.patch.object(Store, "open")
    @mock.patch.object(Store, "rekey")
    async def test_open_store_fail_retry_with_rekey_fails(
        self, mock_store_open, mock_rekey
    ):
        config = {
            "key_derivation_method": self.key_derivation_method,
            "key": self.key,
            "storage_type": self.storage_type,
            "rekey": "rekey",
        }

        mock_store_open.side_effect = [
            AskarError(AskarErrorCode.ENCRYPTION, message="testing"),
            mock.AsyncMock(auto_spec=True),
        ]

        store = await AskarStoreConfig(config).open_store()

        assert isinstance(store, AskarOpenStore)
        assert mock_rekey.called
