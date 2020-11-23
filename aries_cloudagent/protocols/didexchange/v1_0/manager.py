"""Classes to manage connection establishment under RFC 23 (DID exchange)."""

import json
import logging

from typing import Coroutine, Sequence, Tuple

from ....cache.base import BaseCache
from ....connections.models.conn_record import ConnRecord
from ....connections.models.connection_target import ConnectionTarget
from ....connections.models.diddoc import (
    DIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from ....config.base import InjectorError
from ....config.injection_context import InjectionContext
from ....core.error import BaseError
from ....ledger.base import BaseLedger
from ....messaging.decorators.attach_decorator import AttachDecorator
from ....messaging.responder import BaseResponder
from ....storage.base import BaseStorage
from ....storage.error import StorageError, StorageNotFoundError
from ....storage.record import StorageRecord
from ....transport.inbound.receipt import MessageReceipt
from ....wallet.base import BaseWallet, DIDInfo
from ....wallet.crypto import create_keypair, seed_to_did
from ....wallet.error import WalletNotFoundError
from ....wallet.util import bytes_to_b58

from ...out_of_band.v1_0.messages.invitation import (
    InvitationMessage as OOBInvitationMessage,
)
from ...routing.v1_0.manager import RoutingManager

from .messages.complete import DIDXComplete
from .messages.request import DIDXRequest
from .messages.response import DIDXResponse
from .messages.problem_report import ProblemReportReason


class DIDXManagerError(BaseError):
    """Connection error."""


class DIDXManager:
    """Class for managing connections under RFC 23 (DID exchange)."""

    RECORD_TYPE_DID_DOC = "did_doc"
    RECORD_TYPE_DID_KEY = "did_key"

    def __init__(self, context: InjectionContext):
        """
        Initialize a DIDXManager.

        Args:
            context: The context for this connection manager
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    @property
    def context(self) -> InjectionContext:
        """
        Accessor for the current injection context.

        Returns:
            The injection context for this connection manager

        """
        return self._context

    '''
    async def create_invitation(
        self,
        my_label: str = None,
        my_endpoint: str = None,
        auto_accept: bool = None,
        public: bool = False,
        multi_use: bool = False,
        alias: str = None,
        include_handshake: bool = False,
        attachments: Sequence[Mapping] = None,
    ) -> Tuple[ConnRecord, OOBInvitationMessage]:
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
            A tuple of the new `ConnRecord` and invitation instance

        """
        if not my_label:
            my_label = self.context.settings.get("default_label")
        wallet: BaseWallet = await self.context.inject(BaseWallet)

        message_attachments = []
        for atch in attachments or []:
            a_type = atch.get("type")
            a_id = atch.get("id")

            if a_type == "credential-offer":
                cred_ex_rec = await V10CredentialExchange.retrieve_by_id(
                    self.context,
                    a_id,
                )
                message_attachments.append(
                    OOBInvitationMessage.wrap_message(cred_ex_rec.credential_offer_dict)
                )
            elif a_type == "present-proof":
                pres_ex_rec = await V10PresentationExchange.retrieve_by_id(
                    self.context,
                    a_id,
                )
                message_attachments.append(
                    OOBInvitationMessage.wrap_message(
                        pres_ex_rec.presentation_request_dict
                    )
                )
            else:
                raise DIDXManagerError(f"Unknown attachment type: {a_type}")

        if public:
            if not self.context.settings.get("public_invites"):
                raise DIDXManagerError("Public invitations are not enabled")

            public_did = await wallet.get_public_did()
            if not public_did:
                raise DIDXManagerError(
                    "Cannot create public invitation with no public DID"
                )

            if multi_use:
                raise DIDXManagerError(
                    "Cannot use public and multi_use at the same time"
                )

            invitation = OOBInvitationMessage(
                label=my_label,
                handshake_protocols=(
                    [DIDCommPrefix.qualify_current(OOB_INVITATION)]
                    if include_handshake
                    else None
                ),
                request_attach=message_attachments,
                service=[f"did:sov:{public_did.did}"],
            )

            return (None, invitation)

        invitation_mode = (
            ConnRecord.INVITATION_MODE_MULTI
            if multi_use
            else ConnRecord.INVITATION_MODE_ONCE
        )

        if not my_endpoint:
            my_endpoint = self.context.settings.get("default_endpoint")
        accept = (
            ConnRecord.ACCEPT_AUTO
            if (
                auto_accept
                or (
                    auto_accept is None
                    and self.context.settings.get("debug.auto_accept_requests")
                )
            )
            else ConnRecord.ACCEPT_MANUAL
        )

        # Create and store new invitation key
        connection_key = await wallet.create_signing_key()

        # Create connection invitation message
        # Note: Need to split this into two stages to support inbound routing of invites
        # Would want to reuse create_did_document and convert the result
        invitation = OOBInvitationMessage(
            label=my_label,
            handshake_protocols=(
                [DIDCommPrefix.qualify_current("didexchange/1.0/invitation")]
                if include_handshake
                else None
            ),
            request_attach=message_attachments,
            service=[
                OOBService(
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
            their_role=ConnRecord.Role.REQUESTER.rfc23,
            state=ConnRecord.State.INVITATION.rfc23,
            accept=accept,
            invitation_mode=invitation_mode,
            alias=alias,
        )

        await conn_rec.save(self.context, reason="Created new invitation")
        await conn_rec.attach_invitation(self.context, invitation)

        return (conn_rec, invitation)
    '''

    async def receive_invitation(
        self,
        invitation: OOBInvitationMessage,
        auto_accept: bool = None,
        alias: str = None,
    ) -> ConnRecord:
        """
        Create a new connection record to track a received invitation.

        Args:
            invitation: The invitation to store
            auto_accept: set to auto-accept the invitation (None to use config)
            alias: optional alias to set on the record

        Returns:
            The new `ConnRecord` instance

        """
        if not invitation.service_dids:
            if invitation.service_blocks:
                if not all(
                    s.recipient_keys and s.service_endpoint
                    for s in invitation.service_blocks
                ):
                    raise DIDXManagerError(
                        "All service blocks in invitation with no service DIDs "
                        "must contain recipient key(s) and service endpoint(s)"
                    )
            else:
                raise DIDXManagerError(
                    "Invitation must contain service blocks or service DIDs"
                )

        accept = (
            ConnRecord.ACCEPT_AUTO
            if (
                auto_accept
                or (
                    auto_accept is None
                    and self.context.settings.get("debug.auto_accept_invites")
                )
            )
            else ConnRecord.ACCEPT_MANUAL
        )

        # Create connection record
        conn_rec = ConnRecord(
            invitation_key=(
                invitation.service_blocks[0].recipient_keys[0]
                if invitation.service_blocks
                else None
            ),
            their_label=invitation.label,
            their_role=ConnRecord.Role.RESPONDER.rfc23,
            state=ConnRecord.State.INVITATION.rfc23,
            accept=accept,
            alias=alias,
        )

        await conn_rec.save(
            self.context,
            reason="Created new connection record from invitation",
            log_params={
                "invitation": invitation,
                "their_role": ConnRecord.Role.RESPONDER.rfc23,
            },
        )

        # Save the invitation for later processing
        await conn_rec.attach_invitation(self.context, invitation)

        if conn_rec.accept == ConnRecord.ACCEPT_AUTO:
            request = await self.create_request(conn_rec)
            responder: BaseResponder = await self._context.inject(
                BaseResponder, required=False
            )
            if responder:
                await responder.send_reply(
                    request,
                    connection_id=conn_rec.connection_id,
                )

                conn_rec.state = ConnRecord.State.REQUEST.rfc23
                await conn_rec.save(self.context, reason="Sent connection request")
        else:
            self._logger.debug("Connection invitation will await acceptance")

        return conn_rec

    async def create_request(
        self,
        conn_rec: ConnRecord,
        my_label: str = None,
        my_endpoint: str = None,
    ) -> DIDXRequest:
        """
        Create a new connection request for a previously-received invitation.

        Args:
            conn_rec: The `ConnRecord` representing the invitation to accept
            my_label: My label
            my_endpoint: My endpoint

        Returns:
            A new `DIDXRequest` message to send to the other agent

        """
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        if conn_rec.my_did:
            my_info = await wallet.get_local_did(conn_rec.my_did)
        else:
            # Create new DID for connection
            my_info = await wallet.create_local_did()
            conn_rec.my_did = my_info.did

        # Create connection request message
        if my_endpoint:
            my_endpoints = [my_endpoint]
        else:
            my_endpoints = []
            default_endpoint = self.context.settings.get("default_endpoint")
            if default_endpoint:
                my_endpoints.append(default_endpoint)
            my_endpoints.extend(self.context.settings.get("additional_endpoints", []))
        did_doc = await self.create_did_document(
            my_info, conn_rec.inbound_connection_id, my_endpoints
        )
        pthid = did_doc.service[[s for s in did_doc.service][0]].id
        attach = AttachDecorator.from_indy_dict(did_doc.serialize())
        await attach.data.sign(my_info.verkey, wallet)
        if not my_label:
            my_label = self.context.settings.get("default_label")
        request = DIDXRequest(
            label=my_label,
            did=conn_rec.my_did,
            did_doc_attach=attach,
        )
        request.assign_thread_id(thid=request._id, pthid=pthid)

        # Update connection state
        conn_rec.request_id = request._id
        conn_rec.state = ConnRecord.State.REQUEST.rfc23
        await conn_rec.save(self.context, reason="Created connection request")

        return request

    async def receive_request(
        self, request: DIDXRequest, receipt: MessageReceipt
    ) -> ConnRecord:
        """
        Receive and store a connection request.

        Args:
            request: The `DIDXRequest` to accept
            receipt: The message receipt

        Returns:
            The new or updated `ConnRecord` instance

        """
        ConnRecord.log_state(
            self.context, "Receiving connection request", {"request": request}
        )

        conn_rec = None
        connection_key = None
        wallet: BaseWallet = await self.context.inject(BaseWallet)

        # Determine what key will need to sign the response
        if receipt.recipient_did_public:
            my_info = await wallet.get_local_did(receipt.recipient_did)
            connection_key = my_info.verkey
        else:
            connection_key = receipt.recipient_verkey
            try:
                conn_rec = await ConnRecord.retrieve_by_invitation_key(
                    context=self.context,
                    invitation_key=connection_key,
                    their_role=ConnRecord.Role.REQUESTER.rfc23,
                )
            except StorageNotFoundError:
                raise DIDXManagerError("No invitation found for pairwise connection")

        invitation = None
        if conn_rec:
            invitation = await conn_rec.retrieve_invitation(self.context)
            connection_key = conn_rec.invitation_key
            ConnRecord.log_state(
                self.context, "Found invitation", {"invitation": invitation}
            )

            if conn_rec.is_multiuse_invitation:
                wallet: BaseWallet = await self.context.inject(BaseWallet)
                my_info = await wallet.create_local_did()
                new_conn_rec = ConnRecord(
                    invitation_key=connection_key,
                    my_did=my_info.did,
                    state=ConnRecord.State.REQUEST.rfc23,
                    accept=conn_rec.accept,
                    their_role=conn_rec.their_role,
                )

                await new_conn_rec.save(
                    self.context,
                    reason="Received connection request from multi-use invitation DID",
                )
                conn_rec = new_conn_rec

        if not (request.did_doc_attach and request.did_doc_attach.data):
            raise DIDXManagerError(
                "DID Doc attachment missing or has no data: "
                "cannot connect to public DID"
            )
        if not await request.did_doc_attach.data.verify(wallet):
            raise DIDXManagerError("DID Doc signature failed verification")
        conn_did_doc = DIDDoc.from_json(request.did_doc_attach.data.signed.decode())
        if request.did != conn_did_doc.did:
            raise DIDXManagerError(
                (
                    f"Connection DID {request.did} does not match "
                    f"DID Doc id {conn_did_doc.did}"
                ),
                error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED,
            )
        await self.store_did_document(conn_did_doc)

        if conn_rec:
            conn_rec.their_label = request.label
            conn_rec.their_did = request.did
            conn_rec.state = ConnRecord.State.REQUEST.rfc23
            await conn_rec.save(
                self.context, reason="Received connection request from invitation"
            )
        elif not self.context.settings.get("public_invites"):
            raise DIDXManagerError("Public invitations are not enabled")
        else:
            my_info = await wallet.create_local_did()
            conn_rec = ConnRecord(
                invitation_key=connection_key,
                my_did=my_info.did,
                their_did=request.did,
                their_label=request.label,
                their_role=ConnRecord.Role.REQUESTER.rfc23,
                state=ConnRecord.State.REQUEST.rfc23,
            )
            if self.context.settings.get("debug.auto_accept_requests"):
                conn_rec.accept = ConnRecord.ACCEPT_AUTO

            await conn_rec.save(
                self.context, reason="Received connection request from public DID"
            )

        # Attach the connection request so it can be found and responded to
        await conn_rec.attach_request(self.context, request)

        if conn_rec.accept == ConnRecord.ACCEPT_AUTO:
            response = await self.create_response(conn_rec)
            responder: BaseResponder = await self._context.inject(
                BaseResponder, required=False
            )
            if responder:
                await responder.send_reply(
                    response, connection_id=conn_rec.connection_id
                )
                conn_rec.state = ConnRecord.State.RESPONSE.rfc23
                await conn_rec.save(self.context, reason="Sent connection response")
        else:
            self._logger.debug("DID exchange request will await acceptance")

        return conn_rec

    async def create_response(
        self,
        conn_rec: ConnRecord,
        my_endpoint: str = None,
    ) -> DIDXResponse:
        """
        Create a connection response for a received connection request.

        Args:
            conn_rec: The `ConnRecord` with a pending connection request
            my_endpoint: Current agent endpoint

        Returns:
            New `DIDXResponse` message

        """
        ConnRecord.log_state(
            self.context,
            "Creating connection response",
            {"connection_id": conn_rec.connection_id},
        )

        if ConnRecord.State.get(conn_rec.state) is not ConnRecord.State.REQUEST:
            raise DIDXManagerError(
                f"Connection not in state {ConnRecord.State.REQUEST.rfc23}"
            )

        request = await conn_rec.retrieve_request(self.context)
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        if conn_rec.my_did:
            my_info = await wallet.get_local_did(conn_rec.my_did)
        else:
            my_info = await wallet.create_local_did()
            conn_rec.my_did = my_info.did

        # Create connection response message
        if my_endpoint:
            my_endpoints = [my_endpoint]
        else:
            my_endpoints = []
            default_endpoint = self.context.settings.get("default_endpoint")
            if default_endpoint:
                my_endpoints.append(default_endpoint)
            my_endpoints.extend(self.context.settings.get("additional_endpoints", []))
        did_doc = await self.create_did_document(
            my_info, conn_rec.inbound_connection_id, my_endpoints
        )
        attach = AttachDecorator.from_indy_dict(did_doc.serialize())
        await attach.data.sign(conn_rec.invitation_key, wallet)
        response = DIDXResponse(did=my_info.did, did_doc_attach=attach)
        # Assign thread information
        response.assign_thread_from(request)
        response.assign_trace_from(request)
        """  # TODO - re-evaluate what code signs? With what key?
        # Sign connection field using the invitation key
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await response.sign_field("connection", connection.invitation_key, wallet)
        """

        # Update connection state
        conn_rec.state = ConnRecord.State.RESPONSE.rfc23
        await conn_rec.save(
            self.context,
            reason="Created connection response",
            log_params={"response": response},
        )

        return response

    async def accept_response(
        self,
        response: DIDXResponse,
        receipt: MessageReceipt,
    ) -> ConnRecord:
        """
        Accept a connection response under RFC 23 (DID exchange).

        Process a `DIDXResponse` message by looking up
        the connection request and setting up the pairwise connection.

        Args:
            response: The `DIDXResponse` to accept
            receipt: The message receipt

        Returns:
            The updated `ConnRecord` representing the connection

        Raises:
            DIDXManagerError: If there is no DID associated with the
                connection response
            DIDXManagerError: If the corresponding connection is not
                in the request-sent state

        """
        wallet: BaseWallet = await self.context.inject(BaseWallet)

        conn_rec = None
        if response._thread:
            # identify the request by the thread ID
            try:
                conn_rec = await ConnRecord.retrieve_by_request_id(
                    self.context, response._thread_id
                )
            except StorageNotFoundError:
                pass

        if not conn_rec and receipt.sender_did:
            # identify connection by the DID they used for us
            try:
                conn_rec = await ConnRecord.retrieve_by_did(
                    context=self.context,
                    their_did=receipt.sender_did,
                    my_did=receipt.recipient_did,
                    their_role=ConnRecord.Role.RESPONDER.rfc23,
                )
            except StorageNotFoundError:
                pass

        if not conn_rec:
            raise DIDXManagerError(
                "No corresponding connection request found",
                error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED,
            )

        # TODO: RFC 160 impl included STATE_RESPONSE: why?
        if ConnRecord.State.get(conn_rec.state) is not ConnRecord.State.REQUEST:
            raise DIDXManagerError(
                "Cannot accept connection response for connection"
                f" in state: {conn_rec.state}"
            )

        their_did = response.did
        if not response.did_doc_attach:
            raise DIDXManagerError("No DIDDoc attached; cannot connect to public DID")
        conn_did_doc = await self.verify_diddoc(wallet, response.did_doc_attach)
        if their_did != conn_did_doc.did:
            raise DIDXManagerError(
                f"Connection DID {their_did} "
                f"does not match DID doc id {conn_did_doc.did}"
            )
        await self.store_did_document(conn_did_doc)

        conn_rec.their_did = their_did
        conn_rec.state = ConnRecord.State.RESPONSE.rfc23
        await conn_rec.save(self.context, reason="Accepted connection response")

        # create and send connection-complete message
        complete = DIDXComplete()
        complete.assign_thread_from(response)
        responder: BaseResponder = await self._context.inject(
            BaseResponder, required=False
        )
        if responder:
            await responder.send_reply(complete, connection_id=conn_rec.connection_id)

            conn_rec.state = ConnRecord.State.RESPONSE.rfc23
            await conn_rec.save(self.context, reason="Sent connection complete")

        return conn_rec

    async def accept_complete(
        self,
        complete: DIDXComplete,
        receipt: MessageReceipt,
    ) -> ConnRecord:
        """
        Accept a connection complete message under RFC 23 (DID exchange).

        Process a `DIDXComplete` message by looking up
        the connection record and marking the exchange complete.

        Args:
            complete: The `DIDXComplete` to accept
            receipt: The message receipt

        Returns:
            The updated `ConnRecord` representing the connection

        Raises:
            DIDXManagerError: If the corresponding connection does not exist
                or is not in the response-sent state

        """
        conn_rec = None

        # identify the request by the thread ID
        try:
            conn_rec = await ConnRecord.retrieve_by_request_id(
                self.context, complete._thread_id
            )
        except StorageNotFoundError:
            raise DIDXManagerError(
                "No corresponding connection request found",
                error_code=ProblemReportReason.COMPLETE_NOT_ACCEPTED,
            )

        conn_rec.state = ConnRecord.State.COMPLETED.rfc23
        await conn_rec.save(self.context, reason="Received connection complete")

        return conn_rec

    async def create_static_connection(
        self,
        my_did: str = None,
        my_seed: str = None,
        their_did: str = None,
        their_seed: str = None,
        their_verkey: str = None,
        their_endpoint: str = None,
        their_label: str = None,
        alias: str = None,
    ) -> (DIDInfo, DIDInfo, ConnRecord):
        """
        Register a new static connection (for use by the test suite).

        Args:
            my_did: override the DID used in the connection
            my_seed: provide a seed used to generate our DID and keys
            their_did: provide the DID used by the other party
            their_seed: provide a seed used to generate their DID and keys
            their_verkey: provide the verkey used by the other party
            their_endpoint: their URL endpoint for routing messages
            alias: an alias for this connection record

        Returns:
            Tuple: my DIDInfo, their DIDInfo, new `ConnRecord` instance

        """
        wallet: BaseWallet = await self.context.inject(BaseWallet)

        # seed and DID optional
        my_info = await wallet.create_local_did(my_seed, my_did)

        # must provide their DID and verkey if the seed is not known
        if (not their_did or not their_verkey) and not their_seed:
            raise DIDXManagerError(
                "Either a verkey or seed must be provided for the other party"
            )
        if not their_did:
            their_did = seed_to_did(their_seed)
        if not their_verkey:
            their_verkey_bin, _ = create_keypair(their_seed.encode())
            their_verkey = bytes_to_b58(their_verkey_bin)
        their_info = DIDInfo(their_did, their_verkey, {})

        # Create connection record
        conn_rec = ConnRecord(
            invitation_mode=ConnRecord.INVITATION_MODE_STATIC,
            my_did=my_info.did,
            their_did=their_info.did,
            their_label=their_label,
            state=ConnRecord.State.COMPLETED.rfc160,
            alias=alias,
        )
        await conn_rec.save(self.context, reason="Created new static connection")

        # Synthesize their DID doc
        did_doc = await self.create_did_document(their_info, None, [their_endpoint])
        await self.store_did_document(did_doc)

        return my_info, their_info, conn_rec

    async def find_connection(
        self,
        their_did: str,
        my_did: str = None,
        my_verkey: str = None,
        auto_complete=False,
    ) -> ConnRecord:
        """
        Look up existing connection information for a sender verkey.

        Args:
            their_did: Their DID
            my_did: My DID
            my_verkey: My verkey
            auto_complete: Whether to promote connection automatically to completed

        Returns:
            The located `ConnRecord`, if any

        """
        conn_rec = None
        if their_did:
            try:
                conn_rec = await ConnRecord.retrieve_by_did(
                    self.context, their_did, my_did
                )
            except StorageNotFoundError:
                pass

        if (
            conn_rec
            and conn_rec.state == ConnRecord.State.RESPONSE.rfc23
            and auto_complete
        ):
            conn_rec.state = ConnRecord.State.COMPLETED.rfc23

            await conn_rec.save(self.context, reason="Connection promoted to completed")

        if not conn_rec and my_verkey:
            try:
                conn_rec = await ConnRecord.retrieve_by_invitation_key(
                    context=self.context,
                    invitation_key=my_verkey,
                    their_role=ConnRecord.Role.RESPONDER.rfc23,
                )
            except StorageError:
                self._logger.warning(
                    "No corresponding connection record found for sender verkey: %s",
                    my_verkey,
                )
                pass

        return conn_rec

    async def find_inbound_connection(self, receipt: MessageReceipt) -> ConnRecord:
        """
        Deserialize an incoming message and further populate the request context.

        Args:
            receipt: The message receipt

        Returns:
            The `ConnRecord` associated with the expanded message, if any

        """

        cache_key = None
        conn_rec = None
        resolved = False

        if receipt.sender_verkey and receipt.recipient_verkey:
            cache_key = (
                f"connection_by_verkey::{receipt.sender_verkey}"
                f"::{receipt.recipient_verkey}"
            )
            cache: BaseCache = await self.context.inject(BaseCache, required=False)
            if cache:
                async with cache.acquire(cache_key) as entry:
                    if entry.result:
                        cached = entry.result
                        receipt.sender_did = cached["sender_did"]
                        receipt.recipient_did_public = cached["recipient_did_public"]
                        receipt.recipient_did = cached["recipient_did"]
                        conn_rec = await ConnRecord.retrieve_by_id(
                            self.context, cached["id"]
                        )
                    else:
                        conn_rec = await self.resolve_inbound_connection(receipt)
                        if conn_rec:
                            cache_val = {
                                "id": conn_rec.connection_id,
                                "sender_did": receipt.sender_did,
                                "recipient_did": receipt.recipient_did,
                                "recipient_did_public": receipt.recipient_did_public,
                            }
                            await entry.set_result(cache_val, 3600)
                        resolved = True

        if not conn_rec and not resolved:
            conn_rec = await self.resolve_inbound_connection(receipt)
        return conn_rec

    async def resolve_inbound_connection(self, receipt: MessageReceipt) -> ConnRecord:
        """
        Populate the receipt DID information and find the related `ConnRecord`.

        Args:
            receipt: The message receipt

        Returns:
            The `ConnRecord` associated with the expanded message, if any

        """

        if receipt.sender_verkey:
            try:
                receipt.sender_did = await self.find_did_for_key(receipt.sender_verkey)
            except StorageNotFoundError:
                self._logger.warning(
                    "No corresponding DID found for sender verkey: %s",
                    receipt.sender_verkey,
                )

        if receipt.recipient_verkey:
            try:
                wallet: BaseWallet = await self.context.inject(BaseWallet)
                my_info = await wallet.get_local_did_for_verkey(
                    receipt.recipient_verkey
                )
                receipt.recipient_did = my_info.did
                if "public" in my_info.metadata and my_info.metadata["public"]:
                    receipt.recipient_did_public = True
            except InjectorError:
                self._logger.warning(
                    "Cannot resolve recipient verkey, no wallet defined by "
                    "context: %s",
                    receipt.recipient_verkey,
                )
            except WalletNotFoundError:
                self._logger.warning(
                    "No corresponding DID found for recipient verkey: %s",
                    receipt.recipient_verkey,
                )

        return await self.find_connection(
            receipt.sender_did, receipt.recipient_did, receipt.recipient_verkey, True
        )

    async def create_did_document(
        self,
        did_info: DIDInfo,
        inbound_connection_id: str = None,
        svc_endpoints: Sequence[str] = None,
    ) -> DIDDoc:
        """Create our DID doc for a given DID.

        Args:
            did_info: The DID information (DID and verkey) used in the connection
            inbound_connection_id: The ID of the inbound routing connection to use
            svc_endpoints: Custom endpoints for the DID Document

        Returns:
            The prepared `DIDDoc` instance

        """

        did_doc = DIDDoc(did=did_info.did)
        did_controller = did_info.did
        did_key = did_info.verkey
        pk = PublicKey(
            did_info.did,
            "1",
            did_key,
            PublicKeyType.ED25519_SIG_2018,
            did_controller,
            True,
        )
        did_doc.set(pk)

        router_id = inbound_connection_id
        routing_keys = []
        router_idx = 1
        while router_id:
            # look up routing connection information
            router = await ConnRecord.retrieve_by_id(self.context, router_id)
            if ConnRecord.State.get(router.state) is not ConnRecord.State.COMPLETED:
                raise DIDXManagerError(f"Router connection not completed: {router_id}")
            routing_doc, _ = await self.fetch_did_document(router.their_did)
            if not routing_doc.service:
                raise DIDXManagerError(
                    f"No services defined by routing DIDDoc: {router_id}"
                )
            for service in routing_doc.service.values():
                if not service.endpoint:
                    raise DIDXManagerError(
                        "Routing DIDDoc service has no service endpoint"
                    )
                if not service.recip_keys:
                    raise DIDXManagerError(
                        "Routing DIDDoc service has no recipient key(s)"
                    )
                rk = PublicKey(
                    did_info.did,
                    f"routing-{router_idx}",
                    service.recip_keys[0].value,
                    PublicKeyType.ED25519_SIG_2018,
                    did_controller,
                    True,
                )
                routing_keys.append(rk)
                svc_endpoints = [service.endpoint]
                break
            router_id = router.inbound_connection_id

        for (endpoint_index, svc_endpoint) in enumerate(svc_endpoints or []):
            endpoint_ident = "indy" if endpoint_index == 0 else f"indy{endpoint_index}"
            service = Service(
                did_info.did,
                endpoint_ident,
                "IndyAgent",
                [pk],
                routing_keys,
                svc_endpoint,
            )
            did_doc.set(service)

        return did_doc

    async def fetch_did_document(self, did: str) -> Tuple[DIDDoc, StorageRecord]:
        """Retrieve a DID Document for a given DID.

        Args:
            did: The DID for which to search
        """
        storage: BaseStorage = await self.context.inject(BaseStorage)
        record = await storage.find_record(
            DIDXManager.RECORD_TYPE_DID_DOC, {"did": did}
        )
        return (DIDDoc.from_json(record.value), record)

    async def store_did_document(self, did_doc: DIDDoc):
        """Store a DID document.

        Args:
            did_doc: The `DIDDoc` instance to persist
        """
        assert did_doc.did
        storage: BaseStorage = await self.context.inject(BaseStorage)
        try:
            stored_doc, record = await self.fetch_did_document(did_doc.did)
        except StorageNotFoundError:
            record = StorageRecord(
                DIDXManager.RECORD_TYPE_DID_DOC,
                did_doc.to_json(),
                {"did": did_doc.did},
            )
            await storage.add_record(record)
        else:
            await storage.update_record(record, did_doc.to_json(), {"did": did_doc.did})
        await self.remove_keys_for_did(did_doc.did)
        for key in did_doc.pubkey.values():
            if key.controller == did_doc.did:
                await self.add_key_for_did(did_doc.did, key.value)

    async def add_key_for_did(self, did: str, key: str):
        """Store a verkey for lookup against a DID.

        Args:
            did: The DID to associate with this key
            key: The verkey to be added
        """
        record = StorageRecord(
            DIDXManager.RECORD_TYPE_DID_KEY, key, {"did": did, "key": key}
        )
        storage: BaseStorage = await self.context.inject(BaseStorage)
        await storage.add_record(record)

    async def find_did_for_key(self, key: str) -> str:
        """Find the DID previously associated with a key.

        Args:
            key: The verkey to look up
        """
        storage: BaseStorage = await self.context.inject(BaseStorage)
        record = await storage.find_record(
            DIDXManager.RECORD_TYPE_DID_KEY, {"key": key}
        )
        return record.tags["did"]

    async def remove_keys_for_did(self, did: str):
        """Remove all keys associated with a DID.

        Args:
            did: The DID for which to remove keys
        """
        storage: BaseStorage = await self.context.inject(BaseStorage)
        keys = await storage.search_records(
            DIDXManager.RECORD_TYPE_DID_KEY, {"did": did}
        ).fetch_all()
        for record in keys:
            await storage.delete_record(record)

    async def get_connection_targets(
        self,
        *,
        connection_id: str = None,
        conn_rec: ConnRecord = None,
    ):
        """Create a connection target from a `ConnRecord`.

        Args:
            connection_id: The connection ID to search for
            conn_rec: The connection record itself, if already available
        """
        if not connection_id:
            connection_id = conn_rec.connection_id
        cache: BaseCache = await self.context.inject(BaseCache, required=False)
        cache_key = f"connection_target::{connection_id}"
        if cache:
            async with cache.acquire(cache_key) as entry:
                if entry.result:
                    targets = [
                        ConnectionTarget.deserialize(row) for row in entry.result
                    ]
                else:
                    if not conn_rec:
                        conn_rec = await ConnRecord.retrieve_by_id(
                            self.context, connection_id
                        )
                    targets = await self.fetch_connection_targets(conn_rec)
                    await entry.set_result([row.serialize() for row in targets], 3600)
        else:
            targets = await self.fetch_connection_targets(conn_rec)
        return targets

    async def fetch_connection_targets(
        self,
        conn_rec: ConnRecord,
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets from a `ConnRecord`.

        Args:
            conn_rec: The connection record (with associated `DIDDoc`)
                used to generate the connection target
        """

        if not conn_rec.my_did:
            self._logger.debug("No local DID associated with connection")
            return None

        wallet: BaseWallet = await self.context.inject(BaseWallet)
        my_info = await wallet.get_local_did(conn_rec.my_did)
        results = None

        """ was (for RFC 160)
            # KEEP THIS COMMENT AROUND until certain the logic maps OK to RFC 23
        if (
            connection.state
            in (ConnectionRecord.STATE_INVITATION, ConnectionRecord.STATE_REQUEST)
            and connection.initiator == ConnectionRecord.INITIATOR_EXTERNAL
        ):
        """
        if (
            ConnRecord.State.get(conn_rec.state)
            in (ConnRecord.State.INVITATION, ConnRecord.State.REQUEST)
            and ConnRecord.Role.get(conn_rec.their_role) is ConnRecord.Role.REQUESTER
        ):
            invitation = await conn_rec.retrieve_invitation(self.context)
            if invitation.did:
                # populate recipient keys and endpoint from the ledger
                ledger: BaseLedger = await self.context.inject(
                    BaseLedger, required=False
                )
                if not ledger:
                    raise DIDXManagerError("Cannot resolve DID without ledger instance")
                async with ledger:
                    endpoint = await ledger.get_endpoint_for_did(invitation.did)
                    recipient_keys = [await ledger.get_key_for_did(invitation.did)]
                    routing_keys = []
            else:
                endpoint = invitation.endpoint
                recipient_keys = invitation.recipient_keys
                routing_keys = invitation.routing_keys

            results = [
                ConnectionTarget(
                    did=conn_rec.their_did,
                    endpoint=endpoint,
                    label=invitation.label,
                    recipient_keys=recipient_keys,
                    routing_keys=routing_keys,
                    sender_key=my_info.verkey,
                )
            ]
        else:
            if not conn_rec.their_did:
                self._logger.debug(
                    "No target DID associated with connection %s",
                    conn_rec.connection_id,
                )
                return None

            did_doc, _ = await self.fetch_did_document(conn_rec.their_did)
            results = self.diddoc_connection_targets(
                did_doc, my_info.verkey, conn_rec.their_label
            )

        return results

    async def verify_diddoc(
        self,
        wallet: BaseWallet,
        attached: AttachDecorator,
    ) -> DIDDoc:
        """Verify DIDDoc attachment and return signed data."""
        signed_diddoc_bytes = attached.data.signed
        if not signed_diddoc_bytes:
            raise DIDXManagerError("DID doc attachment is not signed.")
        if not await attached.data.verify(wallet):
            raise DIDXManagerError(f"DID doc attachment signature failed verification")

        return DIDDoc.deserialize(json.loads(signed_diddoc_bytes.decode()))

    def diddoc_connection_targets(
        self,
        doc: DIDDoc,
        sender_verkey: str,
        their_label: str = None,
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets from a DID Document.

        Args:
            doc: The DID Document to create the target from
            sender_verkey: The verkey we are using
            their_label: The connection label they are using
        """

        if not doc:
            raise DIDXManagerError("No DIDDoc provided for connection target")
        if not doc.did:
            raise DIDXManagerError("DIDDoc has no DID")
        if not doc.service:
            raise DIDXManagerError("No services defined by DIDDoc")

        targets = []
        for service in doc.service.values():
            if service.recip_keys:
                targets.append(
                    ConnectionTarget(
                        did=doc.did,
                        endpoint=service.endpoint,
                        label=their_label,
                        recipient_keys=[
                            key.value for key in (service.recip_keys or ())
                        ],
                        routing_keys=[
                            key.value for key in (service.routing_keys or ())
                        ],
                        sender_key=sender_verkey,
                    )
                )
        return targets

    async def establish_inbound(
        self,
        conn_rec: ConnRecord,
        inbound_connection_id: str,
        outbound_handler: Coroutine,
    ) -> str:
        """Assign the inbound routing connection for a connection record.

        Returns: the current routing state ("request")
        """

        # The connection must have a verkey, but in the case of a received
        # invitation we might not have created one yet
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        if conn_rec.my_did:
            my_info = await wallet.get_local_did(conn_rec.my_did)
        else:
            # Create new DID for connection
            my_info = await wallet.create_local_did()
            conn_rec.my_did = my_info.did

        try:
            router = await ConnRecord.retrieve_by_id(
                self.context, inbound_connection_id
            )
        except StorageNotFoundError:
            raise DIDXManagerError(
                f"Routing connection not found: {inbound_connection_id}"
            )
        if not router.is_ready:
            raise DIDXManagerError(
                f"Routing connection is not ready: {inbound_connection_id}"
            )
        conn_rec.inbound_connection_id = inbound_connection_id

        route_mgr = RoutingManager(self.context)

        await route_mgr.send_create_route(
            inbound_connection_id, my_info.verkey, outbound_handler
        )
        conn_rec.routing_state = ConnRecord.ROUTING_STATE_REQUEST
        await conn_rec.save(self.context)
        return conn_rec.routing_state

    async def update_inbound(
        self, inbound_connection_id: str, recip_verkey: str, routing_state: str
    ):
        """Activate connections once a route has been established.

        Looks up pending connections associated with the inbound routing
        connection and marks the routing as complete.
        """
        conn_recs = await ConnRecord.query(
            self.context, {"inbound_connection_id": inbound_connection_id}
        )
        wallet: BaseWallet = await self.context.inject(BaseWallet)

        for conn_rec in conn_recs:
            # check the recipient key
            if not conn_rec.my_did:
                continue
            conn_info = await wallet.get_local_did(conn_rec.my_did)
            if conn_info.verkey == recip_verkey:
                conn_rec.routing_state = routing_state
                await conn_rec.save(self.context)
