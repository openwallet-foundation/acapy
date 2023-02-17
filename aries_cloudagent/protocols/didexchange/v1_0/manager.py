"""Classes to manage connection establishment under RFC 23 (DID exchange)."""

import json
import logging
from typing import Optional

import pydid
from pydid import BaseDIDDocument as ResolvedDocument
from pydid import DIDCommService

from ....connections.base_manager import BaseConnectionManager
from ....connections.models.conn_record import ConnRecord
from ....connections.models.diddoc import DIDDoc
from ....core.error import BaseError
from ....core.oob_processor import OobMessageProcessor
from ....core.profile import Profile
from ....did.did_key import DIDKey
from ....messaging.decorators.attach_decorator import AttachDecorator
from ....messaging.responder import BaseResponder
from ....multitenant.base import BaseMultitenantManager
from ....resolver.base import ResolverError
from ....resolver.did_resolver import DIDResolver
from ....storage.error import StorageNotFoundError
from ....transport.inbound.receipt import MessageReceipt
from ....wallet.base import BaseWallet
from ....wallet.did_method import SOV
from ....wallet.did_posture import DIDPosture
from ....wallet.error import WalletError
from ....wallet.key_type import ED25519
from ...coordinate_mediation.v1_0.manager import MediationManager
from ...discovery.v2_0.manager import V20DiscoveryMgr
from ...out_of_band.v1_0.messages.invitation import (
    InvitationMessage as OOBInvitationMessage,
)
from ...out_of_band.v1_0.messages.service import Service as OOBService
from .message_types import ARIES_PROTOCOL as DIDX_PROTO
from .messages.complete import DIDXComplete
from .messages.problem_report_reason import ProblemReportReason
from .messages.request import DIDXRequest
from .messages.response import DIDXResponse


class DIDXManagerError(BaseError):
    """Connection error."""


