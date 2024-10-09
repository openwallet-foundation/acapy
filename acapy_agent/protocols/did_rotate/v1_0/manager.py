"""DID Rotate manager.

Manages and tracks the state of the DID Rotate protocol.
"""

from ....connections.base_manager import (
    BaseConnectionManager,
    BaseConnectionManagerError,
)
from ....connections.models.conn_record import ConnRecord
from ....core.profile import Profile
from ....messaging.responder import BaseResponder
from ....resolver.base import DIDMethodNotSupported, DIDNotFound
from ....resolver.did_resolver import DIDResolver
from .messages import Hangup, Rotate, RotateAck, RotateProblemReport
from .models import RotateRecord


class DIDRotateManagerError(Exception):
    """Raised when an error occurs during a DID Rotate protocol flow."""


class ReportableDIDRotateError(DIDRotateManagerError):
    """Base class for reportable errors."""

    def __init__(self, message: RotateProblemReport):
        """Initialize the ReportableDIDRotateError."""
        self.message = message


class UnresolvableDIDError(ReportableDIDRotateError):
    """Raised when a DID cannot be resolved."""


class UnsupportedDIDMethodError(ReportableDIDRotateError):
    """Raised when a DID method is not supported."""


class UnresolvableDIDCommServicesError(ReportableDIDRotateError):
    """Raised when DIDComm services cannot be resolved."""


class UnrecordableKeysError(ReportableDIDRotateError):
    """Raised when keys cannot be recorded for a resolvable DID."""


