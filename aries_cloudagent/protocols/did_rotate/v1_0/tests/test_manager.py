from unittest import IsolatedAsyncioTestCase

from .....connections.base_manager import (
    BaseConnectionManager,
)
from .....core.in_memory.profile import InMemoryProfile
from .....messaging.responder import BaseResponder, MockResponder
from .....protocols.coordinate_mediation.v1_0.route_manager import RouteManager
from .....protocols.did_rotate.v1_0.manager import (
    DIDRotateManager,
    ReportableDIDRotateError,
    UnrecordableKeysError,
)
from .....protocols.did_rotate.v1_0.messages.ack import RotateAck
from .....protocols.did_rotate.v1_0.messages.problem_report import (
    RotateProblemReport,
)
from .....protocols.did_rotate.v1_0.messages.rotate import Rotate
from .....protocols.did_rotate.v1_0.models.rotate_record import RotateRecord
from .....protocols.didcomm_prefix import DIDCommPrefix
from .....resolver.did_resolver import DIDResolver
from .....tests import mock
from .. import message_types as test_message_types
from ..tests import MockConnRecord, test_conn_id


class TestDIDRotateManager(IsolatedAsyncioTestCase):
    test_endpoint = "http://localhost"

    async def asyncSetUp(self) -> None:
        self.responder = MockResponder()

        self.route_manager = mock.MagicMock(RouteManager)
        self.route_manager.routing_info = mock.CoroutineMock(
            return_value=([], self.test_endpoint)
        )
        self.route_manager.mediation_record_if_id = mock.CoroutineMock(
            return_value=None
        )
        self.route_manager.mediation_record_for_connection = mock.CoroutineMock(
            return_value=None
        )

        self.profile = InMemoryProfile.test_profile(
            bind={
                BaseResponder: self.responder,
                RouteManager: self.route_manager,
                DIDResolver: DIDResolver(),
            }
        )

        self.manager = DIDRotateManager(self.profile)
        assert self.manager.profile

    async def test_hangup(self):
        mock_conn_record = MockConnRecord(test_conn_id, True)
        mock_conn_record.delete_record = mock.CoroutineMock()

        with mock.patch.object(
            self.responder, "send", mock.CoroutineMock()
        ) as mock_send:
            msg = await self.manager.hangup(mock_conn_record)
            mock_conn_record.delete_record.assert_called_once()
            mock_send.assert_called_once()
            assert (
                msg._type == DIDCommPrefix.NEW.value + "/" + test_message_types.HANGUP
            )

    async def test_receive_hangup(self):
        mock_conn_record = MockConnRecord(test_conn_id, True)
        mock_conn_record.delete_record = mock.CoroutineMock()

        await self.manager.receive_hangup(mock_conn_record)
        mock_conn_record.delete_record.assert_called_once()

    async def test_rotate_my_did(self):
        mock_conn_record = MockConnRecord(test_conn_id, True)
        test_to_did = "did:peer:2:testdid"

        with mock.patch.object(
            self.responder, "send", mock.CoroutineMock()
        ) as mock_send:
            msg = await self.manager.rotate_my_did(mock_conn_record, test_to_did)
            mock_send.assert_called_once()
            assert (
                msg._type == DIDCommPrefix.NEW.value + "/" + test_message_types.ROTATE
            )

    async def test_receive_rotate(self):
        mock_conn_record = MockConnRecord(test_conn_id, True)

        test_to_did = "did:peer:2:testdid"

        record = await self.manager.receive_rotate(
            mock_conn_record, Rotate(to_did=test_to_did)
        )

        assert record.RECORD_TYPE == RotateRecord.RECORD_TYPE
        assert record.role == record.ROLE_OBSERVING
        assert record.state == record.STATE_ROTATE_RECEIVED
        assert record.connection_id == mock_conn_record.connection_id

    async def test_receive_rotate_x(self):
        mock_conn_record = MockConnRecord(test_conn_id, True)

        test_to_did = "did:badmethod:1:testdid"
        test_problem_report = ReportableDIDRotateError(
            RotateProblemReport(problem_items=[{"did": test_to_did}])
        )

        with mock.patch.object(
            self.manager, "_ensure_supported_did", side_effect=test_problem_report
        ), mock.patch.object(self.responder, "send", mock.CoroutineMock()) as mock_send:
            await self.manager.receive_rotate(
                mock_conn_record, Rotate(to_did=test_to_did)
            )
            mock_send.assert_called_once_with(
                test_problem_report.message,
                connection_id=mock_conn_record.connection_id,
            )

    @mock.patch.object(
        BaseConnectionManager,
        "record_keys_for_resolvable_did",
        mock.CoroutineMock(),
    )
    async def test_commit_rotate(self, *_):
        mock_conn_record = MockConnRecord(test_conn_id, True)
        mock_conn_record.save = mock.CoroutineMock()

        test_to_did = "did:peer:2:testdid"

        record = await self.manager.receive_rotate(
            mock_conn_record, Rotate(to_did=test_to_did)
        )
        await self.manager.commit_rotate(mock_conn_record, record)

        assert record.state == RotateRecord.STATE_ACK_SENT

    @mock.patch.object(
        BaseConnectionManager,
        "record_keys_for_resolvable_did",
        mock.CoroutineMock(),
    )
    async def test_commit_rotate_x_no_new_did(self, *_):
        mock_conn_record = MockConnRecord(test_conn_id, True)
        mock_conn_record.save = mock.CoroutineMock()

        test_to_did = "did:peer:2:testdid"

        record = await self.manager.receive_rotate(
            mock_conn_record, Rotate(to_did=test_to_did)
        )
        record.new_did = None

        with self.assertRaises(ValueError):
            await self.manager.commit_rotate(mock_conn_record, record)

    async def test_commit_rotate_x_unrecordable_keys(self):
        mock_conn_record = MockConnRecord(test_conn_id, True)
        mock_conn_record.save = mock.CoroutineMock()

        test_to_did = "did:peer:2:testdid"

        record = await self.manager.receive_rotate(
            mock_conn_record, Rotate(to_did=test_to_did)
        )

        with self.assertRaises(UnrecordableKeysError):
            await self.manager.commit_rotate(mock_conn_record, record)

    @mock.patch.object(
        BaseConnectionManager,
        "clear_connection_targets_cache",
        mock.CoroutineMock(),
    )
    async def test_receive_ack(self, *_):
        mock_conn_record = MockConnRecord(test_conn_id, True)
        mock_conn_record.save = mock.CoroutineMock()

        with mock.patch.object(
            RotateRecord,
            "retrieve_by_thread_id",
            return_value=mock.CoroutineMock(
                return_value=mock.MagicMock(
                    new_did="did:peer:2:testdid", delete_record=mock.CoroutineMock()
                )
            ),
        ) as mock_rotate_record:
            await self.manager.receive_ack(mock_conn_record, RotateAck())

            mock_conn_record.save.assert_called_once()
            mock_rotate_record.return_value.delete_record.assert_called_once()

    async def test_receive_ack_x(self):
        mock_conn_record = MockConnRecord(test_conn_id, True)
        mock_conn_record.save = mock.CoroutineMock()

        with mock.patch.object(
            RotateRecord,
            "retrieve_by_thread_id",
            return_value=mock.CoroutineMock(),
        ) as mock_rotate_record:
            mock_rotate_record.return_value.new_did = None
            with self.assertRaises(ValueError):
                await self.manager.receive_ack(mock_conn_record, RotateAck())

    async def test_receive_problem_report(self):
        test_to_did = "did:badmethod:1:testdid"
        mock_problem_report = RotateProblemReport(
            description={"code": 123},
            problem_items=[{"did": test_to_did}],
        )

        with mock.patch.object(
            RotateRecord,
            "retrieve_by_thread_id",
            return_value=mock.CoroutineMock(
                return_value=mock.MagicMock(save=mock.CoroutineMock())
            ),
        ) as mock_rotate_record:
            await self.manager.receive_problem_report(mock_problem_report)

            mock_rotate_record.return_value.save.assert_called_once()
