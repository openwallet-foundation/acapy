"""Classes to manage connection establishment under RFC 23 (DID exchange)."""

import json
import logging
from typing import List, Optional, Sequence, Tuple, Union

from did_peer_4 import LONG_PATTERN, long_to_short

from ....admin.server import AdminResponder
from ....connections.base_manager import BaseConnectionManager
from ....connections.models.conn_record import ConnRecord
from ....connections.models.connection_target import ConnectionTarget
from ....core.error import BaseError
from ....core.oob_processor import OobMessageProcessor
from ....core.profile import Profile
from ....did.did_key import DIDKey
from ....messaging.decorators.attach_decorator import AttachDecorator
from ....messaging.responder import BaseResponder
from ....storage.error import StorageNotFoundError
from ....transport.inbound.receipt import MessageReceipt
from ....wallet.base import BaseWallet
from ....wallet.did_method import SOV
from ....wallet.did_posture import DIDPosture
from ....wallet.error import WalletError
from ....wallet.key_type import ED25519
from ...coordinate_mediation.v1_0.manager import MediationManager
from ...coordinate_mediation.v1_0.models.mediation_record import MediationRecord
from ...discovery.v2_0.manager import V20DiscoveryMgr
from ...out_of_band.v1_0.messages.invitation import (
    InvitationMessage as OOBInvitationMessage,
)
from ...out_of_band.v1_0.messages.service import Service as OOBService
from .message_types import ARIES_PROTOCOL as DIDEX_1_1, DIDEX_1_0
from .messages.complete import DIDXComplete
from .messages.problem_report import DIDXProblemReport, ProblemReportReason
from .messages.request import DIDXRequest
from .messages.response import DIDXResponse


class DIDXManagerError(BaseError):
    """Connection error."""


class LegacyHandlingFallback(DIDXManagerError):
    """Raised when a request cannot be completed using updated semantics.

    Triggers falling back to legacy handling.
    """


