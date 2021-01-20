"""Classes to manage connections."""

import logging
import asyncio

from typing import Mapping, Sequence, Optional

from ....connections.models.conn_record import ConnRecord
from ....core.error import BaseError
from ....core.profile import ProfileSession
from ....multitenant.manager import MultitenantManager
from ....wallet.base import BaseWallet
from ....wallet.util import naked_to_did_key

from ...didexchange.v1_0.manager import DIDXManager
from ...didcomm_prefix import DIDCommPrefix
from ...issue_credential.v1_0.models.credential_exchange import V10CredentialExchange
from ...present_proof.v1_0.message_types import PRESENTATION_REQUEST
from ...present_proof.v1_0.models.presentation_exchange import V10PresentationExchange

from .messages.invitation import InvitationMessage
from .messages.reuse import HandshakeReuse
from .messages.reuse_accept import HandshakeReuseAccept
from .messages.problem_report import ProblemReportReason, ProblemReport
from ...connections.v1_0.BaseConnectionManager import BaseConnectionManager
from ....transport.inbound.receipt import MessageReceipt
from ....storage.error import StorageNotFoundError

from .messages.service import Service as ServiceMessage
from .models.invitation import InvitationRecord
from .models.reuse_msg import ConnReuseMessageRecord

from ...connections.v1_0.manager import ConnectionManager
from ...present_proof.v1_0.manager import PresentationManager
# from ...present_proof.v1_0.messages.presentation_request import PresentationRequest
from ...connections.v1_0.messages.connection_invitation import ConnectionInvitation
from ....ledger.base import BaseLedger
from ....wallet.util import did_key_to_naked
from ....messaging.responder import BaseResponder


DIDX_INVITATION = "didexchange/1.0"
CONNECTION_INVITATION = "connections/1.0"


class OutOfBandManagerError(BaseError):
    """Out of band error."""
    originating_invi_msg_id = None
    originating_reuse_msg_id = None


class OutOfBandManagerNotImplementedError(BaseError):
    """Out of band error for unimplemented functionality."""


