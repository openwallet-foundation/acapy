"""Classes to manage connections."""

import logging
import sys

from typing import Tuple

from ...cache.base import BaseCache
from ...error import BaseError
from ...config.base import InjectorError
from ...config.injection_context import InjectionContext
from ...storage.base import BaseStorage
from ...storage.error import StorageError, StorageNotFoundError
from ...storage.record import StorageRecord
from ...wallet.base import BaseWallet, DIDInfo
from ...wallet.error import WalletNotFoundError

from ..message_delivery import MessageDelivery
from ..responder import BaseResponder
from ..routing.manager import RoutingManager

from .messages.connection_invitation import ConnectionInvitation
from .messages.connection_request import ConnectionRequest
from .messages.connection_response import ConnectionResponse
from .messages.problem_report import ProblemReportReason
from .models.connection_detail import ConnectionDetail
from .models.connection_record import ConnectionRecord
from .models.connection_target import ConnectionTarget
from .models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service


class ConnectionManagerError(BaseError):
    """Connection error."""


class ConnectionManager:
    """Class for managing connections."""

    RECORD_TYPE_DID_DOC = "did_doc"
    RECORD_TYPE_DID_KEY = "did_key"

    def __init__(self, context: InjectionContext):
        """
        Initialize a ConnectionManager.

        Args:
            context: The context for this connection manager
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    def _log_state(self, msg: str, params: dict = None):
        """Print a message with increased visibility (for testing)."""
        if self._context.settings.get("debug.connections"):
            print(msg, file=sys.stderr)
            if params:
                for k, v in params.items():
                    print(f"    {k}: {v}", file=sys.stderr)
            print(file=sys.stderr)

    @property
    def context(self) -> InjectionContext:
        """
        Accessor for the current injection context.

        Returns:
            The injection context for this connection manager

        """
        return self._context

    async def create_invitation(
        self,
        my_label: str = None,
        my_endpoint: str = None,
        their_role: str = None,
        accept: str = None,
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
            my_label: label for this connection
            my_endpoint: endpoint where other party can reach me
            their_role: a role to assign the connection
            accept: set to 'auto' to auto-accept a corresponding connection request

        Returns:
            A tuple of the new `ConnectionRecord` and `ConnectionInvitation` instances

        """
        self._log_state("Creating invitation")

        if not my_endpoint:
            my_endpoint = self.context.settings.get("default_endpoint")
        if not my_label:
            my_label = self.context.settings.get("default_label")
        if not accept and self.context.settings.get("accept_requests"):
            accept = ConnectionRecord.ACCEPT_AUTO

        # Create and store new invitation key
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        connection_key = await wallet.create_signing_key()

        # Create connection record
        connection = ConnectionRecord(
            initiator=ConnectionRecord.INITIATOR_SELF,
            invitation_key=connection_key.verkey,
            their_role=their_role,
            state=ConnectionRecord.STATE_INVITATION,
            accept=accept,
        )

        await connection.save(self.context)
        await self.updated_record(connection)

        self._log_state(
            "Created new connection record",
            {"id": connection.connection_id, "state": connection.state},
        )

        # Create connection invitation message
        # Note: Need to split this into two stages to support inbound routing of invites
        # Would want to reuse create_did_document and convert the result
        invitation = ConnectionInvitation(
            label=my_label, recipient_keys=[connection_key.verkey], endpoint=my_endpoint
        )
        await connection.attach_invitation(self.context, invitation)

        await connection.log_activity(
            self.context, "invitation", connection.DIRECTION_SENT
        )

        return connection, invitation

    async def receive_invitation(
        self,
        invitation: ConnectionInvitation,
        their_role: str = None,
        accept: str = None,
    ) -> ConnectionRecord:
        """
        Create a new connection record to track a received invitation.

        Args:
            invitation: The `ConnectionInvitation` to store
            their_role: The role assigned to this connection
            accept: set to 'auto' to auto-accept the invitation

        Returns:
            The new `ConnectionRecord` instance

        """
        self._log_state(
            "Receiving invitation", {"invitation": invitation, "role": their_role}
        )

        # TODO: validate invitation (must have recipient keys, endpoint)

        if accept is None and self.context.settings.get("accept_invites"):
            accept = ConnectionRecord.ACCEPT_AUTO

        # Create connection record
        connection = ConnectionRecord(
            initiator=ConnectionRecord.INITIATOR_EXTERNAL,
            invitation_key=invitation.recipient_keys[0],
            their_label=invitation.label,
            their_role=their_role,
            state=ConnectionRecord.STATE_INVITATION,
            accept=accept,
        )

        await connection.save(self.context)
        await self.updated_record(connection)

        self._log_state(
            "Created new connection record",
            {"id": connection.connection_id, "state": connection.state},
        )

        # Save the invitation for later processing
        await connection.attach_invitation(self.context, invitation)

        await connection.log_activity(
            self.context, "invitation", connection.DIRECTION_RECEIVED
        )

        if connection.accept == connection.ACCEPT_AUTO:
            request = await self.create_request(connection)
            responder: BaseResponder = await self._context.inject(
                BaseResponder, required=False
            )
            if responder:
                await responder.send(request, connection_id=connection.connection_id)
                # refetch connection for accurate state
                connection = await ConnectionRecord.retrieve_by_id(
                    self._context, connection.connection_id
                )
        else:
            self._logger.debug("Connection invitation will await acceptance")

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
        did_doc = await self.create_did_document(
            my_info, connection.inbound_connection_id
        )
        if not my_label:
            my_label = self.context.settings.get("default_label")
        request = ConnectionRequest(
            label=my_label,
            connection=ConnectionDetail(did=connection.my_did, did_doc=did_doc),
        )

        # Update connection state
        connection.request_id = request._id
        connection.state = ConnectionRecord.STATE_REQUEST

        await connection.save(self.context)
        await self.updated_record(connection)
        self._log_state("Updated connection state", {"connection": connection})

        await connection.log_activity(
            self.context, "request", connection.DIRECTION_SENT
        )

        return request

    async def receive_request(
        self, request: ConnectionRequest, delivery: MessageDelivery
    ) -> ConnectionRecord:
        """
        Receive and store a connection request.

        Args:
            request: The `ConnectionRequest` to accept
            delivery: The message delivery metadata

        Returns:
            The new or updated `ConnectionRecord` instance

        """
        self._log_state("Receiving connection request", {"request": request})

        connection = None
        connection_key = None

        # Determine what key will need to sign the response
        if delivery.recipient_did_public:
            wallet: BaseWallet = await self.context.inject(BaseWallet)
            my_info = await wallet.get_local_did(self.context.recipient_did)
            connection_key = my_info.verkey
        else:
            connection_key = delivery.recipient_verkey
            try:
                connection = await ConnectionRecord.retrieve_by_invitation_key(
                    self.context, connection_key, ConnectionRecord.INITIATOR_SELF
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
            connection.state = ConnectionRecord.STATE_REQUEST

            await connection.save(self.context)
            await self.updated_record(connection)
            self._log_state("Updated connection state", {"connection": connection})
        else:
            connection = ConnectionRecord(
                initiator=ConnectionRecord.INITIATOR_EXTERNAL,
                invitation_key=connection_key,
                their_label=request.label,
                state=ConnectionRecord.STATE_REQUEST,
            )

            await connection.save(self.context)
            await self.updated_record(connection)

            self._log_state(
                "Created new connection record",
                {"id": connection.connection_id, "state": connection.state},
            )

        # Attach the connection request so it can be found and responded to
        await connection.attach_request(self.context, request)

        await connection.log_activity(
            self.context, "request", connection.DIRECTION_RECEIVED
        )

        if connection.accept == ConnectionRecord.ACCEPT_AUTO:
            response = await self.create_response(connection)
            responder: BaseResponder = await self._context.inject(
                BaseResponder, required=False
            )
            if responder:
                await responder.send(response, connection_id=connection.connection_id)
                # refetch connection for accurate state
                connection = await ConnectionRecord.retrieve_by_id(
                    self._context, connection.connection_id
                )
        else:
            self._logger.debug("Connection request will await acceptance")

        return connection

    async def create_response(
        self, connection: ConnectionRecord, my_endpoint: str = None
    ) -> ConnectionResponse:
        """
        Create a connection response for a received connection request.

        Args:
            connection: The `ConnectionRecord` with a pending connection request
            my_endpoint: The endpoint I can be reached at

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

        # Create connection response message
        did_doc = await self.create_did_document(
            my_info, connection.inbound_connection_id, my_endpoint
        )
        response = ConnectionResponse(
            connection=ConnectionDetail(did=my_info.did, did_doc=did_doc)
        )
        # Assign thread information
        response.assign_thread_from(request)
        # Sign connection field using the invitation key
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        await response.sign_field("connection", connection.invitation_key, wallet)
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
        await self.updated_record(connection)
        self._log_state("Updated connection state", {"connection": connection})

        await connection.log_activity(
            self.context, "response", connection.DIRECTION_SENT
        )

        return response

    async def accept_response(
        self, response: ConnectionResponse, delivery: MessageDelivery
    ) -> ConnectionRecord:
        """
        Accept a connection response.

        Process a ConnectionResponse message by looking up
        the connection request and setting up the pairwise connection.

        Args:
            response: The `ConnectionResponse` to accept
            delivery: The message delivery metadata

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
            try:
                connection = await ConnectionRecord.retrieve_by_request_id(
                    self.context, response._thread_id
                )
            except StorageNotFoundError:
                pass

        if not connection and delivery.sender_did:
            # identify connection by the DID they used for us
            try:
                connection = await ConnectionRecord.retrieve_by_did(
                    self.context, delivery.sender_did, delivery.recipient_did
                )
            except StorageNotFoundError:
                pass

        if not connection:
            raise ConnectionManagerError(
                "No corresponding connection request found",
                error_code=ProblemReportReason.RESPONSE_FOR_UNKNOWN_REQUEST.value,
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
        if not conn_did_doc:
            raise ConnectionManagerError(
                "No DIDDoc provided; cannot connect to public DID"
            )
        if their_did != conn_did_doc.did:
            raise ConnectionManagerError("Connection DID does not match DIDDoc id")
        await self.store_did_document(conn_did_doc)

        connection.their_did = their_did
        connection.state = ConnectionRecord.STATE_RESPONSE

        await connection.save(self.context)
        await self.updated_record(connection)

        await connection.log_activity(
            self.context, "response", connection.DIRECTION_RECEIVED
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
            The located `ConnectionRecord`, if any

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
            await self.updated_record(connection)
            self._log_state("Connection promoted to active", {"connection": connection})
        elif connection and connection.state == ConnectionRecord.STATE_INACTIVE:
            connection.state = ConnectionRecord.STATE_ACTIVE
            await connection.save(self.context)
            await self.updated_record(connection)

            self._log_state("Connection restored to active", {"connection": connection})

        if not connection and my_verkey:
            try:
                connection = await ConnectionRecord.retrieve_by_invitation_key(
                    self.context, my_verkey, ConnectionRecord.INITIATOR_SELF
                )
            except StorageError:
                pass

        return connection

    async def find_message_connection(
        self, delivery: MessageDelivery
    ) -> ConnectionRecord:
        """
        Deserialize an incoming message and further populate the request context.

        Args:
            delivery: The message delivery details

        Returns:
            The `ConnectionRecord` associated with the expanded message, if any

        """

        if delivery.sender_verkey:
            try:
                delivery.sender_did = await self.find_did_for_key(
                    delivery.sender_verkey
                )
            except StorageNotFoundError:
                self._logger.warning(
                    "No corresponding DID found for sender verkey: %s",
                    delivery.sender_verkey,
                )

        if delivery.recipient_verkey:
            try:
                wallet: BaseWallet = await self.context.inject(BaseWallet)
                my_info = await wallet.get_local_did_for_verkey(
                    delivery.recipient_verkey
                )
                delivery.recipient_did = my_info.did
                if "public" in my_info.metadata and my_info.metadata["public"] is True:
                    delivery.recipient_did_public = True
            except InjectorError:
                self._logger.warning(
                    "Cannot resolve recipient verkey, no wallet defined by context: %s",
                    delivery.recipient_verkey,
                )
            except WalletNotFoundError:
                self._logger.warning(
                    "No corresponding DID found for recipient verkey: %s",
                    delivery.recipient_verkey,
                )

        connection = await self.find_connection(
            delivery.sender_did, delivery.recipient_did, delivery.recipient_verkey, True
        )
        # if connection:
        #     self._log_state("Found connection", {"connection": connection})

        return connection

    async def create_did_document(
        self,
        my_info: DIDInfo,
        inbound_connection_id: str = None,
        my_endpoint: str = None,
    ) -> DIDDoc:
        """Create our DID document for a given DID.

        Args:
            my_info: The DID I am using in this connection
            inbound_connection_id: The DID of the inbound routing connection to use
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
            router = await ConnectionRecord.retrieve_by_id(self.context, router_id)
            if router.state != ConnectionRecord.STATE_ACTIVE:
                raise ConnectionManagerError(
                    f"Router connection not active: {router_id}"
                )
            routing_doc = await self.fetch_did_document(router.their_did)
            if not routing_doc.service:
                raise ConnectionManagerError(
                    f"No services defined by routing DIDDoc: {router_id}"
                )
            for service in routing_doc.service.values():
                if not service.endpoint:
                    raise ConnectionManagerError(
                        "Routing DIDDoc service has no service endpoint"
                    )
                if not service.recip_keys:
                    raise ConnectionManagerError(
                        "Routing DIDDoc service has no recipient key(s)"
                    )
                rk = PublicKey(
                    my_info.did,
                    f"routing-{router_idx}",
                    service.recip_keys[0].value,
                    PublicKeyType.ED25519_SIG_2018,
                    did_controller,
                    True,
                )
                routing_keys.append(rk)
                my_endpoint = service.endpoint
                break
            router_id = router.inbound_connection_id

        if not my_endpoint:
            my_endpoint = self.context.settings.get("default_endpoint")
        service = Service(
            my_info.did, "indy", "IndyAgent", [pk], routing_keys, my_endpoint
        )
        did_doc.set(service)

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
        for key in did_doc.pubkey.values():
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

        cache: BaseCache = await self.context.inject(BaseCache, required=False)
        cache_key = f"connection_target::{connection.connection_id}"
        if cache:
            target_json = await cache.get(cache_key)
            if target_json:
                return ConnectionTarget.deserialize(target_json)

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
            result = ConnectionTarget(
                did=connection.their_did,
                endpoint=invitation.endpoint,
                label=invitation.label,
                recipient_keys=invitation.recipient_keys,
                routing_keys=invitation.routing_keys,
                sender_key=my_info.verkey,
            )
        else:
            if not connection.their_did:
                self._logger.debug("No target DID associated with connection")
                return None

            doc = await self.fetch_did_document(connection.their_did)
            result = self.diddoc_connection_target(
                doc, my_info.verkey, connection.their_label
            )

        if cache:
            await cache.set(cache_key, result.serialize(), 60)

        return result

    def diddoc_connection_target(
        self, doc: DIDDoc, sender_verkey: str, their_label: str = None
    ) -> ConnectionTarget:
        """Create a connection target from a DID Document.

        Args:
            doc: The DID Document to create the target from
            sender_verkey: The verkey we are using
            their_label: The connection label they are using
        """

        if not doc:
            raise ConnectionManagerError("No DIDDoc provided for connection target")
        if not doc.did:
            raise ConnectionManagerError("DIDDoc has no DID")
        if not doc.service:
            raise ConnectionManagerError("No services defined by DIDDoc")

        for service in doc.service.values():
            if not service.recip_keys:
                raise ConnectionManagerError("DIDDoc service has no recipient key(s)")
            if not service.endpoint:
                raise ConnectionManagerError("DIDDoc service has no service endpoint")

            return ConnectionTarget(
                did=doc.did,
                endpoint=service.endpoint,
                label=their_label,
                recipient_keys=[key.value for key in (service.recip_keys or ())],
                routing_keys=[key.value for key in (service.routing_keys or ())],
                sender_key=sender_verkey,
            )

    async def establish_inbound(
        self, connection: ConnectionRecord, inbound_connection_id: str, outbound_handler
    ) -> str:
        """Assign the inbound routing connection for a connection record.

        Returns: the current routing state (request or done)

        """

        # The connection must have a verkey, but in the case of a received
        # invitation we might not have created one yet
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        if connection.my_did:
            my_info = await wallet.get_local_did(connection.my_did)
        else:
            # Create new DID for connection
            my_info = await wallet.create_local_did()
            connection.my_did = my_info.did

        try:
            router = await ConnectionRecord.retrieve_by_id(
                self.context, inbound_connection_id
            )
        except StorageNotFoundError:
            raise ConnectionManagerError(
                f"Routing connection not found: {inbound_connection_id}"
            )
        if not router.is_ready:
            raise ConnectionManagerError(
                f"Routing connection is not ready: {inbound_connection_id}"
            )
        connection.inbound_connection_id = inbound_connection_id

        route_mgr = RoutingManager(self.context)

        await route_mgr.send_create_route(
            inbound_connection_id, my_info.verkey, outbound_handler
        )
        connection.routing_state = ConnectionRecord.ROUTING_STATE_REQUEST
        await connection.save(self.context)
        await self.updated_record(connection)
        return connection.routing_state

    async def update_inbound(
        self, inbound_connection_id: str, recip_verkey: str, routing_state: str
    ):
        """Activate connections once a route has been established.

        Looks up pending connections associated with the inbound routing
        connection and marks the routing as complete.
        """
        conns = await ConnectionRecord.query(
            self.context, {"inbound_connection_id": inbound_connection_id}
        )
        wallet: BaseWallet = await self.context.inject(BaseWallet)

        for connection in conns:
            # check the recipient key
            if not connection.my_did:
                continue
            conn_info = await wallet.get_local_did(connection.my_did)
            if conn_info.verkey == recip_verkey:
                connection.routing_state = routing_state
                await connection.save(self.context)
                await self.updated_record(connection)

    async def log_activity(
        self,
        connection: ConnectionRecord,
        activity_type: str,
        direction: str,
        meta: dict = None,
    ):
        """Log activity against a connection record and send webhook."""
        await connection.log_activity(self._context, activity_type, direction, meta)
        await self.updated_activity(connection)

    async def updated_record(self, connection: ConnectionRecord):
        """Call webhook when the record is updated."""
        responder: BaseResponder = await self._context.inject(
            BaseResponder, required=False
        )
        if responder:
            await responder.send_webhook("connections", connection.serialize())
        cache: BaseCache = await self._context.inject(BaseCache, required=False)
        cache_key = f"connection_target::{connection.connection_id}"
        if cache:
            await cache.clear(cache_key)

    async def updated_activity(self, connection: ConnectionRecord):
        """Call webhook when the record activity is updated."""
        responder: BaseResponder = await self._context.inject(
            BaseResponder, required=False
        )
        if responder:
            activity = await connection.fetch_activity(self._context)
            await responder.send_webhook(
                "connections_activity",
                {"connection_id": connection.connection_id, "activity": activity},
            )