class DIDXManager(BaseConnectionManager):
    """Class for managing connections under RFC 23 (DID exchange)."""

    SUPPORTED_USE_DID_METHODS = ("did:peer:2", "did:peer:4")

    def __init__(self, profile: Profile):
        """Initialize a DIDXManager.

        Args:
            profile: The profile for this did exchange manager
        """
        self._profile = profile
        self._logger = logging.getLogger(__name__)
        super().__init__(self._profile)

    @property
    def profile(self) -> Profile:
        """Accessor for the current profile.

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
        protocol: Optional[str] = None,
    ) -> ConnRecord:  # leave in didexchange as it uses a responder: not out-of-band
        """Create a new connection record to track a received invitation.

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
        protocol = protocol or DIDEX_1_0
        if protocol not in ConnRecord.SUPPORTED_PROTOCOLS:
            raise DIDXManagerError(f"Unexpected protocol: {protocol}")

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
            state=ConnRecord.State.INVITATION.rfc160,
            accept=accept,
            alias=alias,
            their_public_did=their_public_did,
            connection_protocol=protocol,
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
                targets = await self.resolve_connection_targets(
                    conn_rec.their_public_did
                )
                conn_rec.invitation_key = targets[0].recipient_keys[0]

        await self._route_manager.save_mediator_for_connection(
            self.profile, conn_rec, mediation_id=mediation_id
        )

        if conn_rec.accept == ConnRecord.ACCEPT_AUTO:
            request = await self.create_request(conn_rec, mediation_id=mediation_id)
            base_responder = self.profile.inject(BaseResponder)
            responder = AdminResponder(self.profile, base_responder.send_fn)
            if responder:
                await responder.send_reply(
                    request,
                    connection_id=conn_rec.connection_id,
                )

                conn_rec.state = ConnRecord.State.REQUEST.rfc160
                async with self.profile.session() as session:
                    await conn_rec.save(session, reason="Sent connection request")
        else:
            self._logger.debug("Connection invitation will await acceptance")

        return conn_rec

    async def create_request_implicit(
        self,
        their_public_did: str,
        my_label: Optional[str] = None,
        my_endpoint: Optional[str] = None,
        mediation_id: Optional[str] = None,
        use_public_did: bool = False,
        alias: Optional[str] = None,
        goal_code: Optional[str] = None,
        goal: Optional[str] = None,
        auto_accept: bool = False,
        protocol: Optional[str] = None,
        use_did: Optional[str] = None,
        use_did_method: Optional[str] = None,
    ) -> ConnRecord:
        """Create and send a request against a public DID only (no explicit invitation).

        Args:
            their_public_did: public DID to which to request a connection
            my_label: my label for request
            my_endpoint: my endpoint
            mediation_id: record id for mediation with routing_keys, service endpoint
            use_public_did: use my public DID for this connection
            goal_code: Optional self-attested code for sharing intent of connection
            goal: Optional self-attested string for sharing intent of connection
            auto_accept: auto-accept a corresponding connection request

        Returns:
            The new `ConnRecord` instance

        """

        if use_did and use_did_method:
            raise DIDXManagerError("Cannot specify both use_did and use_did_method")

        if use_public_did and use_did:
            raise DIDXManagerError("Cannot specify both use_public_did and use_did")

        if use_public_did and use_did_method:
            raise DIDXManagerError(
                "Cannot specify both use_public_did and use_did_method"
            )

        my_info = None
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            if use_public_did:
                my_info = await wallet.get_public_did()
                if not my_info:
                    raise WalletError("No public DID configured")
                if (
                    my_info.did == their_public_did
                    or f"did:sov:{my_info.did}" == their_public_did
                ):
                    raise DIDXManagerError(
                        "Cannot connect to yourself through public DID"
                    )
            elif use_did:
                my_info = await wallet.get_local_did(use_did)

            if my_info:
                try:
                    await ConnRecord.retrieve_by_did(
                        session,
                        their_did=their_public_did,
                        my_did=my_info.did,
                    )
                    raise DIDXManagerError(
                        "Connection already exists for their_did "
                        f"{their_public_did} and my_did {my_info.did}"
                    )
                except StorageNotFoundError:
                    pass

        auto_accept = bool(
            auto_accept
            or (
                auto_accept is None
                and self.profile.settings.get("debug.auto_accept_requests")
            )
        )
        protocol = protocol or DIDEX_1_0
        conn_rec = ConnRecord(
            my_did=(
                my_info.did if my_info else None
            ),  # create-request will fill in on local DID creation
            their_did=their_public_did,
            their_label=None,
            their_role=ConnRecord.Role.RESPONDER.rfc23,
            invitation_key=None,
            invitation_msg_id=None,
            alias=alias,
            their_public_did=their_public_did,
            connection_protocol=protocol,
            accept=ConnRecord.ACCEPT_AUTO if auto_accept else ConnRecord.ACCEPT_MANUAL,
        )
        request = await self.create_request(  # saves and updates conn_rec
            conn_rec=conn_rec,
            my_label=my_label,
            my_endpoint=my_endpoint,
            mediation_id=mediation_id,
            goal_code=goal_code,
            goal=goal,
            use_did_method=use_did_method,
        )
        conn_rec.request_id = request._id
        conn_rec.state = ConnRecord.State.REQUEST.rfc160
        async with self.profile.session() as session:
            await conn_rec.save(session, reason="Created connection request")
        responder = self.profile.inject_or(BaseResponder)
        if responder:
            await responder.send(request, connection_id=conn_rec.connection_id)

        return conn_rec

    async def create_request(
        self,
        conn_rec: ConnRecord,
        my_label: Optional[str] = None,
        my_endpoint: Optional[str] = None,
        mediation_id: Optional[str] = None,
        goal_code: Optional[str] = None,
        goal: Optional[str] = None,
        use_did_method: Optional[str] = None,
    ) -> DIDXRequest:
        """Create a new connection request for a previously-received invitation.

        Args:
            conn_rec: The `ConnRecord` representing the invitation to accept
            my_label: My label for request
            my_endpoint: My endpoint
            mediation_id: The record id for mediation that contains routing_keys and
                service endpoint
            goal_code: Optional self-attested code for sharing intent of connection
            goal: Optional self-attested string for sharing intent of connection
        Returns:
            A new `DIDXRequest` message to send to the other agent

        """
        if use_did_method and use_did_method not in self.SUPPORTED_USE_DID_METHODS:
            raise DIDXManagerError(
                f"Unsupported use_did_method: {use_did_method}. Supported methods: "
                f"{self.SUPPORTED_USE_DID_METHODS}"
            )

        # Mediation Support
        mediation_records = await self._route_manager.mediation_records_for_connection(
            self.profile,
            conn_rec,
            mediation_id,
            or_default=True,
        )

        if my_endpoint:
            my_endpoints = [my_endpoint]
        else:
            my_endpoints = []
            default_endpoint = self.profile.settings.get("default_endpoint")
            if default_endpoint:
                my_endpoints.append(default_endpoint)
            my_endpoints.extend(self.profile.settings.get("additional_endpoints", []))

        if not my_label:
            my_label = self.profile.settings.get("default_label")
            assert my_label

        did_url = None
        if conn_rec.their_public_did is not None:
            services = await self.resolve_didcomm_services(conn_rec.their_public_did)
            if services:
                did_url = services[0].id

        pthid = conn_rec.invitation_msg_id or did_url

        if conn_rec.connection_protocol == DIDEX_1_0:
            did, attach = await self._legacy_did_with_attached_doc(
                conn_rec, my_endpoints, mediation_records
            )
        else:
            if conn_rec.accept == ConnRecord.ACCEPT_AUTO or use_did_method is None:
                # If we're auto accepting or engaging in 1.1 without setting a
                # use_did_method, default to did:peer:4
                use_did_method = "did:peer:4"
            try:
                did, attach = await self._qualified_did_with_fallback(
                    conn_rec,
                    my_endpoints,
                    mediation_records,
                    use_did_method,
                )
            except LegacyHandlingFallback:
                did, attach = await self._legacy_did_with_attached_doc(
                    conn_rec, my_endpoints, mediation_records
                )

        request = DIDXRequest(
            label=my_label,
            did=did,
            did_doc_attach=attach,
            goal=goal,
            goal_code=goal_code,
        )

        if conn_rec.connection_protocol == DIDEX_1_0:
            request.assign_version("1.0")

        request.assign_thread_id(thid=request._id, pthid=pthid)

        # Update connection state
        conn_rec.request_id = request._id
        conn_rec.state = ConnRecord.State.REQUEST.rfc160
        async with self.profile.session() as session:
            await conn_rec.save(session, reason="Created connection request")

        # Idempotent; if routing has already been set up, no action taken
        await self._route_manager.route_connection_as_invitee(
            self.profile, conn_rec, mediation_records
        )

        return request

    async def _qualified_did_with_fallback(
        self,
        conn_rec: ConnRecord,
        my_endpoints: Sequence[str],
        mediation_records: List[MediationRecord],
        use_did_method: Optional[str] = None,
        signing_key: Optional[str] = None,
    ) -> Tuple[str, Optional[AttachDecorator]]:
        """Create DID Exchange request using a qualified DID.

        Fall back to unqualified DID if settings don't cause did:peer emission.
        """
        if conn_rec.my_did:  # DID should be public or qualified
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                my_info = await wallet.get_local_did(conn_rec.my_did)

            posture = DIDPosture.get(my_info.metadata)
            if posture not in (
                DIDPosture.PUBLIC,
                DIDPosture.POSTED,
            ) and not my_info.did.startswith("did:"):
                raise LegacyHandlingFallback(
                    "DID has been previously set and not public or qualified"
                )
        elif use_did_method == "did:peer:4":
            my_info = await self.create_did_peer_4(my_endpoints, mediation_records)
            conn_rec.my_did = my_info.did
        elif use_did_method == "did:peer:2":
            my_info = await self.create_did_peer_2(my_endpoints, mediation_records)
            conn_rec.my_did = my_info.did
        else:
            # We shouldn't hit this condition in practice
            raise LegacyHandlingFallback(
                "Use of qualified DIDs not set according to settings"
            )

        did = conn_rec.my_did
        assert did, "DID must be set on connection record"
        if not did.startswith("did:"):
            did = f"did:sov:{did}"

        attach = None
        if signing_key:
            attach = AttachDecorator.data_base64_string(did)
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                await attach.data.sign(signing_key, wallet)

        return did, attach

    async def _legacy_did_with_attached_doc(
        self,
        conn_rec: ConnRecord,
        my_endpoints: Sequence[str],
        mediation_records: List[MediationRecord],
        invitation_key: Optional[str] = None,
    ) -> Tuple[str, Optional[AttachDecorator]]:
        """Create a DID Exchange request using an unqualified DID."""
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

        posture = DIDPosture.get(my_info.metadata)
        if posture in (
            DIDPosture.PUBLIC,
            DIDPosture.POSTED,
        ):
            return my_info.did, None

        did_doc = await self.create_did_document(
            my_info,
            my_endpoints,
            mediation_records=mediation_records,
        )
        attach = AttachDecorator.data_base64(did_doc.serialize())

        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            await attach.data.sign(invitation_key or my_info.verkey, wallet)

        return my_info.did, attach

    async def receive_request(
        self,
        request: DIDXRequest,
        recipient_did: str,
        recipient_verkey: Optional[str] = None,
        alias: Optional[str] = None,
        auto_accept_implicit: Optional[bool] = None,
    ) -> ConnRecord:
        """Receive and store a connection request.

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

        if recipient_verkey:
            conn_rec = await self._receive_request_pairwise_did(request, alias)
        else:
            conn_rec = await self._receive_request_public_did(
                request, recipient_did, alias, auto_accept_implicit
            )

        # Clean associated oob record if not needed anymore
        oob_processor = self.profile.inject(OobMessageProcessor)
        await oob_processor.clean_finished_oob_record(self.profile, request)

        return conn_rec

    async def _receive_request_pairwise_did(
        self,
        request: DIDXRequest,
        alias: Optional[str] = None,
    ) -> ConnRecord:
        """Receive a DID Exchange request against a pairwise (not public) DID."""
        if not request._thread.pthid:
            raise DIDXManagerError("DID Exchange request missing parent thread ID")

        async with self.profile.session() as session:
            conn_rec = await ConnRecord.retrieve_by_invitation_msg_id(
                session=session,
                invitation_msg_id=request._thread.pthid,
                their_role=ConnRecord.Role.REQUESTER.rfc23,
            )

        if not conn_rec:
            raise DIDXManagerError(
                "Pairwise requests must be against explicit invitations that have not "
                "been previously consumed"
            )

        if conn_rec.is_multiuse_invitation:
            conn_rec = await self._derive_new_conn_from_multiuse_invitation(conn_rec)

        conn_rec.their_label = request.label
        if alias:
            conn_rec.alias = alias
        conn_rec.their_did = request.did
        conn_rec.state = ConnRecord.State.REQUEST.rfc160
        conn_rec.request_id = request._id
        conn_rec.connection_protocol = self._handshake_protocol_to_use(request)

        # TODO move to common method or add to transaction?
        await self._extract_and_record_did_doc_info(request)

        async with self.profile.transaction() as txn:
            # Attach the connection request so it can be found and responded to
            await conn_rec.save(
                txn, reason="Received connection request from invitation"
            )
            await conn_rec.attach_request(txn, request)
            await txn.commit()

        return conn_rec

    def _handshake_protocol_to_use(self, request: DIDXRequest):
        """Determine the connection protocol to use based on the request.

        If we support it, we'll send it. If we don't, we'll try didexchange/1.1.
        """
        protocol = f"{request._type.protocol}/{request._type.version}"
        if protocol in ConnRecord.SUPPORTED_PROTOCOLS:
            return protocol

        return DIDEX_1_1

    async def _receive_request_public_did(
        self,
        request: DIDXRequest,
        recipient_did: str,
        alias: Optional[str] = None,
        auto_accept_implicit: Optional[bool] = None,
    ) -> ConnRecord:
        """Receive a DID Exchange request against a public DID."""
        if not self.profile.settings.get("public_invites"):
            raise DIDXManagerError(
                "Public invitations are not enabled: connection request refused"
            )

        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            public_did_info = await wallet.get_local_did(recipient_did)

        if DIDPosture.get(public_did_info.metadata) not in (
            DIDPosture.PUBLIC,
            DIDPosture.POSTED,
        ):
            raise DIDXManagerError(f"Request DID {recipient_did} is not public")

        if request._thread.pthid:
            # Invitation was explicit
            async with self.profile.session() as session:
                conn_rec = await ConnRecord.retrieve_by_invitation_msg_id(
                    session=session,
                    invitation_msg_id=request._thread.pthid,
                    their_role=ConnRecord.Role.REQUESTER.rfc23,
                )
        else:
            # Invitation was implicit
            conn_rec = None

        if conn_rec and conn_rec.is_multiuse_invitation:
            conn_rec = await self._derive_new_conn_from_multiuse_invitation(conn_rec)

        save_reason = None
        if conn_rec:
            conn_rec.their_label = request.label
            if alias:
                conn_rec.alias = alias
            conn_rec.their_did = request.did
            conn_rec.state = ConnRecord.State.REQUEST.rfc160
            conn_rec.request_id = request._id
            save_reason = "Received connection request from invitation to public DID"
        else:
            # request is against implicit invitation on public DID
            if not self.profile.settings.get("requests_through_public_did"):
                raise DIDXManagerError(
                    "Unsolicited connection requests to public DID is not enabled"
                )

            auto_accept = bool(
                auto_accept_implicit
                or (
                    auto_accept_implicit is None
                    and self.profile.settings.get("debug.auto_accept_requests", False)
                )
            )

            conn_rec = ConnRecord(
                my_did=None,  # Defer DID creation until create_response
                accept=(
                    ConnRecord.ACCEPT_AUTO if auto_accept else ConnRecord.ACCEPT_MANUAL
                ),
                their_did=request.did,
                their_label=request.label,
                alias=alias,
                their_role=ConnRecord.Role.REQUESTER.rfc23,
                invitation_key=public_did_info.verkey,
                invitation_msg_id=None,
                request_id=request._id,
                state=ConnRecord.State.REQUEST.rfc160,
            )
            save_reason = "Received connection request from public DID"

        conn_rec.connection_protocol = self._handshake_protocol_to_use(request)

        # TODO move to common method or add to transaction?
        await self._extract_and_record_did_doc_info(request)

        async with self.profile.transaction() as txn:
            # Attach the connection request so it can be found and responded to
            await conn_rec.save(txn, reason=save_reason)
            await conn_rec.attach_request(txn, request)
            await txn.commit()

        return conn_rec

    async def _extract_and_record_did_doc_info(self, request: DIDXRequest):
        """Extract and record DID Document information from the DID Exchange request.

        Extracting this info enables us to correlate messages from these keys back to a
        connection when we later receive inbound messages.
        """
        if request.did_doc_attach and request.did_doc_attach.data:
            self._logger.debug("Received DID Doc attachment in request")
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                conn_did_doc = await self.verify_diddoc(wallet, request.did_doc_attach)
                await self.store_did_document(conn_did_doc)

            # Special case: legacy DIDs were unqualified in request, qualified in doc
            if request.did and not request.did.startswith("did:"):
                did_to_check = f"did:sov:{request.did}"
            else:
                did_to_check = request.did

            if did_to_check != conn_did_doc["id"]:
                raise DIDXManagerError(
                    (
                        f"Connection DID {request.did} does not match "
                        f"DID Doc id {conn_did_doc['id']}"
                    ),
                    error_code=ProblemReportReason.REQUEST_NOT_ACCEPTED.value,
                )
        else:
            if request.did is None:
                raise DIDXManagerError("No DID in request")

            self._logger.debug(
                "No DID Doc attachment in request; doc will be resolved from DID"
            )
            await self.record_keys_for_resolvable_did(request.did)

    async def _derive_new_conn_from_multiuse_invitation(
        self, conn_rec: ConnRecord
    ) -> ConnRecord:
        """Derive a new connection record from a multi-use invitation.

        Multi-use invitations are tracked using a connection record. When a connection
        is formed through a multi-use invitation conn rec, a new record for the resulting
        connection is required. The original multi-use invitation record is retained
        until deleted by the user.
        """
        new_conn_rec = ConnRecord(
            invitation_key=conn_rec.invitation_key,
            state=ConnRecord.State.INIT.rfc160,
            accept=conn_rec.accept,
            their_role=conn_rec.their_role,
        )
        async with self.profile.session() as session:
            # TODO: Suppress the event that gets emitted here?
            await new_conn_rec.save(
                session,
                reason="Created new connection record from multi-use invitation",
            )

        # Transfer metadata from multi-use to new connection
        # Must come after save so there's an ID to associate with metadata
        async with self.profile.session() as session:
            for key, value in (await conn_rec.metadata_get_all(session)).items():
                await new_conn_rec.metadata_set(session, key, value)

        return new_conn_rec

    async def create_response(
        self,
        conn_rec: ConnRecord,
        my_endpoint: Optional[str] = None,
        mediation_id: Optional[str] = None,
        use_public_did: Optional[bool] = None,
    ) -> DIDXResponse:
        """Create a connection response for a received connection request.

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

        mediation_records = await self._route_manager.mediation_records_for_connection(
            self.profile, conn_rec, mediation_id
        )

        if ConnRecord.State.get(conn_rec.state) is not ConnRecord.State.REQUEST:
            raise DIDXManagerError(
                f"Connection not in state {ConnRecord.State.REQUEST.rfc23}"
            )
        async with self.profile.session() as session:
            request = await conn_rec.retrieve_request(session)

        if my_endpoint:
            my_endpoints = [my_endpoint]
        else:
            my_endpoints = []
            default_endpoint = self.profile.settings.get("default_endpoint")
            if default_endpoint:
                my_endpoints.append(default_endpoint)
            my_endpoints.extend(self.profile.settings.get("additional_endpoints", []))

        if conn_rec.their_did and conn_rec.their_did.startswith("did:peer:2"):
            use_did_method = "did:peer:2"
        elif conn_rec.their_did and conn_rec.their_did.startswith("did:peer:4"):
            use_did_method = "did:peer:4"
        else:
            use_did_method = None

        if use_public_did:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                public_info = await wallet.get_public_did()
            if public_info:
                conn_rec.my_did = public_info.did
            else:
                raise DIDXManagerError("No public DID configured")

        if conn_rec.connection_protocol == DIDEX_1_0:
            did, attach = await self._legacy_did_with_attached_doc(
                conn_rec,
                my_endpoints,
                mediation_records,
                invitation_key=conn_rec.invitation_key,
            )
            response = DIDXResponse(did=did, did_doc_attach=attach)
            response.assign_version("1.0")
        else:
            try:
                did, attach = await self._qualified_did_with_fallback(
                    conn_rec,
                    my_endpoints,
                    mediation_records,
                    use_did_method=use_did_method,
                    signing_key=conn_rec.invitation_key,
                )
                response = DIDXResponse(did=did, did_rotate_attach=attach)
            except LegacyHandlingFallback:
                did, attach = await self._legacy_did_with_attached_doc(
                    conn_rec, my_endpoints, mediation_records, conn_rec.invitation_key
                )
                response = DIDXResponse(did=did, did_doc_attach=attach)

        # Idempotent; if routing has already been set up, no action taken
        await self._route_manager.route_connection_as_inviter(
            self.profile, conn_rec, mediation_records
        )

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
            _, request = await temp_mediation_mgr.prepare_request(
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
        """Accept a connection response under RFC 23 (DID exchange).

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
        if response.did_doc_attach:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                conn_did_doc = await self.verify_diddoc(
                    wallet, response.did_doc_attach, conn_rec.invitation_key
                )
            # Special case: legacy DIDs were unqualified in response, qualified in doc
            if their_did and not their_did.startswith("did:"):
                did_to_check = f"did:sov:{their_did}"
            else:
                did_to_check = their_did

            if did_to_check != conn_did_doc["id"]:
                raise DIDXManagerError(
                    f"Connection DID {their_did} "
                    f"does not match DID doc id {conn_did_doc['id']}"
                )
            await self.store_did_document(conn_did_doc)
        else:
            if response.did is None:
                raise DIDXManagerError("No DID in response")

            if response.did_rotate_attach is None:
                raise DIDXManagerError(
                    "did_rotate~attach required if no signed doc attachment"
                )

            self._logger.debug("did_rotate~attach found; verifying signature")
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                signed_did = await self.verify_rotate(
                    wallet, response.did_rotate_attach, conn_rec.invitation_key
                )
                if their_did != response.did:
                    raise DIDXManagerError(
                        f"Connection DID {their_did} "
                        f"does not match singed DID rotate {signed_did}"
                    )

            self._logger.debug(
                "No DID Doc attachment in response; doc will be resolved from DID"
            )
            await self.record_keys_for_resolvable_did(response.did)

        conn_rec.their_did = their_did

        # The long format I sent has been acknowledged, use short form now.
        if LONG_PATTERN.match(conn_rec.my_did or ""):
            conn_rec.my_did = await self.long_did_peer_4_to_short(conn_rec.my_did)
        if LONG_PATTERN.match(conn_rec.their_did or ""):
            conn_rec.their_did = long_to_short(conn_rec.their_did)

        conn_rec.state = ConnRecord.State.RESPONSE.rfc160
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
        if conn_rec.connection_protocol == DIDEX_1_0:
            complete.assign_version("1.0")

        responder = self.profile.inject_or(BaseResponder)
        if responder:
            await responder.send_reply(complete, connection_id=conn_rec.connection_id)

            conn_rec.state = ConnRecord.State.COMPLETED.rfc160
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
        """Accept a connection complete message under RFC 23 (DID exchange).

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

        if LONG_PATTERN.match(conn_rec.my_did or ""):
            conn_rec.my_did = await self.long_did_peer_4_to_short(conn_rec.my_did)
        if LONG_PATTERN.match(conn_rec.their_did or ""):
            conn_rec.their_did = long_to_short(conn_rec.their_did)

        conn_rec.state = ConnRecord.State.COMPLETED.rfc160
        async with self.profile.session() as session:
            await conn_rec.save(session, reason="Received connection complete")
            if session.settings.get("auto_disclose_features"):
                discovery_mgr = V20DiscoveryMgr(self._profile)
                await discovery_mgr.proactive_disclose_features(
                    connection_id=conn_rec.connection_id
                )

        return conn_rec

    async def reject(
        self,
        conn_rec: ConnRecord,
        *,
        reason: Optional[str] = None,
    ) -> DIDXProblemReport:
        """Abandon an existing DID exchange."""
        state_to_reject_code = {
            ConnRecord.State.INVITATION.rfc23
            + "-received": ProblemReportReason.INVITATION_NOT_ACCEPTED,
            ConnRecord.State.REQUEST.rfc23
            + "-received": ProblemReportReason.REQUEST_NOT_ACCEPTED,
        }
        code = state_to_reject_code.get(conn_rec.rfc23_state)
        if not code:
            raise DIDXManagerError(
                f"Cannot reject connection in state: {conn_rec.rfc23_state}"
            )

        async with self.profile.session() as session:
            await conn_rec.abandon(session, reason=reason)

        report = DIDXProblemReport(
            description={
                "code": code.value,
                "en": reason or "DID exchange rejected",
            },
        )
        if conn_rec.connection_protocol == DIDEX_1_0:
            report.assign_version("1.0")

        # TODO Delete the record?
        return report

    async def receive_problem_report(
        self,
        conn_rec: ConnRecord,
        report: DIDXProblemReport,
    ):
        """Receive problem report."""
        if not report.description:
            raise DIDXManagerError("Missing description in problem report")

        if report.description.get("code") in {
            reason.value for reason in ProblemReportReason
        }:
            self._logger.info("Problem report indicates connection is abandoned")
            async with self.profile.session() as session:
                await conn_rec.abandon(
                    session,
                    reason=report.description.get("en"),
                )
        else:
            raise DIDXManagerError(
                f"Received unrecognized problem report: {report.description}"
            )

    async def verify_diddoc(
        self,
        wallet: BaseWallet,
        attached: AttachDecorator,
        invi_key: str = None,
    ) -> dict:
        """Verify DIDDoc attachment and return signed data."""
        signed_diddoc_bytes = attached.data.signed
        if not signed_diddoc_bytes:
            raise DIDXManagerError("DID doc attachment is not signed.")
        if not await attached.data.verify(wallet, invi_key):
            raise DIDXManagerError("DID doc attachment signature failed verification")

        return json.loads(signed_diddoc_bytes.decode())

    async def verify_rotate(
        self,
        wallet: BaseWallet,
        attached: AttachDecorator,
        invi_key: str = None,
    ) -> str:
        """Verify a signed DID rotate attachment and return did."""
        signed_diddoc_bytes = attached.data.signed
        if not signed_diddoc_bytes:
            raise DIDXManagerError("DID rotate attachment is not signed.")
        if not await attached.data.verify(wallet, invi_key):
            raise DIDXManagerError(
                "DID rotate attachment signature failed verification"
            )

        return signed_diddoc_bytes.decode()

    async def manager_error_to_problem_report(
        self,
        e: DIDXManagerError,
        message: Union[DIDXRequest, DIDXResponse],
        message_receipt,
    ) -> tuple[DIDXProblemReport, Sequence[ConnectionTarget]]:
        """Convert DIDXManagerError to problem report."""
        self._logger.exception("Error receiving RFC 23 connection request")
        targets = None
        report = None
        if e.error_code:
            report = DIDXProblemReport(
                description={"en": e.message, "code": e.error_code}
            )
            report.assign_thread_from(message)
            report.assign_version_from(message)
            if message.did_doc_attach:
                try:
                    # convert diddoc attachment to diddoc...
                    async with self.profile.session() as session:
                        wallet = session.inject(BaseWallet)
                        conn_did_doc = await self.verify_diddoc(
                            wallet, message.did_doc_attach
                        )
                    # get the connection targets...
                    targets = self.diddoc_connection_targets(
                        conn_did_doc,
                        message_receipt.recipient_verkey,
                    )
                except DIDXManagerError:
                    self._logger.exception("Error parsing DIDDoc for problem report")

        return report, targets