class DIDRotateManager:
    """DID Rotate Manager.

    Manages and tracks the state of the DID Rotate protocol.

    This mechanism allows a party in a relationship to change the DID they use
    to identify themselves in that relationship. This may be used to switch DID
    methods, but also to switch to a new DID within the same DID method. For
    non-updatable DID methods, this allows updating DID Doc attributes such as
    service endpoints. Inspired by (but different from) the DID rotation
    feature of the DIDComm Messaging (DIDComm v2) spec.

    DID Rotation is a pre-rotate operation. We send notification of rotation
    to the observing party before we rotate the DID. This allows the observing
    party to update their DID for the rotating party and notify the rotating
    party of any issues with the received DID.

    DID Rotation has two roles: the rotating party and the observing party.

    This manager is responsible for both of the possible roles in the protocol.
    """

    def __init__(self, profile: Profile):
        """Initialize DID Rotate Manager."""
        self.profile = profile

    async def hangup(self, conn: ConnRecord) -> Hangup:
        """Hangup the connection.

        Args:
            conn (ConnRecord): The connection to hangup.
        """

        hangup = Hangup()

        async with self.profile.session() as session:
            await conn.delete_record(session)

        responder = self.profile.inject(BaseResponder)
        await responder.send(hangup, connection_id=conn.connection_id)

        return hangup

    async def rotate_my_did(self, conn: ConnRecord, new_did: str) -> Rotate:
        """Rotate my DID.

        Args:
            conn (ConnRecord): The connection to rotate the DID for.
            new_did (str): The new DID to use for the connection.
        """

        record = RotateRecord(
            role=RotateRecord.ROLE_ROTATING,
            state=RotateRecord.STATE_ROTATE_SENT,
            connection_id=conn.connection_id,
            new_did=new_did,
        )
        rotate = Rotate(to_did=new_did)
        record.thread_id = rotate._message_id

        responder = self.profile.inject(BaseResponder)
        await responder.send(rotate, connection_id=conn.connection_id)

        async with self.profile.session() as session:
            await record.save(session, reason="Sent rotate message")

        return rotate

    async def receive_rotate(self, conn: ConnRecord, rotate: Rotate) -> RotateRecord:
        """Receive rotate message.

        Args:
            conn (ConnRecord): The connection to rotate the DID for.
            rotate (Rotate): The received rotate message.
        """
        record = RotateRecord(
            role=RotateRecord.ROLE_OBSERVING,
            state=RotateRecord.STATE_ROTATE_RECEIVED,
            connection_id=conn.connection_id,
            new_did=rotate.to_did,
            thread_id=rotate._message_id,
        )

        try:
            await self._ensure_supported_did(rotate.to_did)
        except ReportableDIDRotateError as err:
            responder = self.profile.inject(BaseResponder)
            err.message.assign_thread_from(rotate)
            await responder.send(err.message, connection_id=conn.connection_id)

        async with self.profile.session() as session:
            await record.save(session, reason="Received rotate message")

        return record

    async def commit_rotate(self, conn: ConnRecord, record: RotateRecord):
        """Commit rotate.

        Args:
            conn (ConnRecord): The connection to rotate the DID for.
            record (RotateRecord): The rotate record.
        """
        record.state = RotateRecord.STATE_ACK_SENT
        if not record.new_did:
            raise ValueError("No new DID stored in record")

        conn_mgr = BaseConnectionManager(self.profile)
        try:
            await conn_mgr.record_keys_for_resolvable_did(record.new_did)
        except BaseConnectionManagerError:
            raise UnrecordableKeysError(
                RotateProblemReport.unrecordable_keys(record.new_did)
            )

        conn.their_did = record.new_did

        ack = RotateAck()
        ack.assign_thread_id(thid=record.thread_id)

        responder = self.profile.inject(BaseResponder)
        await responder.send(ack, connection_id=conn.connection_id)

        async with self.profile.session() as session:
            # Don't emit a connection event for this change
            # Controllers should listen for the rotate event instead
            await conn.save(session, reason="Their DID rotated", event=False)
            await record.save(session, reason="Sent rotate ack")

        # TODO it would be better if the cache key included DIDs so we don't
        # have to manually clear it. This is a bigger change than a first pass
        # warrants though.
        await conn_mgr.clear_connection_targets_cache(conn.connection_id)

    async def receive_ack(self, conn: ConnRecord, ack: RotateAck):
        """Receive rotate ack message.

        Args:
            conn (ConnRecord): The connection to rotate the DID for.
            ack (RotateAck): The received rotate ack message.
        """
        async with self.profile.session() as session:
            record = await RotateRecord.retrieve_by_thread_id(session, ack._thread_id)

        record.state = RotateRecord.STATE_ACK_RECEIVED
        if not record.new_did:
            raise ValueError("No new DID stored in record")

        conn.my_did = record.new_did
        async with self.profile.session() as session:
            # Don't emit a connection event for this change
            # Controllers should listen for the rotate event instead
            await conn.save(session, reason="My DID rotated", event=False)
            # At this point the rotate is complete, so we can delete the record
            await record.delete_record(session)

        # TODO it would be better if the cache key included DIDs so we don't
        # have to manually clear it. This is a bigger change than a first pass
        # warrants though.
        conn_mgr = BaseConnectionManager(self.profile)
        await conn_mgr.clear_connection_targets_cache(conn.connection_id)

    async def receive_problem_report(self, problem_report: RotateProblemReport):
        """Receive problem report message.

        Args:
            conn (ConnRecord): The connection to rotate the DID for.
            problem_report (ProblemReport): The received problem report message.
        """
        async with self.profile.session() as session:
            record = await RotateRecord.retrieve_by_thread_id(
                session, problem_report._thread_id
            )

        record.state = RotateRecord.STATE_FAILED
        # Base ProblemReportSchema requires this value be present
        assert problem_report.description
        record.error = problem_report.description["code"]
        async with self.profile.session() as session:
            await record.save(session, reason="Received problem report")

    async def receive_hangup(self, conn: ConnRecord):
        """Receive hangup message.

        Args:
            conn (ConnRecord): The connection to rotate the DID for.
            hangup (Hangup): The received hangup message.
        """
        async with self.profile.session() as session:
            await conn.delete_record(session)

    async def _ensure_supported_did(self, did: str):
        """Check if the DID is supported."""
        resolver = self.profile.inject(DIDResolver)
        conn_mgr = BaseConnectionManager(self.profile)
        try:
            await resolver.resolve(self.profile, did)
        except DIDMethodNotSupported:
            raise UnsupportedDIDMethodError(RotateProblemReport.unsupported_method(did))
        except DIDNotFound:
            raise UnresolvableDIDError(RotateProblemReport.unresolvable(did))

        try:
            await conn_mgr.resolve_didcomm_services(did)
        except BaseConnectionManagerError:
            raise UnresolvableDIDCommServicesError(
                RotateProblemReport.unresolvable_services(did)
            )
