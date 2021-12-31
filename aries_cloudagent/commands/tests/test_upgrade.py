import asyncio

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ...core.in_memory import InMemoryProfile
from ...config.error import ArgsParseError
from ...connections.models.conn_record import ConnRecord
from ...storage.base import BaseStorage
from ...storage.record import StorageRecord
from ...version import __version__

from .. import upgrade as test_module
from ..upgrade import UpgradeError


class TestUpgrade(AsyncTestCase):
    async def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile

        self.session_storage = InMemoryProfile.test_session()
        self.profile_storage = self.session_storage.profile
        self.storage = self.session_storage.inject(BaseStorage)
        record = StorageRecord(
            "acapy_version",
            "v0.7.2",
        )
        await self.storage.add_record(record)

    def test_bad_calls(self):
        with self.assertRaises(SystemExit):
            test_module.execute(["bad"])

    async def test_upgrade_storage_from_version_included(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile_storage,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), async_mock.patch.object(
            ConnRecord,
            "query",
            async_mock.CoroutineMock(return_value=[ConnRecord()]),
        ), async_mock.patch.object(
            ConnRecord, "save", async_mock.CoroutineMock()
        ):
            await test_module.upgrade(
                {
                    "upgrade.config_path": "./aries_cloudagent/commands/default_version_upgrade_config.yml",
                    "upgrade.from_version": "v0.7.2",
                }
            )

    async def test_upgrade_storage_missing_from_version(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile_storage,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), async_mock.patch.object(
            ConnRecord,
            "query",
            async_mock.CoroutineMock(return_value=[ConnRecord()]),
        ), async_mock.patch.object(
            ConnRecord, "save", async_mock.CoroutineMock()
        ):
            await test_module.upgrade({})

    async def test_upgrade_from_version(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), async_mock.patch.object(
            ConnRecord,
            "query",
            async_mock.CoroutineMock(return_value=[ConnRecord()]),
        ), async_mock.patch.object(
            ConnRecord, "save", async_mock.CoroutineMock()
        ):
            await test_module.upgrade(
                {
                    "upgrade.from_version": "v0.7.2",
                }
            )

    async def test_upgrade_callable(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), async_mock.patch.object(
            test_module.yaml,
            "safe_load",
            async_mock.MagicMock(
                return_value={
                    "v0.7.2": {
                        "resave_records": {
                            "base_record_path": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ]
                        },
                        "update_existing_records": True,
                    },
                }
            ),
        ):
            await test_module.upgrade(
                {
                    "upgrade.from_version": "v0.7.2",
                }
            )

    async def test_upgrade_x_same_version(self):
        version_storage_record = await self.storage.find_record(
            type_filter="acapy_version", tag_query={}
        )
        await self.storage.update_record(version_storage_record, f"v{__version__}", {})
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile_storage,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ):
            with self.assertRaises(UpgradeError):
                await test_module.upgrade(
                    {
                        "upgrade.config_path": "./aries_cloudagent/commands/default_version_upgrade_config.yml",
                    }
                )

    async def test_upgrade_missing_from_version(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), async_mock.patch.object(
            ConnRecord,
            "query",
            async_mock.CoroutineMock(return_value=[ConnRecord()]),
        ), async_mock.patch.object(
            ConnRecord, "save", async_mock.CoroutineMock()
        ):
            await test_module.upgrade(
                {
                    "upgrade.config_path": "./aries_cloudagent/commands/default_version_upgrade_config.yml",
                }
            )

    async def test_upgrade_x_callable_not_set(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), async_mock.patch.object(
            test_module.yaml,
            "safe_load",
            async_mock.MagicMock(
                return_value={
                    "v0.7.2": {
                        "resave_records": {
                            "base_record_path": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ]
                        },
                        "update_existing_records": True,
                    },
                    "v0.6.0": {"update_existing_records": True},
                }
            ),
        ):
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.from_version": "v0.6.0",
                    }
                )
            assert "No update_existing_records function specified" in str(ctx.exception)

    async def test_upgrade_x_class_not_found(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), async_mock.patch.object(
            test_module.yaml,
            "safe_load",
            async_mock.MagicMock(
                return_value={
                    "v0.7.2": {
                        "resave_records": {
                            "base_record_path": [
                                "aries_cloudagent.connections.models.conn_record.Invalid"
                            ],
                        }
                    },
                }
            ),
        ):
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.from_version": "v0.7.2",
                    }
                )
            assert "Unknown Record type" in str(ctx.exception)

    async def test_execute(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), async_mock.patch.object(
            ConnRecord,
            "query",
            async_mock.CoroutineMock(return_value=[ConnRecord()]),
        ), async_mock.patch.object(
            ConnRecord, "save", async_mock.CoroutineMock()
        ), async_mock.patch.object(
            asyncio, "get_event_loop", async_mock.MagicMock()
        ) as mock_get_event_loop:
            mock_get_event_loop.return_value = async_mock.MagicMock(
                run_until_complete=async_mock.MagicMock(),
            )
            test_module.execute(
                [
                    "--upgrade-config",
                    "./aries_cloudagent/config/tests/test-acapy-upgrade-config.yaml",
                    "--from-version",
                    "v0.7.2",
                ]
            )

    async def test_upgrade_x_invalid_record_type(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), async_mock.patch.object(
            test_module.yaml,
            "safe_load",
            async_mock.MagicMock(
                return_value={
                    "v0.7.2": {
                        "resave_records": {
                            "base_exch_record_path": [
                                "aries_cloudagent.connections.models.connection_target.ConnectionTarget"
                            ],
                        }
                    }
                }
            ),
        ):
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.from_version": "v0.7.2",
                    }
                )
            assert "Only BaseRecord can be resaved" in str(ctx.exception)

    async def test_upgrade_x_invalid_config(self):
        with async_mock.patch.object(
            test_module.yaml,
            "safe_load",
            async_mock.MagicMock(return_value={}),
        ):
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade({})
            assert "No version configs found in" in str(ctx.exception)

    async def test_upgrade_x_from_version_not_in_config(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ):
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.from_version": "v1.2.3",
                    }
                )
            assert "No upgrade configuration found for" in str(ctx.exception)

    def test_main(self):
        with async_mock.patch.object(
            test_module, "__name__", "__main__"
        ) as mock_name, async_mock.patch.object(
            test_module, "execute", async_mock.MagicMock()
        ) as mock_execute:
            test_module.main()
            mock_execute.assert_called_once
