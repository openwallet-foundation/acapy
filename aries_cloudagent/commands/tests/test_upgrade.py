import asyncio

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ...config.error import ArgsParseError
from ...connections.models.conn_record import ConnRecord

from .. import upgrade as test_module
from ..upgrade import UpgradeError


class TestUpgrade(AsyncTestCase):
    def test_bad_calls(self):
        with self.assertRaises(ArgsParseError):
            test_module.execute([])

        with self.assertRaises(SystemExit):
            test_module.execute(["bad"])

    async def test_upgrade(self):
        profile = async_mock.MagicMock(close=async_mock.CoroutineMock())
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    profile,
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
                        "0.7.2": {
                            "resave_records": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ],
                            "update_existing_records": True,
                        }
                    },
                    "upgrade.from_version": "0.7.2",
                }
            )

    async def test_upgrade_callable_not_set(self):
        profile = async_mock.MagicMock(close=async_mock.CoroutineMock())
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ) as mock_wallet_config:
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.config": {
                            "0.7.2": {
                                "resave_records": [
                                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                                ],
                                "update_existing_records": True,
                            },
                            "0.6.0": {"update_existing_records": True},
                        },
                        "upgrade.from_version": "0.6.0",
                    }
                )
            assert "No update_existing_records function specified" in str(ctx.exception)

    async def test_upgrade_x_class_not_found(self):
        profile = async_mock.MagicMock(close=async_mock.CoroutineMock())
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ) as mock_wallet_config:
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.config": {
                            "0.7.2": {
                                "resave_records": [
                                    "aries_cloudagent.connections.models.conn_record.Invalid"
                                ],
                            }
                        },
                        "upgrade.from_version": "0.7.2",
                    }
                )
            assert "Unknown Record type" in str(ctx.exception)

    async def test_execute(self):
        profile = async_mock.MagicMock(close=async_mock.CoroutineMock())
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    profile,
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
                    "0.7.2",
                ]
            )

    async def test_upgrade_x_invalid_record_type(self):
        profile = async_mock.MagicMock(close=async_mock.CoroutineMock())
        with async_mock.patch.object(
            test_module,
            "wallet_config",
            async_mock.CoroutineMock(
                return_value=(
                    profile,
                    async_mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ) as mock_wallet_config:
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    {
                        "upgrade.config": {
                            "0.7.2": {
                                "resave_records": [
                                    "aries_cloudagent.connections.models.connection_target.ConnectionTarget"
                                ],
                            }
                        },
                        "upgrade.from_version": "0.7.2",
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
