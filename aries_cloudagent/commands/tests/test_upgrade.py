import pytest

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
                    "upgrade.resave_records": [
                        "aries_cloudagent.connections.models.conn_record.ConnRecord"
                    ],
                    "upgrade.update_existing_records": True,
                }
            )

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
                        "upgrade.resave_records": [
                            "aries_cloudagent.connections.models.conn_record.Invalid"
                        ],
                    }
                )
            assert "Unknown Record type" in str(ctx.exception)

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
                        "upgrade.resave_records": [
                            "aries_cloudagent.connections.models.connection_target.ConnectionTarget"
                        ],
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
