import json
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

    def test_unsupported_storage_type(self):
        with self.assertRaises(ProfileError) as ctx:
            AskarStoreConfig({"storage_type": "invalid"})
        assert "Unsupported storage type" in str(ctx.exception)

    def test_get_uri_sqlite_memory(self):
        config = {
            "storage_type": "sqlite",
            "name": "test",
        }
        askar_store = AskarStoreConfig(config)
        uri = askar_store.get_uri(in_memory=True)
        assert uri == "sqlite://:memory:"

    def test_get_uri_postgres(self):
        config = {
            "storage_type": "postgres",
            "name": "testname",
            "storage_config": json.dumps({"url": "localhost", "connection_timeout": 5}),
            "storage_creds": json.dumps({"account": "user", "password": "pass"}),
        }
        askar_store = AskarStoreConfig(config)
        uri = askar_store.get_uri()
        assert uri.startswith("postgres://user:pass@localhost/testname")

    def test_postgres_config_missing_fields(self):
        config = {
            "storage_type": "postgres",
            "storage_config": json.dumps({}),  # missing url
            "storage_creds": json.dumps({"account": "user", "password": "pass"}),
        }

        with self.assertRaises(ProfileError) as ctx:
            AskarStoreConfig(config)._validate_postgres_config()
        assert "Missing 'url'" in str(ctx.exception)

    @mock.patch(
        "aries_askar.Store.remove",
        side_effect=AskarError(AskarErrorCode.NOT_FOUND, message="Store not found"),
    )
    async def test_remove_store_not_found(self, _):
        config = {"storage_type": "sqlite", "name": "nonexistent"}
        store_config = AskarStoreConfig(config)
        with self.assertRaises(ProfileNotFoundError):
            await store_config.remove_store()

    @mock.patch(
        "aries_askar.Store.remove",
        side_effect=AskarError(AskarErrorCode.UNEXPECTED, message="Some error"),
    )
    async def test_remove_store_other_error(self, _):
        config = {"storage_type": "sqlite", "name": "badstore"}
        store_config = AskarStoreConfig(config)
        with self.assertRaises(ProfileError):
            await store_config.remove_store()

    def test_askar_open_store_name_property(self):
        config = AskarStoreConfig({"storage_type": "sqlite", "name": "teststore"})
        store = mock.AsyncMock()
        open_store = AskarOpenStore(config=config, created=True, store=store)
        assert open_store.name == "teststore"

    async def test_askar_open_store_close(self):
        config = AskarStoreConfig({"storage_type": "sqlite", "auto_remove": True})
        store = mock.AsyncMock()
        open_store = AskarOpenStore(config=config, created=True, store=store)

        await open_store.close()

        store.close.assert_awaited_with(remove=True)
        assert open_store.store is None
