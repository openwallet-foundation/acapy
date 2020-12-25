"""Classes to manage connection establishment under RFC 23 (DID exchange)."""

from aries_cloudagent.multitenant.manager import MultitenantManager
import json
import logging

from typing import Sequence, Tuple

from ....connections.models.conn_record import ConnRecord
from ....connections.models.connection_target import ConnectionTarget
from ....connections.models.diddoc import (
    DIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from ....core.error import BaseError
from ....core.profile import ProfileSession
from ....messaging.decorators.attach_decorator import AttachDecorator
from ....messaging.responder import BaseResponder
from ....storage.base import BaseStorage
from ....storage.error import StorageNotFoundError
from ....storage.record import StorageRecord
from ....transport.inbound.receipt import MessageReceipt
from ....wallet.base import BaseWallet, DIDInfo

from ...out_of_band.v1_0.messages.invitation import (
    InvitationMessage as OOBInvitationMessage,
)
from ...out_of_band.v1_0.models.invitation import (
    InvitationRecord as OOBInvitationRecord,
)

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

    def __init__(self, session: ProfileSession):
        """
        Initialize a DIDXManager.

        Args:
            session: The profile session for this did exchange manager
        """
        self._session = session
        self._logger = logging.getLogger(__name__)

    @property
    def session(self) -> ProfileSession:
        """
        Accessor for the current profile session.

        Returns:
            The profile session for this did exchange manager

        """
        return self._session

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
                    and self._session.settings.get("debug.auto_accept_invites")
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
            invitation_msg_id=invitation._id,
            their_label=invitation.label,
            their_role=ConnRecord.Role.RESPONDER.rfc23,
            state=ConnRecord.State.INVITATION.rfc23,
            accept=accept,
            alias=alias,
        )

        await conn_rec.save(
            self._session,
            reason="Created new connection record from invitation",
            log_params={
                "invitation": invitation,
                "their_role": ConnRecord.Role.RESPONDER.rfc23,
            },
        )

        # Save the invitation for later processing
        await conn_rec.attach_invitation(self._session, invitation)

        if conn_rec.accept == ConnRecord.ACCEPT_AUTO:
            request = await self.create_request(conn_rec)
            responder = self._session.inject(BaseResponder, required=False)
            if responder:
                await responder.send_reply(
                    request,
                    connection_id=conn_rec.connection_id,
                )

                conn_rec.state = ConnRecord.State.REQUEST.rfc23
                await conn_rec.save(self._session, reason="Sent connection request")
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
        wallet = self._session.inject(BaseWallet)
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
            default_endpoint = self._session.settings.get("default_endpoint")
            if default_endpoint:
                my_endpoints.append(default_endpoint)
            my_endpoints.extend(self._session.settings.get("additional_endpoints", []))
        did_doc = await self.create_did_document(
            my_info, conn_rec.inbound_connection_id, my_endpoints
        )
        invitation = await conn_rec.retrieve_invitation(self._session)
        if invitation.service_blocks:
            pthid = invitation._id  # explicit
        else:
            """# early try: keep around until logic in code is proven sound
            pthid = did_doc.service[[s for s in did_doc.service][0]].id
            """
            pthid = invitation.service_dids[0]  # should look like did:sov:abc...123
        attach = AttachDecorator.from_indy_dict(did_doc.serialize())
        await attach.data.sign(my_info.verkey, wallet)
        if not my_label:
            my_label = self._session.settings.get("default_label")
        request = DIDXRequest(
            label=my_label,
            did=conn_rec.my_did,
            did_doc_attach=attach,
        )
        request.assign_thread_id(thid=request._id, pthid=pthid)

        # Update connection state
        conn_rec.request_id = request._id
        conn_rec.state = ConnRecord.State.REQUEST.rfc23
        await conn_rec.save(self._session, reason="Created connection request")

        # Multitenancy: add routing for key to handle inbound messages using relay
        multitenant_enabled = self._session.settings.get("multitenant.enabled")
        wallet_id = self._session.settings.get("wallet.id")
        if multitenant_enabled and wallet_id:
            multitenant_mgr = self._session.inject(MultitenantManager)
            await multitenant_mgr.add_wallet_route(
                wallet_id=wallet_id,
                recipient_key=my_info.verkey,
            )

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
            self._session, "Receiving connection request", {"request": request}
        )

        conn_rec = None
        invi_rec = None
        connection_key = None
        my_info = None
        wallet = self._session.inject(BaseWallet)

        try:
            invi_rec = await OOBInvitationRecord.retrieve_by_tag_filter(
                self._session,
                tag_filter={"invi_msg_id": request._thread.pthid},
            )
        except StorageNotFoundError:
            raise DIDXManagerError(
                f"No record of invitation {request._thread.pthid} "
                f"for request {request._id}"
            )

        # Determine what key will need to sign the response
        if receipt.recipient_did_public:
            my_info = await wallet.get_local_did(receipt.recipient_did)
            connection_key = my_info.verkey
        else:
            connection_key = receipt.recipient_verkey
            try:
                conn_rec = await ConnRecord.retrieve_by_invitation_key(
                    session=self._session,
                    invitation_key=connection_key,
                    their_role=ConnRecord.Role.REQUESTER.rfc23,
                )
            except StorageNotFoundError:
                raise DIDXManagerError("No invitation found for pairwise connection")

        if conn_rec:
            connection_key = conn_rec.invitation_key
            if conn_rec.is_multiuse_invitation:
                wallet = self._session.inject(BaseWallet)
                my_info = await wallet.create_local_did()
                new_conn_rec = ConnRecord(
                    invitation_key=connection_key,
                    my_did=my_info.did,
                    state=ConnRecord.State.REQUEST.rfc23,
                    accept=conn_rec.accept,
                    their_role=conn_rec.their_role,
                )

                await new_conn_rec.save(
                    self._session,
                    reason="Received connection request from multi-use invitation DID",
                )

                # Transfer metadata from multi-use to new connection
                # Must come after save so there's an ID to associate with metadata
                for key, value in (
                    await conn_rec.metadata_get_all(self._session)
                ).items():
                    await new_conn_rec.metadata_set(self._session, key, value)

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
            conn_rec.request_id = request._id
            await conn_rec.save(
                self._session, reason="Received connection request from invitation"
            )
        elif self._session.settings.get("public_invites"):
            my_info = await wallet.create_local_did()
            conn_rec = ConnRecord(
                my_did=my_info.did,
                their_did=request.did,
                their_label=request.label,
                their_role=ConnRecord.Role.REQUESTER.rfc23,
                invitation_key=connection_key,
                request_id=request._id,
                state=ConnRecord.State.REQUEST.rfc23,
                accept=(
                    ConnRecord.ACCEPT_AUTO
                    if invi_rec.auto_accept
                    else ConnRecord.ACCEPT_MANUAL
                ),  # oob manager calculates (including config) at conn record creation
            )

            await conn_rec.save(
                self._session, reason="Received connection request from public DID"
            )
        else:
            raise DIDXManagerError("Public invitations are not enabled")

        # Attach the connection request so it can be found and responded to
        await conn_rec.attach_request(self._session, request)

        # Multitenancy: add routing for key to handle inbound messages using relay
        multitenant_enabled = self._session.settings.get("multitenant.enabled")
        wallet_id = self._session.settings.get("wallet.id")
        if my_info and multitenant_enabled and wallet_id:
            multitenant_mgr = self._session.inject(MultitenantManager)
            await multitenant_mgr.add_wallet_route(
                wallet_id=wallet_id,
                recipient_key=my_info.verkey,
            )

        if invi_rec.auto_accept:
            response = await self.create_response(conn_rec)
            responder = self._session.inject(BaseResponder, required=False)
            if responder:
                await responder.send_reply(
                    response, connection_id=conn_rec.connection_id
                )
                conn_rec.state = ConnRecord.State.RESPONSE.rfc23
                await conn_rec.save(self._session, reason="Sent connection response")
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
            self._session,
            "Creating connection response",
            {"connection_id": conn_rec.connection_id},
        )

        if ConnRecord.State.get(conn_rec.state) is not ConnRecord.State.REQUEST:
            raise DIDXManagerError(
                f"Connection not in state {ConnRecord.State.REQUEST.rfc23}"
            )

        request = await conn_rec.retrieve_request(self._session)
        wallet = self._session.inject(BaseWallet)
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
            default_endpoint = self._session.settings.get("default_endpoint")
            if default_endpoint:
                my_endpoints.append(default_endpoint)
            my_endpoints.extend(self._session.settings.get("additional_endpoints", []))
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
        wallet = self._session.inject(BaseWallet)
        await response.sign_field("connection", connection.invitation_key, wallet)
        """

        # Update connection state
        conn_rec.state = ConnRecord.State.RESPONSE.rfc23
        await conn_rec.save(
            self._session,
            reason="Created connection response",
            log_params={"response": response},
        )

        # Multitenancy: add routing for key to handle inbound messages using relay
        multitenant_enabled = self._session.settings.get("multitenant.enabled")
        wallet_id = self._session.settings.get("wallet.id")
        if multitenant_enabled and wallet_id:
            multitenant_mgr = self._session.inject(MultitenantManager)
            await multitenant_mgr.add_wallet_route(
                wallet_id=wallet_id,
                recipient_key=my_info.verkey,
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
        wallet = self._session.inject(BaseWallet)

        conn_rec = None
        if response._thread:
            # identify the request by the thread ID
            try:
                conn_rec = await ConnRecord.retrieve_by_request_id(
                    self._session, response._thread_id
                )
            except StorageNotFoundError:
                pass

        if not conn_rec and receipt.sender_did:
            # identify connection by the DID they used for us
            try:
                conn_rec = await ConnRecord.retrieve_by_did(
                    session=self._session,
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
        await conn_rec.save(self._session, reason="Accepted connection response")

        # create and send connection-complete message
        complete = DIDXComplete()
        complete.assign_thread_from(response)
        responder = self._session.inject(BaseResponder, required=False)
        if responder:
            await responder.send_reply(complete, connection_id=conn_rec.connection_id)

            conn_rec.state = ConnRecord.State.COMPLETED.rfc23
            await conn_rec.save(self._session, reason="Sent connection complete")

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
                self._session, complete._thread_id
            )
        except StorageNotFoundError:
            raise DIDXManagerError(
                "No corresponding connection request found",
                error_code=ProblemReportReason.COMPLETE_NOT_ACCEPTED,
            )

        conn_rec.state = ConnRecord.State.COMPLETED.rfc23
        await conn_rec.save(self._session, reason="Received connection complete")

        return conn_rec

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
            router = await ConnRecord.retrieve_by_id(self._session, router_id)
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
        storage = self._session.inject(BaseStorage)
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
        storage: BaseStorage = self._session.inject(BaseStorage)
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
        storage = self._session.inject(BaseStorage)
        await storage.add_record(record)

    async def find_did_for_key(self, key: str) -> str:
        """Find the DID previously associated with a key.

        Args:
            key: The verkey to look up
        """
        storage = self._session.inject(BaseStorage)
        record = await storage.find_record(
            DIDXManager.RECORD_TYPE_DID_KEY, {"key": key}
        )
        return record.tags["did"]

    async def remove_keys_for_did(self, did: str):
        """Remove all keys associated with a DID.

        Args:
            did: The DID for which to remove keys
        """
        storage = self._session.inject(BaseStorage)
        await storage.delete_all_records(DIDXManager.RECORD_TYPE_DID_KEY, {"did": did})

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
            raise DIDXManagerError("DID doc attachment signature failed verification")

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
