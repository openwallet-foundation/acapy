import asyncio

from aries_cloudagent.tests import mock
from unittest import IsolatedAsyncioTestCase

from ...core.in_memory import InMemoryProfile
from ...connections.models.conn_record import ConnRecord
from ...storage.base import BaseStorage, BaseStorageSearch
from ...storage.in_memory import InMemoryStorage
from ...storage.record import StorageRecord
from ...version import __version__
from ...wallet.models.wallet_record import WalletRecord

from .. import upgrade as test_module
from ..upgrade import UpgradeError


class TestUpgrade(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile
        self.profile.context.injector.bind_instance(
            BaseStorageSearch, InMemoryStorage(self.profile)
        )
        self.storage = self.session.inject(BaseStorage)
        record = StorageRecord(
            "acapy_version",
            "v0.7.2",
        )
        await self.storage.add_record(record)
        recs = [
            WalletRecord(
                key_management_mode=[
                    WalletRecord.MODE_UNMANAGED,
                    WalletRecord.MODE_MANAGED,
                ][i],
                settings={
                    "wallet.name": f"my-wallet-{i}",
                    "wallet.type": "indy",
                    "wallet.key": f"dummy-wallet-key-{i}",
                },
                wallet_name=f"my-wallet-{i}",
            )
            for i in range(2)
        ]
        async with self.profile.session() as session:
            for rec in recs:
                await rec.save(session)

    def test_bad_calls(self):
        with self.assertRaises(SystemExit):
            test_module.execute(["bad"])

    async def test_upgrade_storage_from_version_included(self):
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), mock.patch.object(
            ConnRecord,
            "query",
            mock.CoroutineMock(return_value=[ConnRecord()]),
        ), mock.patch.object(
            ConnRecord, "save", mock.CoroutineMock()
        ):
            await test_module.upgrade(
                settings={
                    "upgrade.config_path": "./aries_cloudagent/commands/default_version_upgrade_config.yml",
                    "upgrade.from_version": "v0.7.2",
                }
            )

    async def test_upgrade_storage_missing_from_version(self):
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), mock.patch.object(
            ConnRecord,
            "query",
            mock.CoroutineMock(return_value=[ConnRecord()]),
        ), mock.patch.object(
            ConnRecord, "save", mock.CoroutineMock()
        ):
            await test_module.upgrade(settings={})

    async def test_upgrade_from_version(self):
        self.profile.settings.extend(
            {
                "upgrade.from_version": "v0.7.2",
            }
        )
        with mock.patch.object(
            ConnRecord,
            "query",
            mock.CoroutineMock(return_value=[ConnRecord()]),
        ), mock.patch.object(ConnRecord, "save", mock.CoroutineMock()):
            await test_module.upgrade(
                profile=self.profile,
            )

    async def test_upgrade_all_subwallets(self):
        self.profile.settings.extend(
            {
                "upgrade.from_version": "v0.7.2",
                "upgrade.upgrade_all_subwallets": True,
                "upgrade.force_upgrade": True,
                "upgrade.page_size": 1,
            }
        )
        with mock.patch.object(
            ConnRecord,
            "query",
            mock.CoroutineMock(return_value=[ConnRecord()]),
        ), mock.patch.object(ConnRecord, "save", mock.CoroutineMock()):
            await test_module.upgrade(
                profile=self.profile,
            )

    async def test_upgrade_specified_subwallets(self):
        wallet_ids = []
        async with self.profile.session() as session:
            wallet_recs = await WalletRecord.query(session, tag_filter={})
        for wallet_rec in wallet_recs:
            wallet_ids.append(wallet_rec.wallet_id)
        self.profile.settings.extend(
            {
                "upgrade.named_tags": "fix_issue_rev_reg",
                "upgrade.upgrade_subwallets": [wallet_ids[0]],
                "upgrade.force_upgrade": True,
            }
        )
        with mock.patch.object(
            ConnRecord,
            "query",
            mock.CoroutineMock(return_value=[ConnRecord()]),
        ), mock.patch.object(ConnRecord, "save", mock.CoroutineMock()):
            await test_module.upgrade(
                profile=self.profile,
            )

        self.profile.settings.extend(
            {
                "upgrade.named_tags": "fix_issue_rev_reg",
                "upgrade.upgrade_subwallets": wallet_ids,
                "upgrade.force_upgrade": True,
                "upgrade.page_size": 1,
            }
        )
        with mock.patch.object(
            ConnRecord,
            "query",
            mock.CoroutineMock(return_value=[ConnRecord()]),
        ), mock.patch.object(ConnRecord, "save", mock.CoroutineMock()):
            await test_module.upgrade(
                profile=self.profile,
            )

    async def test_upgrade_callable(self):
        version_storage_record = await self.storage.find_record(
            type_filter="acapy_version", tag_query={}
        )
        await self.storage.delete_record(version_storage_record)
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), mock.patch.object(
            test_module.yaml,
            "safe_load",
            mock.MagicMock(
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
                settings={
                    "upgrade.from_version": "v0.7.2",
                }
            )

    async def test_upgrade_callable_named_tag(self):
        version_storage_record = await self.storage.find_record(
            type_filter="acapy_version", tag_query={}
        )
        await self.storage.delete_record(version_storage_record)
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), mock.patch.object(
            test_module.yaml,
            "safe_load",
            mock.MagicMock(
                return_value={
                    "v0.7.2": {
                        "resave_records": {
                            "base_record_path": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ]
                        },
                        "update_existing_records": True,
                    },
                    "fix_issue_rev_reg": {"fix_issue_rev_reg_records": True},
                }
            ),
        ):
            await test_module.upgrade(
                settings={
                    "upgrade.named_tags": ["fix_issue_rev_reg"],
                    "upgrade.force_upgrade": True,
                }
            )

    async def test_upgrade_x_same_version(self):
        version_storage_record = await self.storage.find_record(
            type_filter="acapy_version", tag_query={}
        )
        await self.storage.update_record(version_storage_record, f"v{__version__}", {})
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ):
            await test_module.upgrade(
                settings={
                    "upgrade.config_path": "./aries_cloudagent/commands/default_version_upgrade_config.yml",
                }
            )

    async def test_upgrade_missing_from_version(self):
        version_storage_record = await self.storage.find_record(
            type_filter="acapy_version", tag_query={}
        )
        await self.storage.delete_record(version_storage_record)
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), mock.patch.object(
            ConnRecord,
            "query",
            mock.CoroutineMock(return_value=[ConnRecord()]),
        ), mock.patch.object(
            ConnRecord, "save", mock.CoroutineMock()
        ):
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    settings={
                        "upgrade.config_path": "./aries_cloudagent/commands/default_version_upgrade_config.yml",
                    }
                )
            assert "Error during upgrade: No upgrade from version or tags found" in str(
                ctx.exception
            )

    async def test_upgrade_x_callable_not_set(self):
        version_storage_record = await self.storage.find_record(
            type_filter="acapy_version", tag_query={}
        )
        await self.storage.delete_record(version_storage_record)
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), mock.patch.object(
            test_module.yaml,
            "safe_load",
            mock.MagicMock(
                return_value={
                    "v0.7.2": {
                        "resave_records": {
                            "base_record_path": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ]
                        },
                        "update_existing_records": True,
                    },
                    "v0.6.0": {"update_existing_records_b": True},
                }
            ),
        ):
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(
                    settings={
                        "upgrade.from_version": "v0.6.0",
                    }
                )
            assert "No function specified for" in str(ctx.exception)

    async def test_upgrade_x_class_not_found(self):
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), mock.patch.object(
            test_module.yaml,
            "safe_load",
            mock.MagicMock(
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
                    settings={
                        "upgrade.from_version": "v0.7.2",
                    }
                )
            assert "Unknown Record type" in str(ctx.exception)

    async def test_execute(self):
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), mock.patch.object(
            ConnRecord,
            "query",
            mock.CoroutineMock(return_value=[ConnRecord()]),
        ), mock.patch.object(
            ConnRecord, "save", mock.CoroutineMock()
        ), mock.patch.object(
            asyncio, "get_event_loop", mock.MagicMock()
        ) as mock_get_event_loop, mock.patch.object(
            # Normally, this would be a CoroutingMock. However, the coroutine
            # is awaited by run_until_complete, which is mocked out.
            # Use MagicMock to prevent unawaited coroutine warnings.
            test_module,
            "upgrade",
            mock.MagicMock(),
        ):
            mock_get_event_loop.return_value = mock.MagicMock(
                run_until_complete=mock.MagicMock(),
            )
            test_module.execute(
                [
                    "--upgrade-config",
                    "./aries_cloudagent/config/tests/test-acapy-upgrade-config.yaml",
                    "--from-version",
                    "v0.7.0",
                    "--force-upgrade",
                ]
            )

    async def test_upgrade_x_invalid_record_type(self):
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), mock.patch.object(
            test_module.yaml,
            "safe_load",
            mock.MagicMock(
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
                    settings={
                        "upgrade.from_version": "v0.7.2",
                    }
                )
            assert "Only BaseRecord can be resaved" in str(ctx.exception)

    async def test_upgrade_force(self):
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    self.profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ), mock.patch.object(
            test_module.yaml,
            "safe_load",
            mock.MagicMock(
                return_value={
                    "v0.7.2": {
                        "resave_records": {
                            "base_record_path": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ],
                        },
                        "update_existing_records": True,
                    },
                    "v0.7.3": {
                        "update_existing_records": True,
                    },
                    "v0.7.1": {
                        "update_existing_records": False,
                    },
                }
            ),
        ):
            await test_module.upgrade(
                settings={
                    "upgrade.from_version": "v0.7.0",
                    "upgrade.force_upgrade": True,
                }
            )

    async def test_get_upgrade_version_list(self):
        assert len(test_module.get_upgrade_version_list(from_version="v0.7.2")) >= 1

    async def test_add_version_record(self):
        await test_module.add_version_record(self.profile, "v0.7.4")
        version_storage_record = await self.storage.find_record(
            type_filter="acapy_version", tag_query={}
        )
        assert version_storage_record.value == "v0.7.4"
        await self.storage.delete_record(version_storage_record)
        with self.assertRaises(test_module.StorageNotFoundError):
            await self.storage.find_record(type_filter="acapy_version", tag_query={})
        await test_module.add_version_record(self.profile, "v0.7.5")
        version_storage_record = await self.storage.find_record(
            type_filter="acapy_version", tag_query={}
        )
        assert version_storage_record.value == "v0.7.5"

    async def test_upgrade_x_invalid_config(self):
        with mock.patch.object(
            test_module.yaml,
            "safe_load",
            mock.MagicMock(return_value={}),
        ):
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(profile=self.profile)
            assert "No version configs found in" in str(ctx.exception)

    async def test_upgrade_x_params(self):
        with self.assertRaises(UpgradeError) as ctx:
            await test_module.upgrade(profile=self.profile, settings={})
        assert "upgrade requires either profile or settings" in str(ctx.exception)
        with self.assertRaises(UpgradeError) as ctx:
            await test_module.upgrade(profile=self.profile, settings={"...": "..."})
        assert "upgrade requires either profile or settings" in str(ctx.exception)

    def test_main(self):
        with mock.patch.object(
            test_module, "__name__", "__main__"
        ) as mock_name, mock.patch.object(
            test_module, "execute", mock.MagicMock()
        ) as mock_execute:
            test_module.main()
            mock_execute.assert_called_once

    def test_get_explicit_upgrade_option(self):
        assert not test_module.ExplicitUpgradeOption.get("test")
        assert (
            test_module.ExplicitUpgradeOption.get("critical")
            == test_module.ExplicitUpgradeOption.ERROR_AND_STOP
        )
        assert (
            test_module.ExplicitUpgradeOption.get("warning")
            == test_module.ExplicitUpgradeOption.LOG_AND_PROCEED
        )

    async def test_upgrade_explicit_upgrade_required_check(self):
        test_config_dict = {
            "v0.8.1": {
                "resave_records": [
                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                ],
                "update_existing_records": False,
            },
            "v0.7.2": {
                "resave_records": [
                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                ],
                "update_existing_records": False,
            },
            "v0.7.1": {"resave_records": [], "update_existing_records": False},
            "v0.7.0": {"resave_records": [], "update_existing_records": False},
            "v0.6.0": {"resave_records": [], "update_existing_records": False},
        }
        check, to_skip_list, exp_version = test_module.explicit_upgrade_required_check(
            ["v0.6.0", "v0.7.0", "v0.7.1", "v0.7.2", "v0.8.1"],
            test_config_dict,
        )
        assert (check, to_skip_list, exp_version) == (False, [], None)

        check, to_skip_list, exp_version = test_module.explicit_upgrade_required_check(
            ["v0.8.1", "v0.6.0", "v0.7.1", "v0.7.2", "v0.7.0"],
            test_config_dict,
        )
        assert (check, to_skip_list, exp_version) == (False, [], None)

        test_config_dict = {
            "v0.8.1": {
                "resave_records": [
                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                ],
                "update_existing_records": False,
            },
            "v0.7.2": {
                "resave_records": [
                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                ],
                "update_existing_records": False,
                "explicit_upgrade": "warning",
            },
            "v0.7.1": {
                "resave_records": [],
                "update_existing_records": False,
                "explicit_upgrade": "warning",
            },
            "v0.7.0": {"resave_records": [], "update_existing_records": False},
            "v0.6.0": {
                "resave_records": [],
                "update_existing_records": False,
                "explicit_upgrade": "warning",
            },
        }
        check, to_skip_list, exp_version = test_module.explicit_upgrade_required_check(
            ["v0.6.0", "v0.7.0", "v0.7.1", "v0.7.2", "v0.8.1"],
            test_config_dict,
        )
        assert (check, to_skip_list, exp_version) == (
            False,
            ["v0.6.0", "v0.7.1", "v0.7.2"],
            None,
        )

        test_config_dict = {
            "v0.8.1": {
                "resave_records": [
                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                ],
                "update_existing_records": False,
            },
            "v0.7.2": {
                "resave_records": [
                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                ],
                "update_existing_records": False,
                "explicit_upgrade": "critical",
            },
            "v0.7.1": {"resave_records": [], "update_existing_records": False},
            "v0.7.0": {"resave_records": [], "update_existing_records": False},
            "v0.6.0": {"resave_records": [], "update_existing_records": False},
        }
        check, to_skip_list, exp_version = test_module.explicit_upgrade_required_check(
            ["v0.6.0", "v0.7.0", "v0.7.1", "v0.7.2", "v0.8.1"],
            test_config_dict,
        )
        assert (check, to_skip_list, exp_version) == (True, [], "v0.7.2")

        test_config_dict = {
            "v0.8.1": {
                "resave_records": [
                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                ],
                "update_existing_records": False,
            },
            "v0.7.2": {
                "resave_records": [
                    "aries_cloudagent.connections.models.conn_record.ConnRecord"
                ],
                "update_existing_records": False,
                "explicit_upgrade": "warning",
            },
            "v0.7.1": {
                "resave_records": [],
                "update_existing_records": False,
                "explicit_upgrade": "warning",
            },
            "v0.7.0": {
                "resave_records": [],
                "update_existing_records": False,
                "explicit_upgrade": "critical",
            },
            "v0.6.0": {"resave_records": [], "update_existing_records": False},
        }
        check, to_skip_list, exp_version = test_module.explicit_upgrade_required_check(
            ["v0.6.0", "v0.7.0", "v0.7.1", "v0.7.2", "v0.8.1"],
            test_config_dict,
        )
        assert (check, to_skip_list, exp_version) == (True, [], "v0.7.0")

    async def test_upgrade_explicit_check(self):
        self.profile.settings.extend(
            {
                "upgrade.from_version": "v0.7.0",
            }
        )
        with mock.patch.object(
            test_module.yaml,
            "safe_load",
            mock.MagicMock(
                return_value={
                    "v0.7.2": {
                        "resave_records": {
                            "base_record_path": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ],
                        },
                        "update_existing_records": True,
                    },
                    "v0.7.3": {
                        "update_existing_records": True,
                        "explicit_upgrade": "critical",
                    },
                    "v0.7.1": {
                        "update_existing_records": False,
                    },
                }
            ),
        ):
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(profile=self.profile)
            assert "Explicit upgrade flag with critical value found" in str(
                ctx.exception
            )

        with mock.patch.object(
            test_module.yaml,
            "safe_load",
            mock.MagicMock(
                return_value={
                    "v0.7.2": {
                        "resave_records": {
                            "base_record_path": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ],
                        },
                        "update_existing_records": True,
                        "explicit_upgrade": "warning",
                    },
                    "v0.7.3": {
                        "update_existing_records": True,
                        "explicit_upgrade": "critical",
                    },
                    "v0.7.1": {
                        "update_existing_records": False,
                    },
                }
            ),
        ):
            with self.assertRaises(UpgradeError) as ctx:
                await test_module.upgrade(profile=self.profile)
            assert "Explicit upgrade flag with critical value found" in str(
                ctx.exception
            )

        with mock.patch.object(
            test_module, "LOGGER", mock.MagicMock()
        ) as mock_logger, mock.patch.object(
            test_module.yaml,
            "safe_load",
            mock.MagicMock(
                return_value={
                    "v0.7.2": {
                        "resave_records": {
                            "base_record_path": [
                                "aries_cloudagent.connections.models.conn_record.ConnRecord"
                            ],
                        },
                        "update_existing_records": True,
                    },
                    "v0.7.3": {
                        "update_existing_records": True,
                        "explicit_upgrade": "warning",
                    },
                    "v0.7.1": {
                        "update_existing_records": True,
                        "explicit_upgrade": "warning",
                    },
                }
            ),
        ):
            await test_module.upgrade(profile=self.profile)
            assert mock_logger.warning.call_count == 1
            assert mock_logger.info.call_count == 0
