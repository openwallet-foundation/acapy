"""Classes to manage connections."""

import logging
from typing import Coroutine, Optional, Sequence, Tuple, cast


from ....core.oob_processor import OobMessageProcessor
from ....connections.base_manager import BaseConnectionManager
from ....connections.models.conn_record import ConnRecord
from ....core.error import BaseError
from ....core.profile import Profile
from ....messaging.responder import BaseResponder
from ....messaging.valid import IndyDID
from ....multitenant.base import BaseMultitenantManager
from ....storage.error import StorageNotFoundError
from ....transport.inbound.receipt import MessageReceipt
from ....wallet.base import BaseWallet
from ....wallet.did_method import SOV
from ....wallet.key_type import ED25519
from ...coordinate_mediation.v1_0.manager import MediationManager
from ...routing.v1_0.manager import RoutingManager
from .message_types import ARIES_PROTOCOL as CONN_PROTO
from .messages.connection_invitation import ConnectionInvitation
from .messages.connection_request import ConnectionRequest
from .messages.connection_response import ConnectionResponse
from .messages.problem_report import ProblemReportReason
from .models.connection_detail import ConnectionDetail


class ConnectionManagerError(BaseError):
    """Connection error."""


class ConnectionManager(BaseConnectionManager):
    """Class for managing connections."""

    def __init__(self, profile: Profile):
        """
        Initialize a ConnectionManager.

        Args:
            profile: The profile for this connection manager
        """
        self._profile = profile
        self._logger = logging.getLogger(__name__)
        super().__init__(self._profile)

    @property
    def profile(self) -> Profile:
        """
        Accessor for the current profile.

        Returns:
            The profile for this connection manager

        """
        return self._profile

    async def create_invitation(
        self,
        my_label: str = None,
        my_endpoint: str = None,
        auto_accept: bool = None,
        public: bool = False,
        multi_use: bool = False,
        alias: str = None,
        routing_keys: Sequence[str] = None,
        recipient_keys: Sequence[str] = None,
        metadata: dict = None,
        mediation_id: str = None,
    ) -> Tuple[ConnRecord, ConnectionInvitation]:
        """
        Generate new connection invitation.

        This interaction represents an out-of-band communication channel. In the future
        and in practice, these sort of invitations will be received over any number of
        channels such as SMS, Email, QR Code, NFC, etc.

        Structure of an invite message:

        ::

            {
                "@type": "https://didcomm.org/connections/1.0/invitation",
                "label": "Alice",
                "did": "did:sov:QmWbsNYhMrjHiqZDTUTEJs"
            }

        Or, in the case of a peer DID:

        ::

            {
                "@type": "https://didcomm.org/connections/1.0/invitation",
                "label": "Alice",
                "did": "did:peer:oiSqsNYhMrjHiqZDTUthsw",
                "recipient_keys": ["8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"],
                "service_endpoint": "https://example.com/endpoint"
                "routing_keys": ["9EH5gYEeNc3z7PYXmd53d5x6qAfCNrqQqEB4nS7Zfu6K"],
            }

        Args:
            my_label: label for this connection
            my_endpoint: endpoint where other party can reach me
            auto_accept: auto-accept a corresponding connection request
                (None to use config)
            public: set to create an invitation from the public DID
            multi_use: set to True to create an invitation for multiple use
            alias: optional alias to apply to connection for later use

        Returns:
            A tuple of the new `ConnRecord` and `ConnectionInvitation` instances

        """
        # Mediation Record can still be None after this operation if no
        # mediation id passed and no default
        mediation_record = await self._route_manager.mediation_record_if_id(
            self.profile,
            mediation_id,
            or_default=True,
        )
        image_url = self.profile.context.settings.get("image_url")
        invitation = None
        connection = None

        invitation_mode = ConnRecord.INVITATION_MODE_ONCE
        if multi_use:
            invitation_mode = ConnRecord.INVITATION_MODE_MULTI

        if not my_label:
            my_label = self.profile.settings.get("default_label")

        accept = (
            ConnRecord.ACCEPT_AUTO
            if (
                auto_accept
                or (
                    auto_accept is None
                    and self.profile.settings.get("debug.auto_accept_requests")
                )
            )
            else ConnRecord.ACCEPT_MANUAL
        )

        if recipient_keys:
            # TODO: register recipient keys for relay
            # TODO: check that recipient keys are in wallet
            invitation_key = recipient_keys[0]  # TODO first key appropriate?
        else:
            # Create and store new invitation key
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                invitation_signing_key = await wallet.create_signing_key(
                    key_type=ED25519
                )
            invitation_key = invitation_signing_key.verkey
            recipient_keys = [invitation_key]

        if public:
            if not self.profile.settings.get("public_invites"):
                raise ConnectionManagerError("Public invitations are not enabled")

            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                public_did = await wallet.get_public_did()
            if not public_did:
                raise ConnectionManagerError(
                    "Cannot create public invitation with no public DID"
                )

            # FIXME - allow ledger instance to format public DID with prefix?
            public_did_did = public_did.did
            if bool(IndyDID.PATTERN.match(public_did_did)):
                public_did_did = f"did:sov:{public_did.did}"

            invitation = ConnectionInvitation(
                label=my_label, did=public_did_did, image_url=image_url
            )

            connection = ConnRecord(  # create connection record
                invitation_key=public_did.verkey,
                invitation_msg_id=invitation._id,
                invitation_mode=invitation_mode,
                their_role=ConnRecord.Role.REQUESTER.rfc23,
                state=ConnRecord.State.INVITATION.rfc23,
                accept=accept,
                alias=alias,
                connection_protocol=CONN_PROTO,
            )

            async with self.profile.session() as session:
                await connection.save(session, reason="Created new invitation")

            # Add mapping for multitenant relaying.
            # Mediation of public keys is not supported yet
            await self._route_manager.route_verkey(self.profile, public_did.verkey)

        else:
            # Create connection record
            connection = ConnRecord(
                invitation_key=invitation_key,  # TODO: determine correct key to use
                their_role=ConnRecord.Role.REQUESTER.rfc160,
                state=ConnRecord.State.INVITATION.rfc160,
                accept=accept,
                invitation_mode=invitation_mode,
                alias=alias,
                connection_protocol=CONN_PROTO,
            )
            async with self.profile.session() as session:
                await connection.save(session, reason="Created new invitation")

            await self._route_manager.route_invitation(
                self.profile, connection, mediation_record
            )
            routing_keys, my_endpoint = await self._route_manager.routing_info(
                self.profile,
                my_endpoint or cast(str, self.profile.settings.get("default_endpoint")),
                mediation_record,
            )

            # Create connection invitation message
            # Note: Need to split this into two stages
            # to support inbound routing of invites
            # Would want to reuse create_did_document and convert the result
            invitation = ConnectionInvitation(
                label=my_label,
                recipient_keys=recipient_keys,
                routing_keys=routing_keys,
                endpoint=my_endpoint,
                image_url=image_url,
            )

        async with self.profile.session() as session:
            await connection.attach_invitation(session, invitation)

            if metadata:
                for key, value in metadata.items():
                    await connection.metadata_set(session, key, value)

        return connection, invitation

    async def receive_invitation(
        self,
        invitation: ConnectionInvitation,
        their_public_did: Optional[str] = None,
        auto_accept: Optional[bool] = None,
        alias: Optional[str] = None,
        mediation_id: Optional[str] = None,
    ) -> ConnRecord:
        """
        Create a new connection record to track a received invitation.

        Args:
            invitation: The `ConnectionInvitation` to store
            auto_accept: set to auto-accept the invitation (None to use config)
            alias: optional alias to set on the record

        Returns:
            The new `ConnRecord` instance

        """
        if not invitation.did:
            if not invitation.recipient_keys:
                raise ConnectionManagerError(
                    "Invitation must contain recipient key(s)",
                    error_code="missing-recipient-keys",
                )
            if not invitation.endpoint:
                raise ConnectionManagerError(
                    "Invitation must contain an endpoint",
                    error_code="missing-endpoint",
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
        # Create connection record
        connection = ConnRecord(
            invitation_key=invitation.recipient_keys and invitation.recipient_keys[0],
            their_label=invitation.label,
            invitation_msg_id=invitation._id,
            their_role=ConnRecord.Role.RESPONDER.rfc160,
            state=ConnRecord.State.INVITATION.rfc160,
            accept=accept,
            alias=alias,
            their_public_did=their_public_did,
            connection_protocol=CONN_PROTO,
        )

        async with self.profile.session() as session:
            await connection.save(
                session,
                reason="Created new connection record from invitation",
                log_params={"invitation": invitation, "their_label": invitation.label},
            )

            # Save the invitation for later processing
            await connection.attach_invitation(session, invitation)

        await self._route_manager.save_mediator_for_connection(
            self.profile, connection, mediation_id=mediation_id
        )

        if connection.accept == ConnRecord.ACCEPT_AUTO:
            request = await self.create_request(connection, mediation_id=mediation_id)
            responder = self.profile.inject_or(BaseResponder)
            if responder:
                await responder.send(request, connection_id=connection.connection_id)
                # refetch connection for accurate state
                async with self.profile.session() as session:
                    connection = await ConnRecord.retrieve_by_id(
                        session, connection.connection_id
                    )
        else:
            self._logger.debug("Connection invitation will await acceptance")
        return connection

    async def create_request(
        self,
        connection: ConnRecord,
        my_label: str = None,
        my_endpoint: str = None,
        mediation_id: str = None,
    ) -> ConnectionRequest:
        """
        Create a new connection request for a previously-received invitation.

        Args:
            connection: The `ConnRecord` representing the invitation to accept
            my_label: My label
            my_endpoint: My endpoint

        Returns:
            A new `ConnectionRequest` message to send to the other agent

        """

        mediation_record = await self._route_manager.mediation_record_for_connection(
            self.profile,
            connection,
            mediation_id,
            or_default=True,
        )

        multitenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        wallet_id = self.profile.settings.get("wallet.id")

        base_mediation_record = None
        if multitenant_mgr and wallet_id:
            base_mediation_record = await multitenant_mgr.get_default_mediator()

        if connection.my_did:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.get_local_did(connection.my_did)
        else:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                # Create new DID for connection
                my_info = await wallet.create_local_did(SOV, ED25519)
            connection.my_did = my_info.did

        # Idempotent; if routing has already been set up, no action taken
        await self._route_manager.route_connection_as_invitee(
            self.profile, connection, mediation_record
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
            connection.inbound_connection_id,
            my_endpoints,
            mediation_records=list(
                filter(None, [base_mediation_record, mediation_record])
            ),
        )

        if not my_label:
            my_label = self.profile.settings.get("default_label")
        request = ConnectionRequest(
            label=my_label,
            connection=ConnectionDetail(did=connection.my_did, did_doc=did_doc),
            image_url=self.profile.settings.get("image_url"),
        )
        request.assign_thread_id(thid=request._id, pthid=connection.invitation_msg_id)

        # Update connection state
        connection.request_id = request._id
        connection.state = ConnRecord.State.REQUEST.rfc160

        async with self.profile.session() as session:
            await connection.save(session, reason="Created connection request")

        return request

    async def receive_request(
        self,
        request: ConnectionRequest,
        receipt: MessageReceipt,
    ) -> ConnRecord:
        """
        Receive and store a connection request.

        Args:
            request: The `ConnectionRequest` to accept
            receipt: The message receipt

        Returns:
            The new or updated `ConnRecord` instance

        """
        ConnRecord.log_state(
            "Receiving connection request",
            {"request": request},
            settings=self.profile.settings,
        )

        connection = None
        connection_key = None
        my_info = None

        # Determine what key will need to sign the response
        if receipt.recipient_did_public:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.get_local_did(receipt.recipient_did)
            connection_key = my_info.verkey
        else:
            connection_key = receipt.recipient_verkey
            try:
                async with self.profile.session() as session:
                    connection = await ConnRecord.retrieve_by_invitation_key(
                        session=session,
                        invitation_key=connection_key,
                        their_role=ConnRecord.Role.REQUESTER.rfc160,
                    )
            except StorageNotFoundError:
                raise ConnectionManagerError(
                    "No invitation found for pairwise connection "
                    f"in state {ConnRecord.State.INVITATION.rfc160}: "
                    "a prior connection request may have updated the connection state"
                )

        invitation = None
        if connection:
            async with self.profile.session() as session:
                invitation = await connection.retrieve_invitation(session)
            connection_key = connection.invitation_key
            ConnRecord.log_state(
                "Found invitation",
                {"invitation": invitation},
                settings=self.profile.settings,
            )

            if connection.is_multiuse_invitation:
                async with self.profile.session() as session:
                    wallet = session.inject(BaseWallet)
                    my_info = await wallet.create_local_did(SOV, ED25519)

                new_connection = ConnRecord(
                    invitation_key=connection_key,
                    my_did=my_info.did,
                    state=ConnRecord.State.REQUEST.rfc160,
                    accept=connection.accept,
                    their_role=connection.their_role,
                    connection_protocol=CONN_PROTO,
                )
                async with self.profile.session() as session:
                    await new_connection.save(
                        session,
                        reason=(
                            "Received connection request from multi-use invitation DID"
                        ),
                        event=False,
                    )

                # Transfer metadata from multi-use to new connection
                # Must come after save so there's an ID to associate with metadata
                async with self.profile.session() as session:
                    for key, value in (
                        await connection.metadata_get_all(session)
                    ).items():
                        await new_connection.metadata_set(session, key, value)

                connection = new_connection

        conn_did_doc = request.connection.did_doc
        if not conn_did_doc:
            raise ConnectionManagerError(
                "No DIDDoc provided; cannot connect to public DID"
            )
        if request.connection.did != conn_did_doc.did:
            raise ConnectionManagerError(
                "Connection DID does not match DIDDoc id",
                error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED.value,
            )
        await self.store_did_document(conn_did_doc)

        if connection:
            connection.their_label = request.label
            connection.their_did = request.connection.did
            connection.state = ConnRecord.State.REQUEST.rfc160
            async with self.profile.session() as session:
                # force emitting event that would be ignored for multi-use invitations
                # since the record is not new, and the state was not updated
                await connection.save(
                    session,
                    reason="Received connection request from invitation",
                    event=True,
                )
        elif not self.profile.settings.get("public_invites"):
            raise ConnectionManagerError("Public invitations are not enabled")
        else:  # request from public did
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.create_local_did(SOV, ED25519)

            async with self.profile.session() as session:
                connection = await ConnRecord.retrieve_by_invitation_msg_id(
                    session=session,
                    invitation_msg_id=request._thread.pthid,
                    their_role=ConnRecord.Role.REQUESTER.rfc160,
                )
            if not connection:
                if not self.profile.settings.get("requests_through_public_did"):
                    raise ConnectionManagerError(
                        "Unsolicited connection requests to "
                        "public DID is not enabled"
                    )
                connection = ConnRecord()
            connection.invitation_key = connection_key
            connection.my_did = my_info.did
            connection.their_role = ConnRecord.Role.RESPONDER.rfc160
            connection.their_did = request.connection.did
            connection.their_label = request.label
            connection.accept = (
                ConnRecord.ACCEPT_AUTO
                if self.profile.settings.get("debug.auto_accept_requests")
                else ConnRecord.ACCEPT_MANUAL
            )
            connection.state = ConnRecord.State.REQUEST.rfc160
            connection.connection_protocol = CONN_PROTO
            async with self.profile.session() as session:
                await connection.save(
                    session, reason="Received connection request from public DID"
                )

        async with self.profile.session() as session:
            # Attach the connection request so it can be found and responded to
            await connection.attach_request(session, request)

        # Clean associated oob record if not needed anymore
        oob_processor = self.profile.inject(OobMessageProcessor)
        await oob_processor.clean_finished_oob_record(self.profile, request)

        return connection

    async def create_response(
        self,
        connection: ConnRecord,
        my_endpoint: str = None,
        mediation_id: str = None,
    ) -> ConnectionResponse:
        """
        Create a connection response for a received connection request.

        Args:
            connection: The `ConnRecord` with a pending connection request
            my_endpoint: The endpoint I can be reached at
            mediation_id: The record id for mediation that contains routing_keys and
            service endpoint
        Returns:
            A tuple of the updated `ConnRecord` new `ConnectionResponse` message

        """
        ConnRecord.log_state(
            "Creating connection response",
            {"connection_id": connection.connection_id},
            settings=self.profile.settings,
        )

        mediation_record = await self._route_manager.mediation_record_for_connection(
            self.profile, connection, mediation_id
        )

        # Multitenancy setup
        multitenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        wallet_id = self.profile.settings.get("wallet.id")

        base_mediation_record = None
        if multitenant_mgr and wallet_id:
            base_mediation_record = await multitenant_mgr.get_default_mediator()

        if ConnRecord.State.get(connection.state) not in (
            ConnRecord.State.REQUEST,
            ConnRecord.State.RESPONSE,
        ):
            raise ConnectionManagerError(
                "Connection is not in the request or response state"
            )

        async with self.profile.session() as session:
            request = await connection.retrieve_request(session)

        if connection.my_did:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.get_local_did(connection.my_did)
        else:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.create_local_did(SOV, ED25519)
            connection.my_did = my_info.did

        # Idempotent; if routing has already been set up, no action taken
        await self._route_manager.route_connection_as_inviter(
            self.profile, connection, mediation_record
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
            connection.inbound_connection_id,
            my_endpoints,
            mediation_records=list(
                filter(None, [base_mediation_record, mediation_record])
            ),
        )

        response = ConnectionResponse(
            connection=ConnectionDetail(did=my_info.did, did_doc=did_doc)
        )

        # Assign thread information
        response.assign_thread_from(request)
        response.assign_trace_from(request)
        # Sign connection field using the invitation key
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await response.sign_field("connection", connection.invitation_key, wallet)

            # Update connection state
            connection.state = ConnRecord.State.RESPONSE.rfc160

            await connection.save(
                session,
                reason="Created connection response",
                log_params={"response": response},
            )

        # TODO It's possible the mediation request sent here might arrive
        # before the connection response. This would result in an error condition
        # difficult to accomodate for without modifying handlers for trust ping
        # to ensure the connection is active.
        async with self.profile.session() as session:
            send_mediation_request = await connection.metadata_get(
                session, MediationManager.SEND_REQ_AFTER_CONNECTION
            )
        if send_mediation_request:
            mgr = MediationManager(self.profile)
            _record, request = await mgr.prepare_request(connection.connection_id)
            responder = self.profile.inject(BaseResponder)
            await responder.send(request, connection_id=connection.connection_id)

        return response

    async def accept_response(
        self, response: ConnectionResponse, receipt: MessageReceipt
    ) -> ConnRecord:
        """
        Accept a connection response.

        Process a ConnectionResponse message by looking up
        the connection request and setting up the pairwise connection.

        Args:
            response: The `ConnectionResponse` to accept
            receipt: The message receipt

        Returns:
            The updated `ConnRecord` representing the connection

        Raises:
            ConnectionManagerError: If there is no DID associated with the
                connection response
            ConnectionManagerError: If the corresponding connection is not
                at the request or response stage

        """
        connection = None
        if response._thread:
            # identify the request by the thread ID
            try:
                async with self.profile.session() as session:
                    connection = await ConnRecord.retrieve_by_request_id(
                        session, response._thread_id
                    )
            except StorageNotFoundError:
                pass

        if not connection and receipt.sender_did:
            # identify connection by the DID they used for us
            try:
                async with self.profile.session() as session:
                    connection = await ConnRecord.retrieve_by_did(
                        session, receipt.sender_did, receipt.recipient_did
                    )
            except StorageNotFoundError:
                pass

        if not connection:
            raise ConnectionManagerError(
                "No corresponding connection request found",
                error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED.value,
            )

        if ConnRecord.State.get(connection.state) not in (
            ConnRecord.State.REQUEST,
            ConnRecord.State.RESPONSE,
        ):
            raise ConnectionManagerError(
                f"Cannot accept connection response for connection"
                f" in state: {connection.state}"
            )

        their_did = response.connection.did
        conn_did_doc = response.connection.did_doc
        if not conn_did_doc:
            raise ConnectionManagerError(
                "No DIDDoc provided; cannot connect to public DID"
            )
        if their_did != conn_did_doc.did:
            raise ConnectionManagerError("Connection DID does not match DIDDoc id")
        # Verify connection response using connection field
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            try:
                await response.verify_signed_field(
                    "connection", wallet, connection.invitation_key
                )
            except ValueError:
                raise ConnectionManagerError(
                    "connection field verification using invitation_key failed"
                )
        await self.store_did_document(conn_did_doc)

        connection.their_did = their_did
        connection.state = ConnRecord.State.RESPONSE.rfc160
        async with self.profile.session() as session:
            await connection.save(session, reason="Accepted connection response")

            send_mediation_request = await connection.metadata_get(
                session, MediationManager.SEND_REQ_AFTER_CONNECTION
            )
        if send_mediation_request:
            mgr = MediationManager(self.profile)
            _record, request = await mgr.prepare_request(connection.connection_id)
            responder = self.profile.inject(BaseResponder)
            await responder.send(request, connection_id=connection.connection_id)

        return connection

    async def establish_inbound(
        self,
        connection: ConnRecord,
        inbound_connection_id: str,
        outbound_handler: Coroutine,
    ) -> str:
        """Assign the inbound routing connection for a connection record.

        Returns: the current routing state (request or done)

        """

        # The connection must have a verkey, but in the case of a received
        # invitation we might not have created one yet
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            if connection.my_did:
                my_info = await wallet.get_local_did(connection.my_did)
            else:
                # Create new DID for connection
                my_info = await wallet.create_local_did(SOV, ED25519)
                connection.my_did = my_info.did

        try:
            async with self.profile.session() as session:
                router = await ConnRecord.retrieve_by_id(session, inbound_connection_id)
        except StorageNotFoundError:
            raise ConnectionManagerError(
                f"Routing connection not found: {inbound_connection_id}"
            )
        if not router.is_ready:
            raise ConnectionManagerError(
                f"Routing connection is not ready: {inbound_connection_id}"
            )
        connection.inbound_connection_id = inbound_connection_id

        route_mgr = RoutingManager(self.profile)

        await route_mgr.send_create_route(
            inbound_connection_id, my_info.verkey, outbound_handler
        )
        connection.routing_state = ConnRecord.ROUTING_STATE_REQUEST
        async with self.profile.session() as session:
            await connection.save(session)
        return connection.routing_state

    async def update_inbound(
        self, inbound_connection_id: str, recip_verkey: str, routing_state: str
    ):
        """Activate connections once a route has been established.

        Looks up pending connections associated with the inbound routing
        connection and marks the routing as complete.
        """
        async with self.profile.session() as session:
            conns = await ConnRecord.query(
                session, {"inbound_connection_id": inbound_connection_id}
            )
            wallet = session.inject(BaseWallet)

            for connection in conns:
                # check the recipient key
                if not connection.my_did:
                    continue
                conn_info = await wallet.get_local_did(connection.my_did)
                if conn_info.verkey == recip_verkey:
                    connection.routing_state = routing_state
                    await connection.save(session)
