import asyncio
from time import time
from unittest import IsolatedAsyncioTestCase

from anoncreds import CredentialDefinitionPrivate, KeyCorrectnessProof
from aries_askar import AskarError

from ...anoncreds.issuer import CATEGORY_CRED_DEF_PRIVATE
from ...askar.profile import AskarProfileSession
from ...cache.base import BaseCache
from ...indy.credx.issuer import CATEGORY_CRED_DEF_KEY_PROOF
from ...ledger.multiple_ledger.ledger_requests_executor import IndyLedgerRequestsExecutor
from ...messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from ...messaging.schemas.util import SCHEMA_SENT_RECORD_TYPE
from ...multitenant.base import BaseMultitenantManager
from ...multitenant.manager import MultitenantManager
from ...storage.base import BaseStorage
from ...storage.record import StorageRecord
from ...storage.type import (
    RECORD_TYPE_ACAPY_STORAGE_TYPE,
    RECORD_TYPE_ACAPY_UPGRADING,
    STORAGE_TYPE_VALUE_ANONCREDS,
)
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import anoncreds_upgrade


class TestAnoncredsUpgrade(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile(settings={"wallet.type": "askar"})
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, mock.MagicMock(MultitenantManager, autospec=True)
        )
        self.profile.context.injector.bind_instance(
            BaseCache, mock.MagicMock(BaseCache, autospec=True)
        )

    @mock.patch.object(
        CredentialDefinitionPrivate,
        "load",
        mock.MagicMock(
            return_value=mock.MagicMock(to_json_buffer=mock.MagicMock(return_value=b"{}"))
        ),
    )
    @mock.patch.object(
        KeyCorrectnessProof,
        "load",
        mock.MagicMock(
            return_value=mock.MagicMock(to_json_buffer=mock.MagicMock(return_value=b"{}"))
        ),
    )
    async def test_convert_records_to_anoncreds(self):
        async with self.profile.session() as session:
            storage = session.inject(BaseStorage)

            # Add schema record
            schema_id = "GHjSbphAcdsrZrLjSvsjMp:2:faber-simple:1.1"
            schema_id_parts = schema_id.split(":")
            schema_tags = {
                "schema_id": schema_id,
                "schema_issuer_did": schema_id_parts[0],
                "schema_name": schema_id_parts[-2],
                "schema_version": schema_id_parts[-1],
                "epoch": str(int(time())),
            }
            await storage.add_record(
                StorageRecord(SCHEMA_SENT_RECORD_TYPE, schema_id, schema_tags)
            )

            # Add cred def record
            credential_definition_id = "GHjSbphAcdsrZrLjSvsjMp:3:CL:8:default"
            cred_def_tags = {
                "schema_id": schema_id,
                "schema_issuer_did": schema_id_parts[0],
                "schema_name": schema_id_parts[-2],
                "schema_version": schema_id_parts[-1],
                "issuer_did": "GHjSbphAcdsrZrLjSvsjMp",
                "cred_def_id": credential_definition_id,
                "epoch": str(int(time())),
            }
            await storage.add_record(
                StorageRecord(
                    CRED_DEF_SENT_RECORD_TYPE, credential_definition_id, cred_def_tags
                )
            )

            # Add private cred def record
            await storage.add_record(
                StorageRecord(
                    CATEGORY_CRED_DEF_PRIVATE,
                    b"{}",
                    {},
                    id=credential_definition_id,
                )
            )

            # Add key proof cred def record
            await storage.add_record(
                StorageRecord(
                    CATEGORY_CRED_DEF_KEY_PROOF,
                    b"{}",
                    {},
                    id=credential_definition_id,
                )
            )

            anoncreds_upgrade.IndyLedgerRequestsExecutor = mock.MagicMock(
                IndyLedgerRequestsExecutor, autospec=True
            )
            anoncreds_upgrade.IndyLedgerRequestsExecutor.return_value.get_ledger_for_identifier = mock.CoroutineMock(
                return_value=(
                    None,
                    mock.MagicMock(
                        get_schema=mock.CoroutineMock(
                            return_value={
                                "attrNames": [
                                    "name",
                                    "age",
                                ],
                            },
                        ),
                        get_credential_definition=mock.CoroutineMock(
                            return_value={
                                "type": "CL",
                                "tag": "default",
                                "value": {
                                    "primary": {
                                        "n": "123",
                                    },
                                },
                            },
                        ),
                    ),
                )
            )

        # Need to update private key with a real private key
        with self.assertRaises(AskarError) as err:
            await anoncreds_upgrade.convert_records_to_anoncreds(self.profile)

        assert "Error updating existing entry" in str(err.exception)

    async def test_retry_converting_records(self):
        with mock.patch.object(
            anoncreds_upgrade, "convert_records_to_anoncreds", mock.CoroutineMock()
        ) as mock_convert_records_to_anoncreds:
            mock_convert_records_to_anoncreds.side_effect = [
                Exception("Error"),
                Exception("Error"),
                None,
            ]
            async with self.profile.session() as session:
                storage = session.inject(BaseStorage)
                upgrading_record = StorageRecord(
                    RECORD_TYPE_ACAPY_UPGRADING,
                    anoncreds_upgrade.UPGRADING_RECORD_IN_PROGRESS,
                )
                await storage.add_record(upgrading_record)

            await anoncreds_upgrade.retry_converting_records(
                self.profile, upgrading_record, 0
            )

            assert mock_convert_records_to_anoncreds.call_count == 3

    async def test_upgrade_wallet_to_anoncreds(self):
        # upgrading record not present
        await anoncreds_upgrade.upgrade_wallet_to_anoncreds_if_requested(self.profile)

    async def test_set_storage_type_to_anoncreds_no_existing_record(self):
        async with self.profile.session() as session:
            storage = session.inject(BaseStorage)
            await storage.add_record(
                StorageRecord(
                    RECORD_TYPE_ACAPY_UPGRADING,
                    "true",
                )
            )
            await anoncreds_upgrade.finish_upgrade(self.profile)

            storage_type_record = await storage.find_record(
                RECORD_TYPE_ACAPY_STORAGE_TYPE, tag_query={}
            )
            assert storage_type_record.value == STORAGE_TYPE_VALUE_ANONCREDS

    async def test_set_storage_type_to_anoncreds_has_existing_record(self):
        async with self.profile.session() as session:
            storage = session.inject(BaseStorage)
            await storage.add_record(
                StorageRecord(
                    RECORD_TYPE_ACAPY_STORAGE_TYPE,
                    "askar",
                )
            )
            await storage.add_record(
                StorageRecord(
                    RECORD_TYPE_ACAPY_UPGRADING,
                    "true",
                )
            )
            await anoncreds_upgrade.finish_upgrade(self.profile)
            storage_type_record = await storage.find_record(
                RECORD_TYPE_ACAPY_STORAGE_TYPE, tag_query={}
            )
            assert storage_type_record.value == STORAGE_TYPE_VALUE_ANONCREDS

    async def test_update_if_subwallet_and_set_storage_type_with_subwallet(self):
        async with self.profile.session() as session:
            storage = session.inject(BaseStorage)
            await storage.add_record(
                StorageRecord(
                    RECORD_TYPE_ACAPY_STORAGE_TYPE,
                    "askar",
                )
            )
            await anoncreds_upgrade.finish_upgrade_by_updating_profile_or_shutting_down(
                self.profile, True
            )
            storage_type_record = await storage.find_record(
                RECORD_TYPE_ACAPY_STORAGE_TYPE, tag_query={}
            )
            assert storage_type_record.value == STORAGE_TYPE_VALUE_ANONCREDS
            assert self.profile.context.injector.get_provider(
                BaseCache
            )._instance.flush.called

    async def test_update_if_subwallet_and_set_storage_type_with_base_wallet(self):
        async with self.profile.session() as session:
            storage = session.inject(BaseStorage)
            await storage.add_record(
                StorageRecord(
                    RECORD_TYPE_ACAPY_STORAGE_TYPE,
                    "askar",
                )
            )
        await anoncreds_upgrade.finish_upgrade_by_updating_profile_or_shutting_down(
            self.profile, False
        )

    async def test_failed_upgrade(self):
        async with self.profile.session() as session:
            storage = session.inject(BaseStorage)

            schema_id = "GHjSbphAcdsrZrLjSvsjMp:2:faber-simple:1.1"
            schema_id_parts = schema_id.split(":")
            schema_tags = {
                "schema_id": schema_id,
                "schema_issuer_did": schema_id_parts[0],
                "schema_name": schema_id_parts[-2],
                "schema_version": schema_id_parts[-1],
                "epoch": str(int(time())),
            }
            await storage.add_record(
                StorageRecord(SCHEMA_SENT_RECORD_TYPE, schema_id, schema_tags)
            )
            await storage.add_record(
                StorageRecord(
                    RECORD_TYPE_ACAPY_STORAGE_TYPE,
                    "askar",
                )
            )
            await storage.add_record(
                StorageRecord(
                    RECORD_TYPE_ACAPY_UPGRADING,
                    "true",
                )
            )

            credential_definition_id = "GHjSbphAcdsrZrLjSvsjMp:3:CL:8:default"
            cred_def_tags = {
                "schema_id": schema_id,
                "schema_issuer_did": schema_id_parts[0],
                "schema_name": schema_id_parts[-2],
                "schema_version": schema_id_parts[-1],
                "issuer_did": "GHjSbphAcdsrZrLjSvsjMp",
                "cred_def_id": credential_definition_id,
                "epoch": str(int(time())),
            }
            await storage.add_record(
                StorageRecord(
                    CRED_DEF_SENT_RECORD_TYPE, credential_definition_id, cred_def_tags
                )
            )
            # Add private cred def record
            await storage.add_record(
                StorageRecord(
                    CATEGORY_CRED_DEF_PRIVATE,
                    b"{}",
                    {},
                    id=credential_definition_id,
                )
            )

            # Add key proof cred def record
            await storage.add_record(
                StorageRecord(
                    CATEGORY_CRED_DEF_KEY_PROOF,
                    b"{}",
                    {},
                    id=credential_definition_id,
                )
            )
            anoncreds_upgrade.IndyLedgerRequestsExecutor = mock.MagicMock()
            anoncreds_upgrade.IndyLedgerRequestsExecutor.return_value.get_ledger_for_identifier = mock.CoroutineMock(
                return_value=(
                    None,
                    mock.MagicMock(
                        get_schema=mock.CoroutineMock(
                            return_value={
                                "attrNames": [
                                    "name",
                                    "age",
                                ],
                            },
                        ),
                        get_credential_definition=mock.CoroutineMock(
                            return_value={
                                "type": "CL",
                                "tag": "default",
                                "value": {
                                    "primary": {
                                        "n": "123",
                                    },
                                },
                            },
                        ),
                    ),
                )
            )

            with (
                mock.patch.object(anoncreds_upgrade, "upgrade_and_delete_schema_records"),
                mock.patch.object(
                    anoncreds_upgrade, "upgrade_and_delete_cred_def_records"
                ),
                mock.patch.object(AskarProfileSession, "rollback") as mock_rollback,
                mock.patch.object(
                    AskarProfileSession,
                    "commit",
                    # Don't wait for sleep in retry to speed up test
                ) as mock_commit,
                mock.patch.object(asyncio, "sleep"),
            ):
                """
                Only tests schemas and cred_defs failing to upgrade because the other objects are
                hard to mock. These tests should be enough to cover them as the logic is the same.
                """

                # Schemas fails to upgrade
                anoncreds_upgrade.upgrade_and_delete_schema_records = mock.CoroutineMock(
                    # Needs to fail 5 times because of the retry logic
                    side_effect=[
                        Exception("Error"),
                        Exception("Error"),
                        Exception("Error"),
                        Exception("Error"),
                        Exception("Error"),
                    ]
                )
                await anoncreds_upgrade.upgrade_wallet_to_anoncreds_if_requested(
                    self.profile
                )
                assert mock_rollback.called
                assert not mock_commit.called
                # Upgrading record should not be deleted
                with self.assertRaises(Exception):
                    await storage.find_record(
                        type_filter=RECORD_TYPE_ACAPY_UPGRADING, tag_query={}
                    )

                storage_type_record = await storage.find_record(
                    type_filter=RECORD_TYPE_ACAPY_STORAGE_TYPE, tag_query={}
                )
                # Storage type should not be updated
                assert storage_type_record.value == "askar"

                # Cred_defs fails to upgrade
                anoncreds_upgrade.upgrade_and_delete_cred_def_records = (
                    mock.CoroutineMock(
                        side_effect=[
                            Exception("Error"),
                            Exception("Error"),
                            Exception("Error"),
                            Exception("Error"),
                            Exception("Error"),
                        ]
                    )
                )
                await anoncreds_upgrade.upgrade_wallet_to_anoncreds_if_requested(
                    self.profile
                )
                assert mock_rollback.called
                assert not mock_commit.called
                # Upgrading record should not be deleted
                with self.assertRaises(Exception):
                    await storage.find_record(
                        type_filter=RECORD_TYPE_ACAPY_UPGRADING, tag_query={}
                    )

                storage_type_record = await storage.find_record(
                    type_filter=RECORD_TYPE_ACAPY_STORAGE_TYPE, tag_query={}
                )
                # Storage type should not be updated
                assert storage_type_record.value == "askar"