class OutOfBandManager(BaseConnectionManager):
    """Class for managing out of band messages."""

    def __init__(self, session: ProfileSession):
        """
        Initialize a OutOfBandManager.

        Args:
            session: The profile session for this out of band manager
        """
        self._session = session
        self._logger = logging.getLogger(__name__)
        super().__init__(self, self._session)

    @property
    def session(self) -> ProfileSession:
        """
        Accessor for the current profile session.

        Returns:
            The profile session for this connection manager

        """
        return self._session

    async def create_invitation(
        self,
        my_label: str = None,
        my_endpoint: str = None,
        auto_accept: bool = None,
        public: bool = False,
        include_handshake: bool = False,
        multi_use: bool = False,
        alias: str = None,
        attachments: Sequence[Mapping] = None,
        metadata: dict = None,
    ) -> InvitationRecord:
        """
        Generate new connection invitation.

        This interaction represents an out-of-band communication channel. In the future
        and in practice, these sort of invitations will be received over any number of
        channels such as SMS, Email, QR Code, NFC, etc.

        Args:
            my_label: label for this connection
            my_endpoint: endpoint where other party can reach me
            auto_accept: auto-accept a corresponding connection request
                (None to use config)
            public: set to create an invitation from the public DID
            multi_use: set to True to create an invitation for multiple use
            alias: optional alias to apply to connection for later use
            include_handshake: whether to include handshake protocols
            attachments: list of dicts in form of {"id": ..., "type": ...}

        Returns:
            Invitation record

        """
        if not (include_handshake or attachments):
            raise OutOfBandManagerError(
                "Invitation must include handshake protocols, "
                "request attachments, or both"
            )

        wallet = self._session.inject(BaseWallet)

        # Multitenancy setup
        multitenant_mgr = self._session.inject(MultitenantManager, required=False)
        wallet_id = self._session.settings.get("wallet.id")

        accept = bool(
            auto_accept
            or (
                auto_accept is None
                and self._session.settings.get("debug.auto_accept_requests")
            )
        )

        message_attachments = []
        for atch in attachments or []:
            a_type = atch.get("type")
            a_id = atch.get("id")

            if a_type == "credential-offer":
                cred_ex_rec = await V10CredentialExchange.retrieve_by_id(
                    self._session,
                    a_id,
                )
                message_attachments.append(
                    InvitationMessage.wrap_message(cred_ex_rec.credential_offer_dict)
                )
            elif a_type == "present-proof":
                pres_ex_rec = await V10PresentationExchange.retrieve_by_id(
                    self._session,
                    a_id,
                )
                message_attachments.append(
                    InvitationMessage.wrap_message(
                        pres_ex_rec.presentation_request_dict
                    )
                )
            else:
                raise OutOfBandManagerError(f"Unknown attachment type: {a_type}")

        if public:
            if not self._session.settings.get("public_invites"):
                raise OutOfBandManagerError("Public invitations are not enabled")

            public_did = await wallet.get_public_did()
            if not public_did:
                raise OutOfBandManagerError(
                    "Cannot create public invitation with no public DID"
                )

            if multi_use:
                raise OutOfBandManagerError(
                    "Cannot use public and multi_use at the same time"
                )

            if metadata:
                raise OutOfBandManagerError(
                    "Cannot store metadata on public invitations"
                )

            invi_msg = InvitationMessage(
                label=my_label or self._session.settings.get("default_label"),
                handshake_protocols=(
                    [DIDCommPrefix.qualify_current(DIDX_INVITATION)]
                    if include_handshake
                    else None
                ),
                request_attach=message_attachments,
                service=[f"did:sov:{public_did.did}"],
            )

            # Add mapping for multitenant relay.
            if multitenant_mgr and wallet_id:
                await multitenant_mgr.add_key(
                    wallet_id, public_did.verkey, skip_if_exists=True
                )

        else:
            invitation_mode = (
                ConnRecord.INVITATION_MODE_MULTI
                if multi_use
                else ConnRecord.INVITATION_MODE_ONCE
            )

            if not my_endpoint:
                my_endpoint = self._session.settings.get("default_endpoint")

            # Create and store new invitation key
            connection_key = await wallet.create_signing_key()

            # Add mapping for multitenant relay
            if multitenant_mgr and wallet_id:
                await multitenant_mgr.add_key(wallet_id, connection_key.verkey)

            # Create connection invitation message
            # Note: Need to split this into two stages to support inbound routing
            # of invitations
            # Would want to reuse create_did_document and convert the result
            invi_msg = InvitationMessage(
                label=my_label or self._session.settings.get("default_label"),
                handshake_protocols=(
                    [DIDCommPrefix.qualify_current(DIDX_INVITATION)]
                    if include_handshake
                    else None
                ),
                request_attach=message_attachments,
                service=[
                    ServiceMessage(
                        _id="#inline",
                        _type="did-communication",
                        recipient_keys=[naked_to_did_key(connection_key.verkey)],
                        service_endpoint=my_endpoint,
                    )
                ],
            )

            # Create connection record
            conn_rec = ConnRecord(
                invitation_key=connection_key.verkey,
                invitation_msg_id=invi_msg._id,
                their_role=ConnRecord.Role.REQUESTER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                accept=ConnRecord.ACCEPT_AUTO if accept else ConnRecord.ACCEPT_MANUAL,
                invitation_mode=invitation_mode,
                alias=alias,
            )

            await conn_rec.save(self._session, reason="Created new invitation")
            await conn_rec.attach_invitation(self._session, invi_msg)

            if metadata:
                for key, value in metadata.items():
                    await conn_rec.metadata_set(self._session, key, value)

        # Create invitation record
        invi_rec = InvitationRecord(
            state=InvitationRecord.STATE_INITIAL,
            invi_msg_id=invi_msg._id,
            invitation=invi_msg.serialize(),
            auto_accept=accept,
            multi_use=multi_use,
        )
        await invi_rec.save(self._session, reason="Created new invitation")
        return invi_rec

    async def receive_invitation(
        self,
        invi_msg: InvitationMessage,
        auto_accept: bool = None,
        alias: str = None,
    ) -> ConnRecord:
        """Receive an out of band invitation message."""

        ledger: BaseLedger = self._session.inject(BaseLedger)

        # There must be exactly 1 service entry
        if len(invi_msg.service_blocks) + len(invi_msg.service_dids) != 1:
            raise OutOfBandManagerError("service array must have exactly one element")

        if (len(invi_msg.request_attach) < 1 and
                len(invi_msg.handshake_protocols) < 1):
            raise OutOfBandManagerError("Either handshake_protocols or request_attach \
                or both needs to be specified")
        # Get the single service item
        if len(invi_msg.service_blocks) >= 1:
            service = invi_msg.service_blocks[0]
            public_did = None
        else:
            # If it's in the did format, we need to convert to a full service block
            # An existing connection can only be reused based on a public DID 
            # in an out-of-band message.
            # https://github.com/hyperledger/aries-rfcs/tree/master/features/0434-outofband
            service_did = invi_msg.service_dids[0]
            async with ledger:
                verkey = await ledger.get_key_for_did(service_did)
                did_key = naked_to_did_key(verkey)
                endpoint = await ledger.get_endpoint_for_did(service_did)
            public_did = service_did.split(":")[2]
            service = ServiceMessage.deserialize(
                {
                    "id": "#inline",
                    "type": "did-communication",
                    "recipientKeys": [did_key],
                    "routingKeys": [],
                    "serviceEndpoint": endpoint,
                }
            )

        unq_handshake_protos = list(
            dict.fromkeys(
                [DIDCommPrefix.unqualify(proto) for proto in invi_msg.handshake_protocols]
            )
        )
        # Reuse Connection
        # Only if started by an invitee with Public DID
        conn_rec = None
        if public_did is not None:
            # Inviter has a public DID
            # Looking for an existing connection
            tag_filter = {}
            post_filter = {}
            post_filter["state"] = "active"
            post_filter["their_public_did"] = public_did
            conn_rec = await self.find_existing_connection(
                tag_filter=tag_filter,
                post_filter=post_filter
            )
        if conn_rec is not None:
            num_included_protocols = len(unq_handshake_protos)
            num_included_req_attachments = len(invi_msg.request_attach)
            if num_included_protocols >= 1 and num_included_req_attachments == 0:
                handshake_reuse_msg = await self.create_handshake_reuse_message(
                    invi_msg=invi_msg,
                    service=service,
                    connection=conn_rec,
                )
                try:
                    await asyncio.wait_for(
                        self.check_reuse_msg_state(handshake_reuse_msg._id),
                        30
                    )
                except asyncio.TimeoutError:
                    # If no reuse_accepted or problem_report message was recieved within
                    # the 30s timeout then a new connection to be created
                    conn_rec = None
            # The following cases requires a new connection to be created according to RFC
            elif not ((num_included_protocols == 0 and num_included_req_attachments >= 1) or
                      (num_included_protocols >= 1 and num_included_req_attachments >= 1)):
                conn_rec = None
        if conn_rec is None:
            # Create a new connection
            for proto in unq_handshake_protos:
                if proto == DIDX_INVITATION:
                    # Transform back to 'naked' verkey
                    service.recipient_keys = [
                        did_key_to_naked(key) for key in service.recipient_keys or []
                    ]
                    service.routing_keys = [
                        did_key_to_naked(key) for key in service.routing_keys
                    ] or []
                    didx_mgr = DIDXManager(self._session)
                    conn_rec = await didx_mgr.receive_invitation(
                        invitation=invi_msg,
                        their_public_did=public_did,
                        auto_accept=True,
                    )
                elif proto == CONNECTION_INVITATION:
                    service.recipient_keys = [
                        did_key_to_naked(key) for key in service.recipient_keys or []
                    ]
                    service.routing_keys = [
                        did_key_to_naked(key) for key in service.routing_keys
                    ] or []
                    connection_invitation = ConnectionInvitation.deserialize(
                        {
                            "@id": invi_msg._id,
                            "@type": DIDCommPrefix.qualify_current(CONNECTION_INVITATION),
                            "label": invi_msg.label,
                            "recipientKeys": service.recipient_keys,
                            "serviceEndpoint": service.service_endpoint,
                            "routingKeys": service.routing_keys,
                        }
                    )
                    conn_mgr = ConnectionManager(self._session)
                    conn_rec = await conn_mgr.receive_invitation(
                            invitation=connection_invitation,
                            their_public_did=public_did,
                            auto_accept=True,
                    )
                if conn_rec is not None:
                    break

        # Request Attach
        if len(invi_msg.request_attach) > 1:
            raise OutOfBandManagerError("More than 1 request~attach included.")
        elif len(invi_msg.request_attach) == 1:
            req_attach = invi_msg.request_attach[0]
            req_attach_type = req_attach.data.json["@type"]
            if DIDCommPrefix.unqualify(req_attach_type) == PRESENTATION_REQUEST:
                proof_present_mgr = PresentationManager(self._session)
                presentation_exchange_record = V10PresentationExchange(
                    connection_id=conn_rec.connection_id,
                    initiator=V10PresentationExchange.INITIATOR_EXTERNAL,
                    role=V10PresentationExchange.ROLE_PROVER,
                    presentation_request_dict=req_attach.data.json.serialize(),
                )
                presentation_exchange_record = await proof_present_mgr.receive_request(
                    presentation_exchange_record=presentation_exchange_record
                )

        return conn_rec

    async def find_existing_connection(
        self,
        tag_filter: dict,
        post_filter: dict,
    ) -> Optional[ConnRecord]:
        conn_records = await ConnRecord.query(
            self._session,
            tag_filter,
            post_filter_positive=post_filter,
        )
        if len(conn_records) == 0:
            conn_rec = None
        else:
            conn_rec = conn_records[0]
        return conn_rec

    async def find_reuse_msg_record(
        self,
        reuse_msg_id: str,
        session: ProfileSession,
    ) -> ConnReuseMessageRecord:
        reuse_msg_record = await ConnReuseMessageRecord.retrieve_by_id(
            session,
            reuse_msg_id,
        )
        return reuse_msg_record

    async def check_reuse_msg_state(
        self,
        reuse_msg_id: str,
    ):
        recieved = False
        while not recieved:
            reuse_msg_record = await self.find_reuse_msg_record(
                reuse_msg_id=reuse_msg_id,
                session=self._session
            )
            if not reuse_msg_record.state == ConnReuseMessageRecord.STATE_INITIAL:
                recieved = True
        return

    async def create_handshake_reuse_message(
        self,
        invi_msg: InvitationMessage,
        service: ServiceMessage,
        conn_record: ConnRecord,
    ) -> HandshakeReuse:
        """
        Create and Send a Handshake Reuse message under RFC 0434.

        Args:
            invi_msg: OOB Invitation Message
            service: Service block extracted from the OOB invitation

        Returns:

        Raises:
            OutOfBandManagerError: If there is an issue creating or
            sending the OOB invitation
        """
        try:
            # ID of Out-of-Band invitation to use as a pthid
            pthid = invi_msg._decorators._id
            reuse_msg = HandshakeReuse()
            thid = reuse_msg._id
            reuse_msg.assign_thread_id(thid=thid, pthid=pthid)
            connection_targets = self.fetch_connection_targets(connection=conn_record)
            responder = self._session.inject(BaseResponder, required=False)
            if responder:
                await responder.send(
                   message=reuse_msg,
                   target_list=connection_targets,
                )

            reuse_msg_record = ConnReuseMessageRecord(
                state=ConnReuseMessageRecord.STATE_INITIAL,
                invi_msg_id=invi_msg._decorators._id,
                conn_rec_id=conn_record._id,
                conn_reuse_msg_id=reuse_msg._id
            )
            await reuse_msg_record.save(self._session, reason="Created new reuse message record")
            return reuse_msg
        except Exception as err:
            raise OutOfBandManagerError(f"Error on creating and sending a handshake reuse message: {err}")

    async def receive_reuse_message(
        self,
        reuse_msg: HandshakeReuse,
        reciept: MessageReceipt,
    ):
        """
        Recieve and process a HandshakeReuse message under RFC 0434.

        Process a `HandshakeReuse` message by looking up
        the connection records using the MessageReciept sender DID.

        Args:
            reuse_msg: The `HandshakeReuse` to process
            receipt: The message receipt

        Returns:

        Raises:
            OutOfBandManagerError: If the existing connection is not active
            or the connection does not exists
        """
        try:
            invi_msg_id = reuse_msg._thread.pthid
            reuse_msg_id = reuse_msg._thread.thid
            tag_filter = {}
            post_filter = {}
            post_filter["state"] = "active"
            tag_filter["their_did"] = reciept.sender_did
            conn_record = await self.find_existing_connection(
                tag_filter=tag_filter,
                post_filter=post_filter
            )
            if conn_record is not None:
                reuse_accept_msg = HandshakeReuseAccept()
                reuse_accept_msg.assign_thread_id(thid=reuse_msg_id, pthid=invi_msg_id)
                connection_targets = self.fetch_connection_targets(connection=conn_record)
                responder = self._session.inject(BaseResponder, required=False)
                if responder:
                    await responder.send(
                        message=reuse_accept_msg,
                        target_list=connection_targets,
                    )
            else:
                raise OutOfBandManagerError(
                    (
                        f"No active connection found for OOB Invitee {reciept.sender_did}"
                    ),
                    error_code=ProblemReportReason.EXISTING_CONNECTION_NOT_ACTIVE,
                    originating_invi_msg_id=invi_msg_id,
                    originating_reuse_msg_id=reuse_msg_id,
                )
        except StorageNotFoundError:
            raise OutOfBandManagerError(
                (
                    f"No existing ConnRecord found for OOB Invitee {reciept.sender_did}"
                ),
                error_code=ProblemReportReason.EXISTING_CONNECTION_DOES_NOT_EXISTS,
                originating_invi_msg_id=invi_msg_id,
                originating_reuse_msg_id=reuse_msg_id,
            )

    async def receive_reuse_accepted_message(
        self,
        reuse_accepted_msg: HandshakeReuseAccept,
        reciept: MessageReceipt,
    ):
        """
        Recieve and process a HandshakeReuseAccept message under RFC 0434.

        Process a `HandshakeReuseAccept` message by updating the state of
        ConnReuseMessageRecord to STATE_ACCEPTED.

        Args:
            reuse_accepted_msg: The `HandshakeReuseAccept` to process
            receipt: The message receipt

        Returns:

        Raises:
            OutOfBandManagerError: if there is an error in processing the
            HandshakeReuseAccept message
        """
        try:
            invi_msg_id = reuse_accepted_msg._thread.pthid
            reuse_msg_id = reuse_accepted_msg._thread.thid
            reuse_msg_record = await self.find_reuse_msg_record(
                session=self._session,
                reuse_msg_id=reuse_msg_id,
            )
            assert invi_msg_id == reuse_msg_record.invi_msg_id
            reuse_msg_record.state = ConnReuseMessageRecord.STATE_ACCEPTED
            await reuse_msg_record.save(self._session, reason="Reuse message accepted by Inviter")
        except StorageNotFoundError as e:
            raise OutOfBandManagerError(
                (
                    f"Error processing reuse accepted message for OOB invitation {invi_msg_id}, {e}"
                )            
            )

    async def receive_problem_report(
        self,
        problem_report: ProblemReport,
        reciept: MessageReceipt,
    ):
        """
        Recieve and process a ProblemReport message from the inviter to invitee.

        Process a `ProblemReport` message by updating the state of
        ConnReuseMessageRecord to STATE_NOT_ACCEPTED.

        Args:
            problem_report: The `ProblemReport` to process
            receipt: The message receipt

        Returns:

        Raises:
            OutOfBandManagerError: if there is an error in processing the
            HandshakeReuseAccept message
        """
        try:
            invi_msg_id = problem_report._thread.pthid
            reuse_msg_id = problem_report._thread.thid
            reuse_msg_record = self.find_reuse_msg_record(
                session=self._session,
                reuse_msg_id=reuse_msg_id,
            )
            assert invi_msg_id == reuse_msg_record.invi_msg_id
            reuse_msg_record.state = ConnReuseMessageRecord.STATE_NOT_ACCEPTED
            await reuse_msg_record.save(self._session, reason="Recieved problem report message from inviter")
        except StorageNotFoundError:
            raise OutOfBandManagerError(
                (
                    f"Error processing problem report message for OOB invitation {invi_msg_id}"
                ) 
            )