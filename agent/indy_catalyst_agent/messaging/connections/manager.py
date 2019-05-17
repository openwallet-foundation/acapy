"""Classes to manage connections."""

import asyncio
import aiohttp
import json
import logging

from typing import Tuple, Union

from ...error import BaseError
from ..agent_message import AgentMessage
from ...config.base import InjectorError
from ..message_delivery import MessageDelivery
from .messages.connection_invitation import ConnectionInvitation
from .messages.connection_request import ConnectionRequest
from .messages.connection_response import ConnectionResponse
from ..message_factory import MessageFactory, MessageParseError
from .models.connection_detail import ConnectionDetail
from .models.connection_record import ConnectionRecord
from .models.connection_target import ConnectionTarget
from ..request_context import RequestContext
from ..routing.messages.forward import Forward
from ...storage.base import BaseStorage
from ...storage.error import StorageError, StorageNotFoundError
from ...storage.record import StorageRecord
from ...wallet.base import BaseWallet, DIDInfo
from ...wallet.error import WalletError, WalletNotFoundError
from ...wallet.util import bytes_to_b64

from ..util import send_webhook, time_now

from von_anchor.a2a import DIDDoc
from von_anchor.a2a.publickey import PublicKey, PublicKeyType
from von_anchor.a2a.service import Service


class ConnectionManagerError(BaseError):
    """Connection error."""