class DIDXManager(BaseConnectionManager):
    """Class for managing connections under RFC 23 (DID exchange)."""

    def __init__(self, profile: Profile):
        """
        Initialize a DIDXManager.

        Args:
            profile: The profile for this did exchange manager
        """
        self._profile = profile
        self._logger = logging.getLogger(__name__)
        super().__init__(self._profile)

    @property
    def profile(self) -> Profile:
        """
        Accessor for the current profile.

        Returns:
            The profile for this did exchange manager

        """
        return self._profile

    async def receive_invitation(
        self,
        invitation: OOBInvitationMessage,
        their_public_did: Optional[str] = None,
        auto_accept: Optional[bool] = None,
        alias: Optional[str] = None,
        mediation_id: Optional[str] = None,
    ) -> ConnRecord:  # leave in didexchange as it uses a responder: not out-of-band
        """
        Create a new connection record to track a received invitation.

        Args:
            invitation: invitation to store
            their_public_did: their public DID
            auto_accept: set to auto-accept invitation (None to use config)
            alias: optional alias to set on record
            mediation_id: record id for mediation with routing_keys, service endpoint

        Returns:
            The new `ConnRecord` instance

        """
        if not invitation.services:
            raise DIDXManagerError(
                "Invitation must contain service blocks or service DIDs"
            )
        else:
            for s in invitation.services:
                if isinstance(s, OOBService):
                    if not s.recipient_keys or not s.service_endpoint:
                        raise DIDXManagerError(
                            "All service blocks in invitation with no service DIDs "
                            "must contain recipient key(s) and service endpoint(s)"
                        )

        accept = (
            ConnRecord.ACCEPT_AUTO
            if (
                auto_accept
                or (
                    auto_accept is None
                    and self.profile.settings.get("debug.auto_accept_invites")
                )
            )
            else ConnRecord.ACCEPT_MANUAL
        )

        service_item = invitation.services[0]
        # Create connection record
        conn_rec = ConnRecord(
            invitation_key=(
                DIDKey.from_did(service_item.recipient_keys[0]).public_key_b58
                if isinstance(service_item, OOBService)
                else None
            ),
            invitation_msg_id=invitation._id,
            their_label=invitation.label,
            their_role=ConnRecord.Role.RESPONDER.rfc23,
            state=ConnRecord.State.INVITATION.rfc23,
            accept=accept,
            alias=alias,
            their_public_did=their_public_did,
            connection_protocol=DIDX_PROTO,
        )

        async with self.profile.session() as session:
            await conn_rec.save(
                session,
                reason="Created new connection record from invitation",
                log_params={
                    "invitation": invitation,
                    "their_role": ConnRecord.Role.RESPONDER.rfc23,
                },
            )

            # Save the invitation for later processing
            await conn_rec.attach_invitation(session, invitation)
            if not conn_rec.invitation_key and conn_rec.their_public_did:
                did_document = await self.get_resolved_did_document(
                    conn_rec.their_public_did
                )
                conn_rec.invitation_key = did_document.verification_method[
                    0
                ].public_key_base58

        await self._route_manager.save_mediator_for_connection(
            self.profile, conn_rec, mediation_id=mediation_id
        )

        if conn_rec.accept == ConnRecord.ACCEPT_AUTO:
            request = await self.create_request(conn_rec, mediation_id=mediation_id)
            responder = self.profile.inject_or(BaseResponder)
            if responder:
                await responder.send_reply(
                    request,
                    connection_id=conn_rec.connection_id,
                )

                conn_rec.state = ConnRecord.State.REQUEST.rfc23
                async with self.profile.session() as session:
                    await conn_rec.save(session, reason="Sent connection request")
        else:
            self._logger.debug("Connection invitation will await acceptance")

        return conn_rec

    async def create_request_implicit(
        self,
        their_public_did: str,
        my_label: str = None,
        my_endpoint: str = None,
        mediation_id: str = None,
        use_public_did: bool = False,
        alias: str = None,
    ) -> ConnRecord:
        """
        Create and send a request against a public DID only (no explicit invitation).

        Args:
            their_public_did: public DID to which to request a connection
            my_label: my label for request
            my_endpoint: my endpoint
            mediation_id: record id for mediation with routing_keys, service endpoint
            use_public_did: use my public DID for this connection

        Returns:
            The new `ConnRecord` instance

        """
        my_public_info = None
        if use_public_did:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_public_info = await wallet.get_public_did()
            if not my_public_info:
                raise WalletError("No public DID configured")

        conn_rec = ConnRecord(
            my_did=my_public_info.did
            if my_public_info
            else None,  # create-request will fill in on local DID creation
            their_did=their_public_did,
            their_label=None,
            their_role=ConnRecord.Role.RESPONDER.rfc23,
            invitation_key=None,
            invitation_msg_id=None,
            accept=None,
            alias=alias,
            their_public_did=their_public_did,
            connection_protocol=DIDX_PROTO,
        )
        request = await self.create_request(  # saves and updates conn_rec
            conn_rec=conn_rec,
            my_label=my_label,
            my_endpoint=my_endpoint,
            mediation_id=mediation_id,
        )
        conn_rec.request_id = request._id
        conn_rec.state = ConnRecord.State.REQUEST.rfc23
        async with self.profile.session() as session:
            await conn_rec.save(session, reason="Created connection request")
        responder = self.profile.inject_or(BaseResponder)
        if responder:
            await responder.send(request, connection_id=conn_rec.connection_id)

        return conn_rec

    async def create_request(
        self,
        conn_rec: ConnRecord,
        my_label: str = None,
        my_endpoint: str = None,
        mediation_id: str = None,
    ) -> DIDXRequest:
        """
        Create a new connection request for a previously-received invitation.

        Args:
            conn_rec: The `ConnRecord` representing the invitation to accept
            my_label: My label for request
            my_endpoint: My endpoint
            mediation_id: The record id for mediation that contains routing_keys and
                service endpoint

        Returns:
            A new `DIDXRequest` message to send to the other agent

        """
        # Mediation Support
        mediation_record = await self._route_manager.mediation_record_for_connection(
            self.profile,
            conn_rec,
            mediation_id,
            or_default=True,
        )

        # Multitenancy setup
        multitenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        wallet_id = self.profile.settings.get("wallet.id")

        base_mediation_record = None
        if multitenant_mgr and wallet_id:
            base_mediation_record = await multitenant_mgr.get_default_mediator()

        my_info = None

        if conn_rec.my_did:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.get_local_did(conn_rec.my_did)
        else:
            # Create new DID for connection
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.create_local_did(
                    method=SOV,
                    key_type=ED25519,
                )
            conn_rec.my_did = my_info.did

        # Idempotent; if routing has already been set up, no action taken
        await self._route_manager.route_connection_as_invitee(
            self.profile, conn_rec, mediation_record
        )

        # Create connection request message
        if my_endpoint:
            my_endpoints = [my_endpoint]
        else:
            my_endpoints = []
            default_endpoint = self.profile.settings.get("default_endpoint")
            if default_endpoint:
                my_endpoints.append(default_endpoint)
            my_endpoints.extend(self.profile.settings.get("additional_endpoints", []))

        did_doc = await self.create_did_document(
            my_info,
            conn_rec.inbound_connection_id,
            my_endpoints,
            mediation_records=list(
                filter(None, [base_mediation_record, mediation_record])
            ),
        )
        if conn_rec.their_public_did is not None:
            qualified_did = conn_rec.their_public_did
            did_document = await self.get_resolved_did_document(qualified_did)
            did_url = await self.get_first_applicable_didcomm_service(did_document)
        pthid = conn_rec.invitation_msg_id or did_url
        attach = AttachDecorator.data_base64(did_doc.serialize())
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await attach.data.sign(my_info.verkey, wallet)
        if not my_label:
            my_label = self.profile.settings.get("default_label")
        request = DIDXRequest(
            label=my_label,
            did=conn_rec.my_did,
            did_doc_attach=attach,
        )
        request.assign_thread_id(thid=request._id, pthid=pthid)

        # Update connection state
        conn_rec.request_id = request._id
        conn_rec.state = ConnRecord.State.REQUEST.rfc23
        async with self.profile.session() as session:
            await conn_rec.save(session, reason="Created connection request")

        return request

    async def receive_request(
        self,
        request: DIDXRequest,
        recipient_did: str,
        recipient_verkey: str = None,
        my_endpoint: str = None,
        alias: str = None,
        auto_accept_implicit: bool = None,
    ) -> ConnRecord:
        """
        Receive and store a connection request.

        Args:
            request: The `DIDXRequest` to accept
            recipient_did: The (unqualified) recipient DID
            recipient_verkey: The recipient verkey: None for public recipient DID
            my_endpoint: My endpoint
            alias: Alias for the connection
            auto_accept: Auto-accept request against implicit invitation
        Returns:
            The new or updated `ConnRecord` instance

        """
        ConnRecord.log_state(
            "Receiving connection request",
            {"request": request},
            settings=self.profile.settings,
        )

        conn_rec = None
        connection_key = None
        my_info = None

        # Determine what key will need to sign the response
        if recipient_verkey:  # peer DID
            connection_key = recipient_verkey
            try:
                async with self.profile.session() as session:
                    conn_rec = await ConnRecord.retrieve_by_invitation_key(
                        session=session,
                        invitation_key=connection_key,
                        their_role=ConnRecord.Role.REQUESTER.rfc23,
                    )
            except StorageNotFoundError:
                if recipient_verkey:
                    raise DIDXManagerError(
                        "No explicit invitation found for pairwise connection "
                        f"in state {ConnRecord.State.INVITATION.rfc23}: "
                        "a prior connection request may have updated the connection state"
                    )
        else:
            if not self.profile.settings.get("public_invites"):
                raise DIDXManagerError(
                    "Public invitations are not enabled: connection request refused"
                )

            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.get_local_did(recipient_did)
            if DIDPosture.get(my_info.metadata) not in (
                DIDPosture.PUBLIC,
                DIDPosture.POSTED,
            ):
                raise DIDXManagerError(f"Request DID {recipient_did} is not public")
            connection_key = my_info.verkey

            async with self.profile.session() as session:
                conn_rec = await ConnRecord.retrieve_by_invitation_msg_id(
                    session=session,
                    invitation_msg_id=request._thread.pthid,
                    their_role=ConnRecord.Role.REQUESTER.rfc23,
                )

        if conn_rec:  # invitation was explicit
            connection_key = conn_rec.invitation_key
            if conn_rec.is_multiuse_invitation:
                async with self.profile.session() as session:
                    wallet = session.inject(BaseWallet)
                    my_info = await wallet.create_local_did(
                        method=SOV,
                        key_type=ED25519,
                    )

                new_conn_rec = ConnRecord(
                    invitation_key=connection_key,
                    my_did=my_info.did,
                    state=ConnRecord.State.REQUEST.rfc23,
                    accept=conn_rec.accept,
                    their_role=conn_rec.their_role,
                    connection_protocol=DIDX_PROTO,
                )
                async with self.profile.session() as session:
                    await new_conn_rec.save(
                        session,
                        reason=(
                            "Received connection request from multi-use invitation DID"
                        ),
                    )

                # Transfer metadata from multi-use to new connection
                # Must come after save so there's an ID to associate with metadata
                async with self.profile.session() as session:
                    for key, value in (
                        await conn_rec.metadata_get_all(session)
                    ).items():
                        await new_conn_rec.metadata_set(session, key, value)

                conn_rec = new_conn_rec

        # request DID doc describes requester DID
        if not (request.did_doc_attach and request.did_doc_attach.data):
            raise DIDXManagerError(
                "DID Doc attachment missing or has no data: "
                "cannot connect to public DID"
            )
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            conn_did_doc = await self.verify_diddoc(wallet, request.did_doc_attach)
        if request.did != conn_did_doc.did:
            raise DIDXManagerError(
                (
                    f"Connection DID {request.did} does not match "
                    f"DID Doc id {conn_did_doc.did}"
                ),
                error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED.value,
            )
        await self.store_did_document(conn_did_doc)

        if conn_rec:  # request is against explicit invitation
            auto_accept = (
                conn_rec.accept == ConnRecord.ACCEPT_AUTO
            )  # null=manual; oob-manager calculated at conn rec creation

            conn_rec.their_label = request.label
            if alias:
                conn_rec.alias = alias
            conn_rec.their_did = request.did
            conn_rec.state = ConnRecord.State.REQUEST.rfc23
            conn_rec.request_id = request._id
            async with self.profile.session() as session:
                await conn_rec.save(
                    session, reason="Received connection request from invitation"
                )
        else:
            # request is against implicit invitation on public DID
            if not self.profile.settings.get("requests_through_public_did"):
                raise DIDXManagerError(
                    "Unsolicited connection requests to " "public DID is not enabled"
                )
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.create_local_did(
                    method=SOV,
                    key_type=ED25519,
                )

            auto_accept = bool(
                auto_accept_implicit
                or (
                    auto_accept_implicit is None
                    and self.profile.settings.get("debug.auto_accept_requests", False)
                )
            )

            conn_rec = ConnRecord(
                my_did=my_info.did,
                accept=(
                    ConnRecord.ACCEPT_AUTO if auto_accept else ConnRecord.ACCEPT_MANUAL
                ),
                their_did=request.did,
                their_label=request.label,
                alias=alias,
                their_role=ConnRecord.Role.REQUESTER.rfc23,
                invitation_key=connection_key,
                invitation_msg_id=None,
                request_id=request._id,
                state=ConnRecord.State.REQUEST.rfc23,
                connection_protocol=DIDX_PROTO,
            )
            async with self.profile.session() as session:
                await conn_rec.save(
                    session, reason="Received connection request from public DID"
                )

        async with self.profile.session() as session:
            # Attach the connection request so it can be found and responded to
            await conn_rec.attach_request(session, request)

        # Clean associated oob record if not needed anymore
        oob_processor = self.profile.inject(OobMessageProcessor)
        await oob_processor.clean_finished_oob_record(self.profile, request)

        return conn_rec

    async def create_response(
        self,
        conn_rec: ConnRecord,
        my_endpoint: str = None,
        mediation_id: str = None,
    ) -> DIDXResponse:
        """
        Create a connection response for a received connection request.

        Args:
            conn_rec: The `ConnRecord` with a pending connection request
            my_endpoint: Current agent endpoint
            mediation_id: The record id for mediation that contains routing_keys and
                service endpoint

        Returns:
            New `DIDXResponse` message

        """
        ConnRecord.log_state(
            "Creating connection response",
            {"connection_id": conn_rec.connection_id},
            settings=self.profile.settings,
        )

        mediation_record = await self._route_manager.mediation_record_for_connection(
            self.profile, conn_rec, mediation_id
        )

        # Multitenancy setup
        multitenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        wallet_id = self.profile.settings.get("wallet.id")

        base_mediation_record = None
        if multitenant_mgr and wallet_id:
            base_mediation_record = await multitenant_mgr.get_default_mediator()

        if ConnRecord.State.get(conn_rec.state) is not ConnRecord.State.REQUEST:
            raise DIDXManagerError(
                f"Connection not in state {ConnRecord.State.REQUEST.rfc23}"
            )
        async with self.profile.session() as session:
            request = await conn_rec.retrieve_request(session)

        if conn_rec.my_did:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.get_local_did(conn_rec.my_did)
        else:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.create_local_did(
                    method=SOV,
                    key_type=ED25519,
                )
            conn_rec.my_did = my_info.did

        # Idempotent; if routing has already been set up, no action taken
        await self._route_manager.route_connection_as_inviter(
            self.profile, conn_rec, mediation_record
        )

        # Create connection response message
        if my_endpoint:
            my_endpoints = [my_endpoint]
        else:
            my_endpoints = []
            default_endpoint = self.profile.settings.get("default_endpoint")
            if default_endpoint:
                my_endpoints.append(default_endpoint)
            my_endpoints.extend(self.profile.settings.get("additional_endpoints", []))

        did_doc = await self.create_did_document(
            my_info,
            conn_rec.inbound_connection_id,
            my_endpoints,
            mediation_records=list(
                filter(None, [base_mediation_record, mediation_record])
            ),
        )
        attach = AttachDecorator.data_base64(did_doc.serialize())
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await attach.data.sign(conn_rec.invitation_key, wallet)
        response = DIDXResponse(did=my_info.did, did_doc_attach=attach)
        # Assign thread information
        response.assign_thread_from(request)
        response.assign_trace_from(request)

        # Update connection state
        conn_rec.state = ConnRecord.State.RESPONSE.rfc23
        async with self.profile.session() as session:
            await conn_rec.save(
                session,
                reason="Created connection response",
                log_params={"response": response},
            )

        async with self.profile.session() as session:
            send_mediation_request = await conn_rec.metadata_get(
                session, MediationManager.SEND_REQ_AFTER_CONNECTION
            )
        if send_mediation_request:
            temp_mediation_mgr = MediationManager(self.profile)
            _record, request = await temp_mediation_mgr.prepare_request(
                conn_rec.connection_id
            )
            responder = self.profile.inject(BaseResponder)
            await responder.send(request, connection_id=conn_rec.connection_id)

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

        conn_rec = None
        if response._thread:
            # identify the request by the thread ID
            async with self.profile.session() as session:
                try:
                    conn_rec = await ConnRecord.retrieve_by_request_id(
                        session,
                        response._thread_id,
                        their_role=ConnRecord.Role.RESPONDER.rfc23,
                    )
                except StorageNotFoundError:
                    pass
                if not conn_rec:
                    try:
                        conn_rec = await ConnRecord.retrieve_by_request_id(
                            session,
                            response._thread_id,
                            their_role=ConnRecord.Role.RESPONDER.rfc160,
                        )
                    except StorageNotFoundError:
                        pass

        if not conn_rec and receipt.sender_did:
            # identify connection by the DID they used for us
            try:
                async with self.profile.session() as session:
                    conn_rec = await ConnRecord.retrieve_by_did(
                        session=session,
                        their_did=receipt.sender_did,
                        my_did=receipt.recipient_did,
                        their_role=ConnRecord.Role.RESPONDER.rfc23,
                    )
            except StorageNotFoundError:
                pass

        if not conn_rec:
            raise DIDXManagerError(
                "No corresponding connection request found",
                error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED.value,
            )

        if ConnRecord.State.get(conn_rec.state) is not ConnRecord.State.REQUEST:
            raise DIDXManagerError(
                "Cannot accept connection response for connection"
                f" in state: {conn_rec.state}"
            )

        their_did = response.did
        if not response.did_doc_attach:
            raise DIDXManagerError("No DIDDoc attached; cannot connect to public DID")
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            conn_did_doc = await self.verify_diddoc(
                wallet, response.did_doc_attach, conn_rec.invitation_key
            )
        if their_did != conn_did_doc.did:
            raise DIDXManagerError(
                f"Connection DID {their_did} "
                f"does not match DID doc id {conn_did_doc.did}"
            )
        await self.store_did_document(conn_did_doc)

        conn_rec.their_did = their_did
        conn_rec.state = ConnRecord.State.RESPONSE.rfc23
        async with self.profile.session() as session:
            await conn_rec.save(session, reason="Accepted connection response")

        async with self.profile.session() as session:
            send_mediation_request = await conn_rec.metadata_get(
                session, MediationManager.SEND_REQ_AFTER_CONNECTION
            )
        if send_mediation_request:
            temp_mediation_mgr = MediationManager(self.profile)
            _record, request = await temp_mediation_mgr.prepare_request(
                conn_rec.connection_id
            )
            responder = self.profile.inject(BaseResponder)
            await responder.send(request, connection_id=conn_rec.connection_id)

        # create and send connection-complete message
        complete = DIDXComplete()
        complete.assign_thread_from(response)
        responder = self.profile.inject_or(BaseResponder)
        if responder:
            await responder.send_reply(complete, connection_id=conn_rec.connection_id)

            conn_rec.state = ConnRecord.State.COMPLETED.rfc23
            async with self.profile.session() as session:
                await conn_rec.save(session, reason="Sent connection complete")
                if session.settings.get("auto_disclose_features"):
                    discovery_mgr = V20DiscoveryMgr(self._profile)
                    await discovery_mgr.proactive_disclose_features(
                        connection_id=conn_rec.connection_id
                    )

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
        async with self.profile.session() as session:
            try:
                conn_rec = await ConnRecord.retrieve_by_request_id(
                    session,
                    complete._thread_id,
                    their_role=ConnRecord.Role.REQUESTER.rfc23,
                )
            except StorageNotFoundError:
                pass

            if not conn_rec:
                try:
                    conn_rec = await ConnRecord.retrieve_by_request_id(
                        session,
                        complete._thread_id,
                        their_role=ConnRecord.Role.REQUESTER.rfc160,
                    )
                except StorageNotFoundError:
                    pass

        if not conn_rec:
            raise DIDXManagerError(
                "No corresponding connection request found",
                error_code=ProblemReportReason.COMPLETE_NOT_ACCEPTED.value,
            )

        conn_rec.state = ConnRecord.State.COMPLETED.rfc23
        async with self.profile.session() as session:
            await conn_rec.save(session, reason="Received connection complete")
            if session.settings.get("auto_disclose_features"):
                discovery_mgr = V20DiscoveryMgr(self._profile)
                await discovery_mgr.proactive_disclose_features(
                    connection_id=conn_rec.connection_id
                )

        return conn_rec

    async def verify_diddoc(
        self,
        wallet: BaseWallet,
        attached: AttachDecorator,
        invi_key: str = None,
    ) -> DIDDoc:
        """Verify DIDDoc attachment and return signed data."""
        signed_diddoc_bytes = attached.data.signed
        if not signed_diddoc_bytes:
            raise DIDXManagerError("DID doc attachment is not signed.")
        if not await attached.data.verify(wallet, invi_key):
            raise DIDXManagerError("DID doc attachment signature failed verification")

        return DIDDoc.deserialize(json.loads(signed_diddoc_bytes.decode()))

    async def get_resolved_did_document(self, qualified_did: str) -> ResolvedDocument:
        """Return resolved DID document."""
        resolver = self._profile.inject(DIDResolver)
        if not qualified_did.startswith("did:"):
            qualified_did = f"did:sov:{qualified_did}"
        try:
            doc_dict: dict = await resolver.resolve(self._profile, qualified_did)
            doc = pydid.deserialize_document(doc_dict, strict=True)
            return doc
        except ResolverError as error:
            raise DIDXManagerError(
                "Failed to resolve public DID in invitation"
            ) from error

    async def get_first_applicable_didcomm_service(
        self, did_doc: ResolvedDocument
    ) -> str:
        """Return first applicable DIDComm service url with highest priority."""
        if not did_doc.service:
            raise DIDXManagerError(
                "Cannot connect via public DID that has no associated services"
            )

        didcomm_services = sorted(
            [
                service
                for service in did_doc.service
                if isinstance(service, DIDCommService)
            ],
            key=lambda service: service.priority,
        )

        if not didcomm_services:
            raise DIDXManagerError(
                "Cannot connect via public DID that has no associated DIDComm services"
            )

        first_didcomm_service, *_ = didcomm_services
        return first_didcomm_service.id
