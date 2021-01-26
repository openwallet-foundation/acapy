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
from ...present_proof.v1_0.message_types import PRESENTATION_REQUEST
from ...present_proof.v1_0.models.presentation_exchange import V10PresentationExchange

from .messages.invitation import InvitationMessage
from .messages.reuse import HandshakeReuse
from .messages.reuse_accept import HandshakeReuseAccept
from .messages.problem_report import ProblemReportReason, ProblemReport
from ...connections.v1_0.base_manager import BaseConnectionManager
from ....transport.inbound.receipt import MessageReceipt
from ....storage.error import StorageNotFoundError

from .messages.service import Service as ServiceMessage
from .models.invitation import InvitationRecord

from ...connections.v1_0.manager import ConnectionManager
from ...present_proof.v1_0.manager import PresentationManager

from ...connections.v1_0.messages.connection_invitation import ConnectionInvitation
from ....ledger.base import BaseLedger
from ....wallet.util import did_key_to_naked
from ....messaging.responder import BaseResponder
from ...present_proof.v1_0.messages.presentation_proposal import PresentationProposal
from ...present_proof.v1_0.util.indy import indy_proof_req_preview2indy_requested_creds
from ....indy.holder import IndyHolder


DIDX_INVITATION = "didexchange/1.0"
CONNECTION_INVITATION = "connections/1.0"