class ConnectionManager:
    """Class for managing connections."""

    RECORD_TYPE_DID_DOC = "did_doc"
    RECORD_TYPE_DID_KEY = "did_key"

    def __init__(self, context: RequestContext):
        """
        Initialize a ConnectionManager.

        Args:
            context: The context for this connection
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    def _log_state(self, msg: str, params: dict = None):
        """Print a message with increased visibility (for testing)."""
        print(f"{msg}")
        if params:
            for k, v in params.items():
                print(f"    {k}: {v}")
        print()

    @property
    def context(self) -> RequestContext:
        """
        Accessor for the current request context.

        Returns:
            The request context for this connection

        """
        return self._context

    async def create_invitation(
        self,
        my_label: str = None,
        my_endpoint: str = None,
        their_role: str = None,
        my_router_did: str = None,
    ) -> Tuple[ConnectionRecord, ConnectionInvitation]:
        """
        Generate new connection invitation.

        This interaction represents an out-of-band communication channel. In the future
        and in practice, these sort of invitations will be received over any number of
        channels such as SMS, Email, QR Code, NFC, etc.

        Structure of an invite message:
        ```json
        {
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation",
            "label": "Alice",
            "did": "did:sov:QmWbsNYhMrjHiqZDTUTEJs"
        }```

        Or, in the case of a peer DID:
        ```json
        {
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/connections/1.0/invitation",
            "label": "Alice",
            "did": "did:peer:oiSqsNYhMrjHiqZDTUthsw",
            "recipientKeys": ["8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"],
            "serviceEndpoint": "https://example.com/endpoint"
        }```

        Currently, only peer DID is supported.

        Args:
            label: Label for this connection
            my_endpoint: Endpoint where other party can reach me
            seed: Seed for key
            metadata: Metadata for key

        Returns:
            A tuple of the new `ConnectionRecord` and `ConnectionInvitation` instances

        """
        self._log_state("Creating invitation")

        if not my_endpoint:
            my_endpoint = self.context.default_endpoint
        if not my_label:
            my_label = self.context.default_label

        # Create and store new invitation key
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        connection_key = await wallet.create_signing_key()

        # Create connection record
        connection = ConnectionRecord(
            my_router_did=my_router_did,
            initiator=ConnectionRecord.INITIATOR_SELF,
            invitation_key=connection_key.verkey,
            their_role=their_role,
            state=ConnectionRecord.STATE_INVITATION,
            routing_state=ConnectionRecord.ROUTING_STATE_REQUIRED
            if my_router_did
            else ConnectionRecord.ROUTING_STATE_NONE,
        )

        await connection.save(self.context)
        asyncio.ensure_future(send_webhook("connections", connection.serialize()))

        self._log_state(
            "Created new connection record",
            {"id": connection.connection_id, "state": connection.state},
        )

        # Create connection invitation message
        # Note: routing keys would need to be filled in later
        invitation = ConnectionInvitation(
            label=my_label, recipient_keys=[connection_key.verkey], endpoint=my_endpoint
        )
        await connection.attach_invitation(self.context, invitation)

        await connection.log_activity(
            self.context, "invitation", connection.DIRECTION_SENT,
        )

        return connection, invitation

    async def send_invitation(self, invitation: ConnectionInvitation, endpoint: str):
        """
        Deliver an invitation to an HTTP endpoint.

        Args:
            invitation: The `ConnectionInvitation` to send
            endpoint: Endpoint to send this invitation to
        """
        self._log_state("Sending invitation", {"endpoint": endpoint})
        invite_json = invitation.to_json()
        invite_b64 = bytes_to_b64(invite_json.encode("ascii"), urlsafe=True)
        async with aiohttp.ClientSession() as session:
            await session.get(endpoint, params={"invite": invite_b64})

    async def receive_invitation(
        self,
        invitation: ConnectionInvitation,
        their_role: str = None,
        my_router_did: str = None,
    ) -> ConnectionRecord:
        """
        Create a new connection record to track a received invitation.

        Args:
            invitation: The `ConnectionInvitation` to store
            their_role: The role assigned to this connection
            my_router_did: The DID of the router connection to use

        Returns:
            The new `ConnectionRecord` instance

        """
        self._log_state(
            "Receiving invitation", {"invitation": invitation, "role": their_role}
        )

        # TODO: validate invitation (must have recipient keys, endpoint)

        # Create connection record
        connection = ConnectionRecord(
            my_router_did=my_router_did,
            initiator=ConnectionRecord.INITIATOR_EXTERNAL,
            invitation_key=invitation.recipient_keys[0],
            their_label=invitation.label,
            their_role=their_role,
            state=ConnectionRecord.STATE_INVITATION,
            routing_state=ConnectionRecord.ROUTING_STATE_REQUIRED
            if my_router_did
            else ConnectionRecord.ROUTING_STATE_NONE,
        )

        await connection.save(self.context)
        asyncio.ensure_future(send_webhook("connections", connection.serialize()))

        self._log_state(
            "Created new connection record",
            {
                "id": connection.connection_id,
                "routing_state": connection.routing_state,
                "state": connection.state,
            },
        )

        # Save the invitation for later processing
        await connection.attach_invitation(self.context, invitation)

        await connection.log_activity(
            self.context, "invitation", connection.DIRECTION_RECEIVED,
        )

        return connection

    async def create_request(
        self,
        connection: ConnectionRecord,
        my_label: str = None,
        my_endpoint: str = None,
    ) -> ConnectionRequest:
        """
        Create a new connection request for a previously-received invitation.

        Args:
            connection: The `ConnectionRecord` representing the invitation to accept
            my_label: My label
            my_endpoint: My endpoint

        Returns:
            A new `ConnectionRequest` message to send to the other agent

        """
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        if connection.my_did:
            my_info = await wallet.get_local_did(connection.my_did)
        else:
            # Create new DID for connection
            my_info = await wallet.create_local_did()
            connection.my_did = my_info.did

        # Create connection request message
        did_doc = await self.create_did_document(my_info, connection.my_router_did)
        if not my_label:
            my_label = self.context.default_label
        request = ConnectionRequest(
            label=my_label,
            connection=ConnectionDetail(did=connection.my_did, did_doc=did_doc),
        )

        # Update connection state
        connection.request_id = request._id
        connection.state = ConnectionRecord.STATE_REQUEST

        await connection.save(self.context)
        asyncio.ensure_future(send_webhook("connections", connection.serialize()))
        self._log_state("Updated connection state", {"connection": connection})

        await connection.log_activity(
            self.context, "request", connection.DIRECTION_SENT,
        )

        return request

    async def receive_request(self, request: ConnectionRequest) -> ConnectionRecord:
        """
        Receive and store a connection request.

        Args:
            request: The `ConnectionRequest` to accept

        Returns:
            The new or updated `ConnectionRecord` instance

        """
        self._log_state("Receiving connection request", {"request": request})

        connection = None
        connection_key = None

        # Determine what key will need to sign the response
        if self.context.message_delivery.recipient_did_public:
            wallet: BaseWallet = await self.context.inject(BaseWallet)
            my_info = await wallet.get_local_did(
                self.context.recipient_did
            )
            connection_key = my_info.verkey
        else:
            connection_key = self.context.message_delivery.recipient_verkey
            try:
                connection = await ConnectionRecord.retrieve_by_invitation_key(
                    self.context,
                    connection_key,
                    ConnectionRecord.INITIATOR_SELF,
                )
            except StorageNotFoundError:
                raise ConnectionManagerError(
                    "No invitation found for pairwise connection"
                )

        invitation = None
        if connection:
            invitation = await connection.retrieve_invitation(self.context)
            connection_key = connection.invitation_key
            self._log_state("Found invitation", {"invitation": invitation})

        conn_did_doc = request.connection.did_doc
        if request.connection.did != conn_did_doc.did:
            raise ConnectionManagerError("Connection DID does not match DIDDoc id")
        await self.store_did_document(conn_did_doc)

        if connection:
            connection.their_label = request.label
            connection.their_did = request.connection.did
            connection.state = ConnectionRecord.STATE_REQUEST

            await connection.save(self.context)
            asyncio.ensure_future(send_webhook("connections", connection.serialize()))
            self._log_state("Updated connection state", {"connection": connection})
        else:
            connection = ConnectionRecord(
                my_router_did=None,
                initiator=ConnectionRecord.INITIATOR_EXTERNAL,
                invitation_key=connection_key,
                their_label=request.label,
                state=ConnectionRecord.STATE_REQUEST,
                routing_state=ConnectionRecord.ROUTING_STATE_NONE,
            )

            await connection.save(self.context)
            asyncio.ensure_future(send_webhook("connections", connection.serialize()))

            self._log_state(
                "Created new connection record",
                {
                    "id": connection.connection_id,
                    "routing_state": connection.routing_state,
                    "state": connection.state,
                },
            )

        # Attach the connection request so it can be found and responded to
        await connection.attach_request(self.context, request)

        await connection.log_activity(
            self.context, "request", connection.DIRECTION_RECEIVED,
        )

        return connection

    async def create_response(
        self,
        connection: ConnectionRecord,
        my_endpoint: str = None,
        my_router_did: str = None,
        their_role: str = None,
    ) -> ConnectionResponse:
        """
        Create a connection response for a received connection request.

        Args:
            connection: The `ConnectionRecord` with a pending connection request
            my_endpoint: The endpoint I can be reached at
            my_router_did: The DID of my router connection to use
            their_role: The role to assign to this connection

        Returns:
            A tuple of the updated `ConnectionRecord` new `ConnectionResponse` message

        """
        self._log_state(
            "Creating connection response", {"connection_id": connection.connection_id}
        )

        if connection.state not in (
            connection.STATE_REQUEST,
            connection.STATE_RESPONSE,
        ):
            raise ConnectionManagerError(
                "Connection is not in the request or response state"
            )

        request = await connection.retrieve_request(self.context)
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        if connection.my_did:
            my_info = await wallet.get_local_did(connection.my_did)
        else:
            my_info = await wallet.create_local_did()
            connection.my_did = my_info.did

        if my_router_did:
            connection.my_router_did = my_router_did
            connection.routing_state = ConnectionRecord.ROUTING_STATE_REQUIRED
        if their_role:
            connection.their_role = their_role

        if not my_endpoint:
            my_endpoint = self.context.default_endpoint

        # Create connection response message
        did_doc = await self.create_did_document(
            my_info, connection.my_router_did, my_endpoint
        )
        response = ConnectionResponse(
            connection=ConnectionDetail(did=my_info.did, did_doc=did_doc)
        )
        # Assign thread information
        response.assign_thread_from(request)
        # Sign connection field using the invitation key
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await response.sign_field(
            "connection", connection.invitation_key, wallet
        )
        self._log_state(
            "Created connection response",
            {
                "my_did": my_info.did,
                "their_did": connection.their_did,
                "response": response,
            },
        )

        # Update connection state
        connection.state = ConnectionRecord.STATE_RESPONSE

        await connection.save(self.context)
        asyncio.ensure_future(send_webhook("connections", connection.serialize()))
        self._log_state("Updated connection state", {"connection": connection})

        await connection.log_activity(
            self.context, "response", connection.DIRECTION_SENT,
        )

        return response

    async def accept_response(self, response: ConnectionResponse) -> ConnectionRecord:
        """
        Accept a connection response.

        Process a ConnectionResponse message by looking up
        the connection request and setting up the pairwise connection.

        Args:
            response: The `ConnectionResponse` to accept

        Returns:
            The updated `ConnectionRecord` representing the connection

        Raises:
            ConnectionManagerError: If there is no DID associated with the
                connection response
            ConnectionManagerError: If the corresponding connection is not
                at the request or response stage

        """

        connection = None
        if response._thread:
            # identify the request by the thread ID
            request_id = response._thread_id
            try:
                connection = await ConnectionRecord.retrieve_by_request_id(
                    self.context, request_id
                )
            except StorageNotFoundError:
                pass

        if not connection:
            # identify connection by the DID they used for us
            try:
                connection = await ConnectionRecord.retrieve_by_did(
                    self.context,
                    self.context.message_delivery.sender_did,
                    self.context.message_delivery.recipient_did,
                )
            except StorageNotFoundError:
                pass

        if not connection:
            raise ConnectionManagerError(
                "No connection associated with connection response"
            )

        if connection.state not in (
            ConnectionRecord.STATE_REQUEST,
            ConnectionRecord.STATE_RESPONSE,
        ):
            raise ConnectionManagerError(
                f"Cannot accept connection response for connection"
                " in state: {connection.state}"
            )

        their_did = response.connection.did
        conn_did_doc = response.connection.did_doc
        if their_did != conn_did_doc.did:
            raise ConnectionManagerError("Connection DID does not match DIDDoc id")
        await self.store_did_document(conn_did_doc)

        connection.their_did = their_did
        connection.state = ConnectionRecord.STATE_RESPONSE

        await connection.save(self.context)
        asyncio.ensure_future(send_webhook("connections", connection.serialize()))

        await connection.log_activity(
            self.context, "response", connection.DIRECTION_RECEIVED,
        )

        return connection

    async def find_connection(
        self,
        their_did: str,
        my_did: str = None,
        my_verkey: str = None,
        auto_complete=False,
    ) -> ConnectionRecord:
        """
        Look up existing connection information for a sender verkey.

        Args:
            their_did: Their DID
            my_did: My DID
            my_verkey: My verkey
            auto_complete: Should this connection automatically be promoted to active

        Returns:
            The found `ConnectionRecord`

        """
        # self._log_state(
        #    "Finding connection",
        #    {"their_did": their_did, "my_did": my_did, "my_verkey": my_verkey},
        # )
        connection = None
        if their_did:
            try:
                connection = await ConnectionRecord.retrieve_by_did(
                    self.context, their_did, my_did
                )
            except StorageNotFoundError:
                pass

        if (
            connection
            and connection.state == ConnectionRecord.STATE_RESPONSE
            and auto_complete
        ):
            connection.state = ConnectionRecord.STATE_ACTIVE

            await connection.save(self.context)
            asyncio.ensure_future(send_webhook("connections", connection.serialize()))
            self._log_state("Connection promoted to active", {"connection": connection})
        elif connection and connection.state == ConnectionRecord.STATE_INACTIVE:
            connection.state = ConnectionRecord.STATE_ACTIVE
            await connection.save(self.context)
            asyncio.ensure_future(send_webhook("connections", connection.serialize()))

            self._log_state("Connection restored to active", {"connection": connection})

        if not connection and my_verkey:
            try:
                connection = await ConnectionRecord.retrieve_by_invitation_key(
                    self.context, my_verkey, ConnectionRecord.INITIATOR_SELF
                )
            except StorageError:
                pass

        return connection

    async def expand_message(
        self,
        message_body: Union[str, bytes],
        transport_type: str,
        allow_direct_response: bool = False,
    ) -> RequestContext:
        """
        Deserialize an incoming message and further populate the request context.

        Args:
            message_body: The body of the message
            transport_type: The transport the message was received on
            allow_direct_response: Whether direct responses are supported

        Returns:
            The `RequestContext` of the expanded message

        Raises:
            MessageParseError: If there is no message factory defined
            MessageParseError: If there is no wallet defined
            MessageParseError: If the JSON parsing failed

        """
        context = self.context.start_scope("message")

        try:
            message_factory: MessageFactory = await context.inject(MessageFactory)
        except InjectorError:
            raise MessageParseError("Message factory not defined")

        try:
            wallet: BaseWallet = await context.inject(BaseWallet)
        except InjectorError:
            raise MessageParseError("Wallet not defined")

        message_dict = None
        message_json = message_body
        from_verkey = None
        to_verkey = None

        try:
            message_dict = json.loads(message_json)
        except ValueError:
            raise MessageParseError("Message JSON parsing failed")

        if "@type" not in message_dict:
            try:
                unpacked = await wallet.unpack_message(message_body)
                message_json, from_verkey, to_verkey = unpacked
            except WalletError:
                self._logger.debug("Message unpack failed, falling back to JSON")
            else:
                try:
                    message_dict = json.loads(message_json)
                except ValueError:
                    raise MessageParseError("Message JSON parsing failed")

        self._logger.debug(f"Expanded message: {message_dict}")

        context.message = message_factory.make_message(message_dict)
        delivery = MessageDelivery()
        delivery.in_time = time_now()
        delivery.transport_type = transport_type

        # handle transport decorator
        transport_dec = context.message._transport
        if transport_dec and transport_dec.return_route == "all":
            if allow_direct_response:
                delivery.direct_response = True
            else:
                self._logger.warning(
                    "Direct response requested, but not supported by transport %s",
                    transport_type
                )

        if from_verkey and to_verkey:
            # must be a packed message for from_verkey and to_verkey to be populated
            delivery.recipient_verkey = to_verkey
            delivery.sender_verkey = from_verkey
            try:
                delivery.sender_did = await self.find_did_for_key(from_verkey)
            except StorageNotFoundError:
                pass

            try:
                my_info = await wallet.get_local_did_for_verkey(to_verkey)
                delivery.recipient_did = my_info.did
                if "public" in my_info.metadata and my_info.metadata["public"] is True:
                    delivery.recipient_did_public = True

            except WalletNotFoundError:
                pass

            connection = await self.find_connection(
                delivery.sender_did, delivery.recipient_did, to_verkey, True
            )
            if connection:
                self._log_state("Found connection", {"connection": connection})
                context.connection_active = (
                    connection.state == ConnectionRecord.STATE_ACTIVE
                )
                context.connection_record = connection
                context.connection_target = await self.get_connection_target(
                    connection)
                if transport_dec and transport_dec.return_route:
                    save_conn = False
                    if transport_dec.return_route == "all":
                        if not connection.direct_response:
                            connection.direct_response = "all"
                            save_conn = True
                    elif transport_dec.return_route == "none":
                        if connection.direct_response:
                            connection.direct_response = None
                            save_conn = True
                    else:
                        self._logger.warning(
                            "Unsupported transport return route: %s",
                            transport_dec.return_route)
                    if save_conn:
                        await connection.save(context)
                if not transport_dec or not transport_dec.return_route:
                    if allow_direct_response and connection.direct_response:
                        delivery.direct_response = True

        context.message_delivery = delivery

        # look up thread information?

        # handle any other decorators having special behaviour (timing, trace, etc)

        return context

    async def compact_message(
        self, message: Union[AgentMessage, str, bytes], target: ConnectionTarget
    ) -> Union[str, bytes]:
        """
        Serialize an outgoing message for transport.

        Args:
            message: The `AgentMessage` to compact, or a pre-packed string or bytes
            target: The `ConnectionTarget` you are compacting for

        Returns:
            The compacted message

        """

        wallet: BaseWallet = await self.context.inject(BaseWallet)

        if isinstance(message, AgentMessage):
            message_json = message.to_json()
            if target and target.sender_key and target.recipient_keys:
                message = await wallet.pack_message(
                    message_json, target.recipient_keys, target.sender_key
                )
                if target.routing_keys:
                    recip_keys = target.recipient_keys
                    for router_key in target.routing_keys:
                        fwd_msg = Forward(to=recip_keys[0], msg=message)
                        # Forwards are anon packed
                        recip_keys = [router_key]
                        message = await wallet.pack_message(
                            fwd_msg.to_json(), recip_keys
                        )
            else:
                message = message_json
        return message

    async def create_did_document(
        self, my_info: DIDInfo, my_router_did: str = None, my_endpoint: str = None
    ) -> DIDDoc:
        """Create our DID document for a given DID.

        Args:
            my_info: The DID I am using in this connection
            my_router_did: The DID of the router connection to use
            my_endpoint: A custom endpoint for the DID Document

        Returns:
            The prepared `DIDDoc` instance

        """

        did_doc = DIDDoc(did=my_info.did)
        did_controller = my_info.did
        did_key = my_info.verkey
        pk = PublicKey(
            my_info.did,
            "1",
            PublicKeyType.ED25519_SIG_2018,
            did_controller,
            did_key,
            True,
        )
        did_doc.verkeys.append(pk)

        if not my_endpoint:
            my_endpoint = self.context.default_endpoint
        service = Service(my_info.did, "indy", "IndyAgent", [did_key], [], my_endpoint)
        did_doc.services.append(service)

        return did_doc

    async def fetch_did_document(self, did: str) -> DIDDoc:
        """Retrieve a DID Document for a given DID.

        Args:
            did: The DID to search for
        """
        storage: BaseStorage = await self.context.inject(BaseStorage)
        record = await storage.search_records(
            self.RECORD_TYPE_DID_DOC, {"did": did}
        ).fetch_single()
        return DIDDoc.from_json(record.value)

    async def store_did_document(self, did_doc: DIDDoc):
        """Store a DID document.

        Args:
            did_doc: The `DIDDoc` instance to be persisted
        """
        assert did_doc.did
        storage: BaseStorage = await self.context.inject(BaseStorage)
        try:
            record = await self.fetch_did_document(did_doc.did)
        except StorageNotFoundError:
            record = StorageRecord(
                self.RECORD_TYPE_DID_DOC, did_doc.to_json(), {"did": did_doc.did}
            )
            await storage.add_record(record)
        else:
            await storage.update_record_value(record, did_doc.value)
        await self.remove_keys_for_did(did_doc.did)
        for key in did_doc.verkeys:
            if key.controller == did_doc.did:
                await self.add_key_for_did(did_doc.did, key.value)

    async def add_key_for_did(self, did: str, key: str):
        """Store a verkey for lookup against a DID.

        Args:
            did: The DID to associate with this key
            key: The verkey to be added
        """
        record = StorageRecord(self.RECORD_TYPE_DID_KEY, key, {"did": did, "key": key})
        storage: BaseStorage = await self.context.inject(BaseStorage)
        await storage.add_record(record)

    async def find_did_for_key(self, key: str) -> str:
        """Find the DID previously associated with a key.

        Args:
            key: The verkey to look up
        """
        storage: BaseStorage = await self.context.inject(BaseStorage)
        record = await storage.search_records(
            self.RECORD_TYPE_DID_KEY, {"key": key}
        ).fetch_single()
        return record.tags["did"]

    async def remove_keys_for_did(self, did: str):
        """Remove all keys associated with a DID.

        Args:
            did: The DID to remove keys for
        """
        storage: BaseStorage = await self.context.inject(BaseStorage)
        keys = await storage.search_records(
            self.RECORD_TYPE_DID_KEY, {"did": did}
        ).fetch_all()
        for record in keys:
            await storage.delete_record(record)

    async def get_connection_target(
        self, connection: ConnectionRecord
    ) -> ConnectionTarget:
        """Create a connection target from a `ConnectionRecord`.

        Args:
            connection: The connection record (with associated `DIDDoc`)
                used to generate the connection target
        """
        if not connection.my_did:
            self._logger.debug("No local DID associated with connection")
            return None

        wallet: BaseWallet = await self.context.inject(BaseWallet)
        my_info = await wallet.get_local_did(connection.my_did)

        if (
            connection.state in (connection.STATE_INVITATION, connection.STATE_REQUEST)
            and connection.initiator == connection.INITIATOR_EXTERNAL
        ):
            invitation = await connection.retrieve_invitation(self.context)
            return ConnectionTarget(
                did=connection.their_did,
                endpoint=invitation.endpoint,
                label=invitation.label,
                recipient_keys=invitation.recipient_keys,
                routing_keys=invitation.routing_keys,
                sender_key=my_info.verkey,
            )

        if not connection.their_did:
            self._logger.debug("No target DID associated with connection")
            return None

        doc = await self.fetch_did_document(connection.their_did)
        if not doc.services:
            raise ConnectionManagerError("No services defined by DIDDoc")

        service = doc.services[0]
        return ConnectionTarget(
            did=doc.did,
            endpoint=service.endpoint,
            label=connection.their_label,
            recipient_keys=service.recip_keys,
            routing_keys=service.routing_keys,
            sender_key=my_info.verkey,
        )
