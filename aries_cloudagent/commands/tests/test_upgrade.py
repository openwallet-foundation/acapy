import asyncio

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ...core.in_memory import InMemoryProfile
from ...config.error import ArgsParseError
from ...connections.models.conn_record import ConnRecord
from ...storage.base import BaseStorage
from ...storage.record import StorageRecord

from .. import upgrade as test_module
from ..upgrade import UpgradeError


class TestUpgrade(AsyncTestCase):
    def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile

    def test_bad_calls(self):
        with self.assertRaises(ArgsParseError):
            test_module.execute([])

        with self.assertRaises(SystemExit):
            test_module.execute(["bad"])

    async def test_upgrade_storage_from_version_included(self):
        storage = self.session.inject(BaseStorage)
        record = StorageRecord(
            "acapy_version",
            "v0.7.2",
        )
        await storage.add_record(record)
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ) as mock_wallet_config, async_mock.patch.object(
            ConnRecord,
            "query",
            async_mock.CoroutineMock(return_value=[ConnRecord()]),
        ) as mock_conn_query, async_mock.patch.object(
            ConnRecord, "save", async_mock.CoroutineMock()
        ) as mock_conn_save:
            await test_module.upgrade(
                {
                    "upgrade.config": {
                        "v0.7.2": {
                            "resave_records": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ],
                            "update_existing_records": True,
                        }
                    },
                    "upgrade.from_version": "v0.7.2",
                }
            )

    async def test_upgrade_storage_missing_from_version(self):
        storage = self.session.inject(BaseStorage)
        record = StorageRecord(
            "acapy_version",
            "v0.7.2",
        )
        await storage.add_record(record)
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ) as mock_wallet_config, async_mock.patch.object(
            ConnRecord,
            "query",
            async_mock.CoroutineMock(return_value=[ConnRecord()]),
        ) as mock_conn_query, async_mock.patch.object(
            ConnRecord, "save", async_mock.CoroutineMock()
        ) as mock_conn_save:
            await test_module.upgrade(
                {
                    "upgrade.config": {
                        "v0.7.2": {
                            "resave_records": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ],
                            "update_existing_records": True,
                        }
                    },
                }
            )

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
        ) as mock_wallet_config, async_mock.patch.object(
            ConnRecord,
            "query",
            async_mock.CoroutineMock(return_value=[ConnRecord()]),
        ) as mock_conn_query, async_mock.patch.object(
            ConnRecord, "save", async_mock.CoroutineMock()
        ) as mock_conn_save:
            await test_module.upgrade(
                {
                    "upgrade.config": {
                        "v0.7.2": {
                            "resave_records": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ],
                            "update_existing_records": True,
                        }
                    },
                    "upgrade.from_version": "v0.7.2",
                }
            )

    async def test_upgrade_x_missing_from_version(self):
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    self.profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ) as mock_wallet_config, async_mock.patch.object(
            ConnRecord,
            "query",
            async_mock.CoroutineMock(return_value=[ConnRecord()]),
        ) as mock_conn_query, async_mock.patch.object(
            ConnRecord, "save", async_mock.CoroutineMock()
        ) as mock_conn_save:
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.config": {
                            "v0.7.2": {
                                "resave_records": [
                                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                                ],
                                "update_existing_records": True,
                            }
                        },
                    }
                )
            assert "ACA-Py version not found in storage and" in str(ctx.exception)

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
        ) as mock_wallet_config:
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.config": {
                            "v0.7.2": {
                                "resave_records": [
                                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                                ],
                                "update_existing_records": True,
                            },
                            "v0.6.0": {"update_existing_records": True},
                        },
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
        ) as mock_wallet_config:
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.config": {
                            "v0.7.2": {
                                "resave_records": [
                                    "aries_cloudagent.connections.models.conn_record.Invalid"
                                ],
                            }
                        },
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
        ) as mock_wallet_config, async_mock.patch.object(
            ConnRecord,
            "query",
            async_mock.CoroutineMock(return_value=[ConnRecord()]),
        ) as mock_conn_query, async_mock.patch.object(
            ConnRecord, "save", async_mock.CoroutineMock()
        ) as mock_conn_save, async_mock.patch.object(
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
        ) as mock_wallet_config:
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.config": {
                            "v0.7.2": {
                                "resave_records": [
                                    "aries_cloudagent.connections.models.connection_target.ConnectionTarget"
                                ],
                            }
                        },
                        "upgrade.from_version": "v0.7.2",
                    }
                )
            assert "Only BaseRecord and BaseExchangeRecord can be resaved" in str(
                ctx.exception
            )

    def test_main(self):
        with async_mock.patch.object(
            test_module, "__name__", "__main__"
        ) as mock_name, async_mock.patch.object(
            test_module, "execute", async_mock.MagicMock()
        ) as mock_execute:
            test_module.main()
            mock_execute.assert_called_once