class OutOfBandManagerError(BaseError):
    """Out of band error."""


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
        super().__init__(self._session)

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

            # if a_type == "credential-offer":
            #     cred_ex_rec = await V10CredentialExchange.retrieve_by_id(
            #         self._session,
            #         a_id,
            #     )
            #     message_attachments.append(
            #         InvitationMessage.wrap_message(cred_ex_rec.credential_offer_dict)
            #     )
            if a_type == "present-proof":
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
        use_existing_connection: bool = True,
        auto_accept: bool = None,
        alias: str = None,
    ) -> dict:
        """Receive an out of band invitation message."""

        ledger: BaseLedger = self._session.inject(BaseLedger)

        # There must be exactly 1 service entry
        if len(invi_msg.service_blocks) + len(invi_msg.service_dids) != 1:
            raise OutOfBandManagerError("service array must have exactly one element")

        if len(invi_msg.request_attach) < 1 and len(invi_msg.handshake_protocols) < 1:
            raise OutOfBandManagerError(
                "Either handshake_protocols or request_attach \
                or both needs to be specified"
            )
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
            if "did:" in service_did and len(service_did.split(":")) == 3:
                public_did = service_did.split(":")[2]
            else:
                public_did = service_did
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
                [
                    DIDCommPrefix.unqualify(proto)
                    for proto in invi_msg.handshake_protocols
                ]
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
                tag_filter=tag_filter, post_filter=post_filter
            )
        if conn_rec is not None:
            num_included_protocols = len(unq_handshake_protos)
            num_included_req_attachments = len(invi_msg.request_attach)
            # Handshake_Protocol included Request_Attachment
            # not included Use_Existing_Connection Yes
            if (
                num_included_protocols >= 1
                and num_included_req_attachments == 0
                and use_existing_connection
            ):
                await self.create_handshake_reuse_message(
                    invi_msg=invi_msg,
                    connection=conn_rec,
                )
                try:
                    await asyncio.wait_for(
                        self.check_reuse_msg_state(
                            conn_rec=conn_rec,
                        ),
                        30,
                    )
                except asyncio.TimeoutError:
                    # If no reuse_accepted or problem_report message was recieved within
                    # the 30s timeout then a new connection to be created
                    conn_rec = None
                conn_rec.metadata_delete(session=self._session, key="reuse_msg_id")
                conn_rec.metadata_delete(session=self._session, key="reuse_msg_state")
            # Inverse of the following cases
            # Handshake_Protocol not included
            # Request_Attachment included
            # Use_Existing_Connection Yes
            # Handshake_Protocol included
            # Request_Attachment included
            # Use_Existing_Connection Yes
            elif not (
                (
                    num_included_protocols == 0
                    and num_included_req_attachments >= 1
                    and use_existing_connection
                )
                or (
                    num_included_protocols >= 1
                    and num_included_req_attachments >= 1
                    and use_existing_connection
                )
            ):
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
                            "@type": DIDCommPrefix.qualify_current(
                                CONNECTION_INVITATION
                            ),
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
        if len(invi_msg.request_attach) >= 1 and conn_rec is not None:
            req_attach = invi_msg.request_attach[0]
            if "data" in req_attach:
                req_attach_type = req_attach.data.json["@type"]
                if DIDCommPrefix.unqualify(req_attach_type) == PRESENTATION_REQUEST:
                    proof_present_mgr = PresentationManager(self._session)
                    indy_proof_request = req_attach.data.json[
                        "request_presentations~attach"
                    ][0].indy_dict
                    present_request_msg = req_attach.data.json
                    service_deco = {}
                    oob_invi_service = service.serialize()
                    service_deco["recipientKeys"] = oob_invi_service.get(
                        "recipientKeys"
                    )
                    service_deco["routingKeys"] = oob_invi_service.get("routingKeys")
                    service_deco["serviceEndpoint"] = oob_invi_service.get(
                        "serviceEndpoint"
                    )
                    present_request_msg["~service"] = service_deco
                    presentation_exchange_record = V10PresentationExchange(
                        connection_id=conn_rec.connection_id,
                        thread_id=invi_msg._id,
                        initiator=V10PresentationExchange.INITIATOR_EXTERNAL,
                        role=V10PresentationExchange.ROLE_PROVER,
                        presentation_request=indy_proof_request,
                        presentation_request_dict=present_request_msg,
                        auto_present=self._session.context.settings.get(
                            "debug.auto_respond_presentation_request"
                        ),
                        trace=(invi_msg._trace is not None),
                    )

                    presentation_exchange_record.presentation_request = (
                        indy_proof_request
                    )
                    presentation_exchange_record = (
                        await proof_present_mgr.receive_request(
                            presentation_exchange_record
                        )
                    )

                    if presentation_exchange_record.auto_present:
                        presentation_preview = None
                        if presentation_exchange_record.presentation_proposal_dict:
                            exchange_pres_proposal = PresentationProposal.deserialize(
                                presentation_exchange_record.presentation_proposal_dict
                            )
                            presentation_preview = (
                                exchange_pres_proposal.presentation_proposal
                            )

                        try:
                            req_creds = (
                                await indy_proof_req_preview2indy_requested_creds(
                                    indy_proof_request,
                                    presentation_preview,
                                    holder=self._session.inject(IndyHolder),
                                )
                            )
                        except ValueError as err:
                            self._logger.warning(f"{err}")
                            return

                        (
                            presentation_exchange_record,
                            presentation_message,
                        ) = await proof_present_mgr.create_presentation(
                            presentation_exchange_record=presentation_exchange_record,
                            requested_credentials=req_creds,
                            comment="auto-presented for proof request nonce={}".format(
                                indy_proof_request["nonce"]
                            ),
                        )
                    responder = self._session.inject(BaseResponder, required=False)
                    connection_targets = self.fetch_connection_targets(
                        connection=conn_rec
                    )
                    if responder:
                        await responder.send(
                            message=presentation_message,
                            target_list=connection_targets,
                        )
                    return presentation_message.serialize()
                else:
                    raise OutOfBandManagerError(
                        "Unsupported request~attach type, \
                            only request-presentation is supported"
                    )
            else:
                raise OutOfBandManagerError(
                    "request~attach is not properly formatted as data is missing"
                )
        else:
            return conn_rec.serialize()

    async def find_existing_connection(
        self,
        tag_filter: dict,
        post_filter: dict,
    ) -> Optional[ConnRecord]:
        """
        Find existing ConnRecord.

        Args:
            tag_filter: The filter dictionary to apply
            post_filter: Additional value filters to apply matching positively,
                with sequence values specifying alternatives to match (hit any)

        Returns:
            ConnRecord or None

        """
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

    async def check_reuse_msg_state(
        self,
        conn_rec: ConnRecord,
    ):
        """
        Check reuse message state from the ConnRecord Metadata.

        Args:
            conn_rec: The required ConnRecord with updated metadata

        Returns:

        """
        recieved = False
        while not recieved:
            if not conn_rec.metadata_get(self._session, "reuse_msg_state") == "initial":
                recieved = True
        return

    async def create_handshake_reuse_message(
        self,
        invi_msg: InvitationMessage,
        conn_record: ConnRecord,
    ):
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
                conn_record.metadata_set(
                    session=self._session, key="reuse_msg_id", value=reuse_msg._id
                )
                conn_record.metadata_set(
                    session=self._session, key="reuse_msg_state", value="initial"
                )
        except Exception as err:
            raise OutOfBandManagerError(
                f"Error on creating and sending a handshake reuse message: {err}"
            )

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
                tag_filter=tag_filter, post_filter=post_filter
            )
            if conn_record is not None:
                reuse_accept_msg = HandshakeReuseAccept()
                reuse_accept_msg.assign_thread_id(thid=reuse_msg_id, pthid=invi_msg_id)
                connection_targets = self.fetch_connection_targets(
                    connection=conn_record
                )
                responder = self._session.inject(BaseResponder, required=False)
                if responder:
                    await responder.send(
                        message=reuse_accept_msg,
                        target_list=connection_targets,
                    )
                # Find corresponding OOB Invitation Record
                try:
                    invi_rec = await InvitationRecord.retrieve_by_tag_filter(
                        self._session,
                        tag_filter={"invi_msg_id": invi_msg_id},
                    )
                except StorageNotFoundError:
                    raise OutOfBandManagerError(
                        f"No record of invitation {invi_msg_id} "
                    )
                # If Invitation is single-use, then delete the ConnRecord
                # created as the existing connection will be used.
                if not invi_rec.multi_use:
                    invi_id_post_filter = {}
                    invi_id_post_filter["invitation_msg_id"] = invi_msg_id
                    conn_record_to_delete = self.find_existing_connection(
                        tag_filter={},
                        post_filter=invi_id_post_filter,
                    )
                    if conn_record.connection_id != conn_record_to_delete.connection_id:
                        conn_record_to_delete.delete_record(session=self._session)
            else:
                targets = None
                if reuse_msg.did_doc_attach:
                    try:
                        targets = self.diddoc_connection_targets(
                            reuse_msg.did_doc_attach,
                            reciept.recipient_verkey,
                        )
                    except OutOfBandManagerError:
                        self._logger.exception(
                            "Error parsing DIDDoc for problem report"
                        )
                problem_report = ProblemReport(
                    problem_code=ProblemReportReason.EXISTING_CONNECTION_NOT_ACTIVE,
                    explain=f"No active connection found for Invitee {reciept.sender_did}",
                )
                problem_report.assign_thread_id(thid=invi_msg_id, pthid=reuse_msg_id)
                await responder.send_reply(
                    problem_report,
                    target_list=targets,
                )
        except StorageNotFoundError:
            targets = None
            if reuse_msg.did_doc_attach:
                try:
                    targets = self.diddoc_connection_targets(
                        reuse_msg.did_doc_attach,
                        reciept.recipient_verkey,
                    )
                except OutOfBandManagerError:
                    self._logger.exception("Error parsing DIDDoc for problem report")
            problem_report = ProblemReport(
                problem_code=ProblemReportReason.EXISTING_CONNECTION_DOES_NOT_EXISTS,
                explain=f"No existing connection for Invitee {reciept.sender_did}",
            )
            problem_report.assign_thread_id(thid=invi_msg_id, pthid=reuse_msg_id)
            await responder.send_reply(
                problem_report,
                target_list=targets,
            )
        except Exception as e:
            raise OutOfBandManagerError(
                (f"No existing ConnRecord found for OOB Invitee, {e}"),
            )

    async def receive_reuse_accepted_message(
        self,
        reuse_accepted_msg: HandshakeReuseAccept,
        reciept: MessageReceipt,
        conn_record: ConnRecord,
    ):
        """
        Recieve and process a HandshakeReuseAccept message under RFC 0434.

        Process a `HandshakeReuseAccept` message by updating the ConnRecord metadata
        state to `accepted`.

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
            thread_reuse_msg_id = reuse_accepted_msg._thread.thid
            conn_reuse_msg_id = conn_record.metadata_get(
                session=self._session, key="reuse_msg_id"
            )
            assert thread_reuse_msg_id == conn_reuse_msg_id
            conn_record.metadata_set(
                session=self._session, key="reuse_msg_state", value="accepted"
            )
        except StorageNotFoundError as e:
            raise OutOfBandManagerError(
                (
                    f"Error processing reuse accepted message \
                        for OOB invitation {invi_msg_id}, {e}"
                )
            )

    async def receive_problem_report(
        self,
        problem_report: ProblemReport,
        reciept: MessageReceipt,
        conn_record: ConnRecord,
    ):
        """
        Recieve and process a ProblemReport message from the inviter to invitee.

        Process a `ProblemReport` message by updating  the ConnRecord metadata
        state to `not_accepted`.

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
            thread_reuse_msg_id = problem_report._thread.thid
            conn_reuse_msg_id = conn_record.metadata_get(
                session=self._session, key="reuse_msg_id"
            )
            assert thread_reuse_msg_id == conn_reuse_msg_id
            conn_record.metadata_set(
                session=self._session, key="reuse_msg_state", value="not_accepted"
            )
        except StorageNotFoundError:
            raise OutOfBandManagerError(
                (
                    f"Error processing problem report message \
                        for OOB invitation {invi_msg_id}"
                )
            )
