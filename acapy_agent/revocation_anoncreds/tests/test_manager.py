import json
from unittest import IsolatedAsyncioTestCase

import pytest

from ...anoncreds.issuer import AnonCredsIssuer
from ...protocols.issue_credential.v1_0.models.credential_exchange import (
    V10CredentialExchange,
)
from ...protocols.issue_credential.v2_0.models.cred_ex_record import V20CredExRecord
from ...revocation.models.issuer_cred_rev_record import IssuerCredRevRecord
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import manager as test_module
from ..manager import RevocationManager, RevocationManagerError

TEST_DID = "LjgpST2rjsoxYegQDRm7EL"
SCHEMA_NAME = "bc-reg"
SCHEMA_TXN = 12
SCHEMA_ID = f"{TEST_DID}:2:{SCHEMA_NAME}:1.0"
CRED_DEF_ID = f"{TEST_DID}:3:CL:12:tag1"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:tag1"
TAILS_DIR = "/tmp/indy/revocation/tails_files"
TAILS_HASH = "8UW1Sz5cqoUnK9hqQk7nvtKK65t7Chu3ui866J23sFyJ"
TAILS_LOCAL = f"{TAILS_DIR}/{TAILS_HASH}"


class TestRevocationManager(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        self.manager = RevocationManager(self.profile)

    @pytest.mark.skip(reason="AnonCreds-break")
    async def test_revoke_credential_publish(self):
        CRED_EX_ID = "dummy-cxid"
        CRED_REV_ID = "1"
        mock_issuer_rev_reg_record = mock.MagicMock(
            revoc_reg_id=REV_REG_ID,
            tails_local_path=TAILS_LOCAL,
            send_entry=mock.CoroutineMock(),
            clear_pending=mock.CoroutineMock(),
            pending_pub=["2"],
        )
        issuer = mock.MagicMock(AnonCredsIssuer, autospec=True)
        issuer.revoke_credentials = mock.AsyncMock(
            return_value=(
                json.dumps(
                    {
                        "ver": "1.0",
                        "value": {
                            "prevAccum": "1 ...",
                            "accum": "21 ...",
                            "issued": [1],
                        },
                    }
                ),
                [],
            )
        )
        self.profile.context.injector.bind_instance(AnonCredsIssuer, issuer)

        with (
            mock.patch.object(
                test_module.IssuerCredRevRecord,
                "retrieve_by_cred_ex_id",
                mock.CoroutineMock(),
            ) as mock_retrieve,
            mock.patch.object(test_module, "IndyRevocation", autospec=True) as revoc,
            mock.patch.object(
                test_module.IssuerRevRegRecord,
                "retrieve_by_id",
                mock.CoroutineMock(return_value=mock_issuer_rev_reg_record),
            ),
        ):
            mock_retrieve.return_value = mock.MagicMock(
                rev_reg_id="dummy-rr-id", cred_rev_id=CRED_REV_ID
            )
            mock_rev_reg = mock.MagicMock(
                get_or_fetch_local_tails_path=mock.CoroutineMock()
            )
            revoc.return_value.get_issuer_rev_reg_record = mock.CoroutineMock(
                return_value=mock_issuer_rev_reg_record
            )
            revoc.return_value.get_ledger_registry = mock.CoroutineMock(
                return_value=mock_rev_reg
            )

            await self.manager.revoke_credential_by_cred_ex_id(CRED_EX_ID, publish=True)

        issuer.revoke_credentials.assert_awaited_once_with(
            mock_issuer_rev_reg_record.cred_def_id,
            mock_issuer_rev_reg_record.revoc_reg_id,
            mock_issuer_rev_reg_record.tails_local_path,
            ["2", "1"],
        )

    async def test_revoke_cred_by_cxid_not_found(self):
        CRED_EX_ID = "dummy-cxid"

        with mock.patch.object(
            test_module.IssuerCredRevRecord,
            "retrieve_by_cred_ex_id",
            mock.CoroutineMock(),
        ) as mock_retrieve:
            mock_retrieve.side_effect = test_module.StorageNotFoundError("no such rec")

            issuer = mock.MagicMock(AnonCredsIssuer, autospec=True)
            self.profile.context.injector.bind_instance(AnonCredsIssuer, issuer)

            with self.assertRaises(RevocationManagerError):
                await self.manager.revoke_credential_by_cred_ex_id(CRED_EX_ID)

    @pytest.mark.skip(reason="AnonCreds-break")
    async def test_revoke_credential_no_rev_reg_rec(self):
        CRED_REV_ID = "1"
        V10CredentialExchange(
            credential_exchange_id="dummy-cxid",
            credential_definition_id=CRED_DEF_ID,
            role=V10CredentialExchange.ROLE_ISSUER,
            revocation_id=CRED_REV_ID,
            revoc_reg_id=REV_REG_ID,
        )

        with mock.patch.object(test_module, "IndyRevocation", autospec=True) as revoc:
            revoc.return_value.get_issuer_rev_reg_record = mock.CoroutineMock(
                return_value=None
            )

            issuer = mock.MagicMock(AnonCredsIssuer, autospec=True)
            self.profile.context.injector.bind_instance(AnonCredsIssuer, issuer)

            with self.assertRaises(RevocationManagerError):
                await self.manager.revoke_credential(REV_REG_ID, CRED_REV_ID)

    @pytest.mark.skip(reason="AnonCreds-break")
    async def test_revoke_credential_pend(self):
        CRED_REV_ID = "1"
        mock_issuer_rev_reg_record = mock.MagicMock(mark_pending=mock.AsyncMock())
        issuer = mock.MagicMock(AnonCredsIssuer, autospec=True)
        self.profile.context.injector.bind_instance(AnonCredsIssuer, issuer)

        with (
            mock.patch.object(test_module, "IndyRevocation", autospec=True) as revoc,
            mock.patch.object(
                self.profile,
                "session",
                mock.MagicMock(return_value=self.profile.session()),
            ) as session,
            mock.patch.object(
                self.profile,
                "transaction",
                mock.MagicMock(return_value=session.return_value),
            ) as session,
            mock.patch.object(
                test_module.IssuerRevRegRecord,
                "retrieve_by_id",
                mock.CoroutineMock(return_value=mock_issuer_rev_reg_record),
            ),
        ):
            revoc.return_value.get_issuer_rev_reg_record = mock.CoroutineMock(
                return_value=mock_issuer_rev_reg_record
            )

            await self.manager.revoke_credential(REV_REG_ID, CRED_REV_ID, False)
            mock_issuer_rev_reg_record.mark_pending.assert_called_once_with(
                session.return_value, CRED_REV_ID
            )

        issuer.revoke_credentials.assert_not_awaited()

    @pytest.mark.skip(reason="AnonCreds-break")
    async def test_publish_pending_revocations_basic(self):
        deltas = [
            {
                "ver": "1.0",
                "value": {"prevAccum": "1 ...", "accum": "21 ...", "issued": [1, 2, 3]},
            },
            {
                "ver": "1.0",
                "value": {
                    "prevAccum": "21 ...",
                    "accum": "36 ...",
                    "issued": [1, 2, 3],
                },
            },
        ]

        mock_issuer_rev_reg_record = mock.MagicMock(
            revoc_reg_id=REV_REG_ID,
            tails_local_path=TAILS_LOCAL,
            pending_pub=["1", "2"],
            send_entry=mock.CoroutineMock(),
            clear_pending=mock.CoroutineMock(),
        )
        with (
            mock.patch.object(
                test_module.IssuerRevRegRecord,
                "query_by_pending",
                mock.CoroutineMock(return_value=[mock_issuer_rev_reg_record]),
            ),
            mock.patch.object(
                test_module.IssuerRevRegRecord,
                "retrieve_by_id",
                mock.CoroutineMock(return_value=mock_issuer_rev_reg_record),
            ),
        ):
            issuer = mock.MagicMock(AnonCredsIssuer, autospec=True)
            issuer.merge_revocation_registry_deltas = mock.AsyncMock(side_effect=deltas)

            issuer.revoke_credentials = mock.CoroutineMock(
                side_effect=[(json.dumps(delta), []) for delta in deltas]
            )
            self.profile.context.injector.bind_instance(AnonCredsIssuer, issuer)

            result = await self.manager.publish_pending_revocations()
            assert result == {REV_REG_ID: ["1", "2"]}
            mock_issuer_rev_reg_record.clear_pending.assert_called_once()

    @pytest.mark.skip(reason="AnonCreds-break")
    async def test_publish_pending_revocations_1_rev_reg_all(self):
        deltas = [
            {
                "ver": "1.0",
                "value": {"prevAccum": "1 ...", "accum": "21 ...", "issued": [1, 2, 3]},
            },
            {
                "ver": "1.0",
                "value": {
                    "prevAccum": "21 ...",
                    "accum": "36 ...",
                    "issued": [1, 2, 3],
                },
            },
        ]

        mock_issuer_rev_reg_records = [
            mock.MagicMock(
                record_id=0,
                revoc_reg_id=REV_REG_ID,
                tails_local_path=TAILS_LOCAL,
                pending_pub=["1", "2"],
                send_entry=mock.CoroutineMock(),
                clear_pending=mock.CoroutineMock(),
            ),
            mock.MagicMock(
                record_id=1,
                revoc_reg_id=f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:tag2",
                tails_local_path=TAILS_LOCAL,
                pending_pub=["9", "99"],
                send_entry=mock.CoroutineMock(),
                clear_pending=mock.CoroutineMock(),
            ),
        ]
        with (
            mock.patch.object(
                test_module.IssuerRevRegRecord,
                "query_by_pending",
                mock.CoroutineMock(return_value=mock_issuer_rev_reg_records),
            ),
            mock.patch.object(
                test_module.IssuerRevRegRecord,
                "retrieve_by_id",
                mock.CoroutineMock(
                    side_effect=lambda _, id, **args: mock_issuer_rev_reg_records[id]
                ),
            ),
        ):
            issuer = mock.MagicMock(AnonCredsIssuer, autospec=True)
            issuer.merge_revocation_registry_deltas = mock.AsyncMock(side_effect=deltas)

            issuer.revoke_credentials = mock.CoroutineMock(
                side_effect=[(json.dumps(delta), []) for delta in deltas]
            )
            self.profile.context.injector.bind_instance(AnonCredsIssuer, issuer)

            result = await self.manager.publish_pending_revocations({REV_REG_ID: None})
            assert result == {REV_REG_ID: ["1", "2"]}
            mock_issuer_rev_reg_records[0].clear_pending.assert_called_once()
            mock_issuer_rev_reg_records[1].clear_pending.assert_not_called()

    @pytest.mark.skip(reason="AnonCreds-break")
    async def test_publish_pending_revocations_1_rev_reg_some(self):
        deltas = [
            {
                "ver": "1.0",
                "value": {"prevAccum": "1 ...", "accum": "21 ...", "issued": [1, 2, 3]},
            },
            {
                "ver": "1.0",
                "value": {
                    "prevAccum": "21 ...",
                    "accum": "36 ...",
                    "issued": [1, 2, 3],
                },
            },
        ]

        mock_issuer_rev_reg_records = [
            mock.MagicMock(
                record_id=0,
                revoc_reg_id=REV_REG_ID,
                tails_local_path=TAILS_LOCAL,
                pending_pub=["1", "2"],
                send_entry=mock.CoroutineMock(),
                clear_pending=mock.CoroutineMock(),
            ),
            mock.MagicMock(
                record_id=1,
                revoc_reg_id=f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:tag2",
                tails_local_path=TAILS_LOCAL,
                pending_pub=["9", "99"],
                send_entry=mock.CoroutineMock(),
                clear_pending=mock.CoroutineMock(),
            ),
        ]
        with (
            mock.patch.object(
                test_module.IssuerRevRegRecord,
                "query_by_pending",
                mock.CoroutineMock(return_value=mock_issuer_rev_reg_records),
            ),
            mock.patch.object(
                test_module.IssuerRevRegRecord,
                "retrieve_by_id",
                mock.CoroutineMock(
                    side_effect=lambda _, id, **args: mock_issuer_rev_reg_records[id]
                ),
            ),
        ):
            issuer = mock.MagicMock(AnonCredsIssuer, autospec=True)
            issuer.merge_revocation_registry_deltas = mock.AsyncMock(side_effect=deltas)

            issuer.revoke_credentials = mock.CoroutineMock(
                side_effect=[(json.dumps(delta), []) for delta in deltas]
            )
            self.profile.context.injector.bind_instance(AnonCredsIssuer, issuer)

            result = await self.manager.publish_pending_revocations({REV_REG_ID: "2"})
            assert result == {REV_REG_ID: ["2"]}
            mock_issuer_rev_reg_records[0].clear_pending.assert_called_once()
            mock_issuer_rev_reg_records[1].clear_pending.assert_not_called()

    @pytest.mark.skip(reason="AnonCreds-break")
    async def test_clear_pending(self):
        mock_issuer_rev_reg_records = [
            mock.MagicMock(
                revoc_reg_id=REV_REG_ID,
                tails_local_path=TAILS_LOCAL,
                pending_pub=[],
                clear_pending=mock.CoroutineMock(),
            ),
            mock.MagicMock(
                revoc_reg_id=f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:tag2",
                tails_local_path=TAILS_LOCAL,
                pending_pub=[],
                clear_pending=mock.CoroutineMock(),
            ),
        ]
        with mock.patch.object(
            test_module.IssuerRevRegRecord,
            "query_by_pending",
            mock.CoroutineMock(return_value=mock_issuer_rev_reg_records),
        ):
            result = await self.manager.clear_pending_revocations()
            assert result == {}

    @pytest.mark.skip(reason="AnonCreds-break")
    async def test_clear_pending_1_rev_reg_all(self):
        mock_issuer_rev_reg_records = [
            mock.MagicMock(
                revoc_reg_id=REV_REG_ID,
                tails_local_path=TAILS_LOCAL,
                pending_pub=["1", "2"],
                clear_pending=mock.CoroutineMock(),
            ),
            mock.MagicMock(
                revoc_reg_id=f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:tag2",
                tails_local_path=TAILS_LOCAL,
                pending_pub=["9", "99"],
                clear_pending=mock.CoroutineMock(),
            ),
        ]
        with mock.patch.object(
            test_module.IssuerRevRegRecord,
            "query_by_pending",
            mock.CoroutineMock(return_value=mock_issuer_rev_reg_records),
        ):
            result = await self.manager.clear_pending_revocations({REV_REG_ID: None})
            assert result == {
                REV_REG_ID: ["1", "2"],
                f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:tag2": ["9", "99"],
            }

    @pytest.mark.skip(reason="AnonCreds-break")
    async def test_clear_pending_1_rev_reg_some(self):
        mock_issuer_rev_reg_records = [
            mock.MagicMock(
                revoc_reg_id=REV_REG_ID,
                tails_local_path=TAILS_LOCAL,
                pending_pub=["1", "2"],
                clear_pending=mock.CoroutineMock(),
            ),
            mock.MagicMock(
                revoc_reg_id=f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:tag2",
                tails_local_path=TAILS_LOCAL,
                pending_pub=["99"],
                clear_pending=mock.CoroutineMock(),
            ),
        ]
        with mock.patch.object(
            test_module.IssuerRevRegRecord,
            "query_by_pending",
            mock.CoroutineMock(return_value=mock_issuer_rev_reg_records),
        ):
            result = await self.manager.clear_pending_revocations({REV_REG_ID: ["9"]})
            assert result == {
                REV_REG_ID: ["1", "2"],
                f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:tag2": ["99"],
            }

    async def test_retrieve_records(self):
        session = await self.profile.session()
        for index in range(2):
            exchange_record = V10CredentialExchange(
                connection_id=str(index),
                thread_id=str(1000 + index),
                initiator=V10CredentialExchange.INITIATOR_SELF,
                role=V10CredentialExchange.ROLE_ISSUER,
            )
            await exchange_record.save(session)

        for _ in range(2):  # second pass gets from cache
            for index in range(2):
                ret_ex = await V10CredentialExchange.retrieve_by_connection_and_thread(
                    session, str(index), str(1000 + index)
                )
                assert ret_ex.connection_id == str(index)
                assert ret_ex.thread_id == str(1000 + index)

    async def test_set_revoked_state_v1(self):
        CRED_REV_ID = "1"

        async with self.profile.session() as session:
            exchange_record = V10CredentialExchange(
                connection_id="mark-revoked-cid",
                thread_id="mark-revoked-tid",
                initiator=V10CredentialExchange.INITIATOR_SELF,
                revoc_reg_id=REV_REG_ID,
                revocation_id=CRED_REV_ID,
                role=V10CredentialExchange.ROLE_ISSUER,
                state=V10CredentialExchange.STATE_ISSUED,
            )
            await exchange_record.save(session)

            crev_record = IssuerCredRevRecord(
                cred_ex_id=exchange_record.credential_exchange_id,
                cred_def_id=CRED_DEF_ID,
                rev_reg_id=REV_REG_ID,
                cred_rev_id=CRED_REV_ID,
                state=IssuerCredRevRecord.STATE_ISSUED,
            )
            await crev_record.save(session)

        await self.manager.set_cred_revoked_state(REV_REG_ID, [CRED_REV_ID])

        async with self.profile.session() as session:
            check_exchange_record = await V10CredentialExchange.retrieve_by_id(
                session, exchange_record.credential_exchange_id
            )
            assert (
                check_exchange_record.state
                == V10CredentialExchange.STATE_CREDENTIAL_REVOKED
            )

            check_crev_record = await IssuerCredRevRecord.retrieve_by_id(
                session, crev_record.record_id
            )
            assert check_crev_record.state == IssuerCredRevRecord.STATE_REVOKED

    async def test_set_revoked_state_v2(self):
        CRED_REV_ID = "1"

        async with self.profile.session() as session:
            exchange_record = V20CredExRecord(
                connection_id="mark-revoked-cid",
                thread_id="mark-revoked-tid",
                initiator=V20CredExRecord.INITIATOR_SELF,
                role=V20CredExRecord.ROLE_ISSUER,
                state=V20CredExRecord.STATE_ISSUED,
            )
            await exchange_record.save(session)

            crev_record = IssuerCredRevRecord(
                cred_ex_id=exchange_record.cred_ex_id,
                cred_def_id=CRED_DEF_ID,
                rev_reg_id=REV_REG_ID,
                cred_rev_id=CRED_REV_ID,
                state=IssuerCredRevRecord.STATE_ISSUED,
            )
            await crev_record.save(session)

        await self.manager.set_cred_revoked_state(REV_REG_ID, [CRED_REV_ID])

        async with self.profile.session() as session:
            check_exchange_record = await V20CredExRecord.retrieve_by_id(
                session, exchange_record.cred_ex_id
            )
            assert check_exchange_record.state == V20CredExRecord.STATE_CREDENTIAL_REVOKED

            check_crev_record = await IssuerCredRevRecord.retrieve_by_id(
                session, crev_record.record_id
            )
            assert check_crev_record.state == IssuerCredRevRecord.STATE_REVOKED
