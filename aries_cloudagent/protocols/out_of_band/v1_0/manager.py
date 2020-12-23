"""Classes to manage connections."""

from aries_cloudagent.multitenant.manager import MultitenantManager
import logging

from typing import Mapping, Sequence

from ....connections.models.conn_record import ConnRecord
from ....core.error import BaseError
from ....core.profile import ProfileSession
from ....ledger.base import BaseLedger
from ....wallet.base import BaseWallet
from ....wallet.util import did_key_to_naked, naked_to_did_key

from ...didexchange.v1_0.manager import DIDXManager
from ...didcomm_prefix import DIDCommPrefix
from ...issue_credential.v1_0.models.credential_exchange import V10CredentialExchange
from ...present_proof.v1_0.message_types import PRESENTATION_REQUEST
from ...present_proof.v1_0.models.presentation_exchange import V10PresentationExchange

from .messages.invitation import InvitationMessage
from .messages.service import Service as ServiceMessage
from .models.invitation import InvitationRecord

DIDX_INVITATION = "didexchange/v1.0"


class OutOfBandManagerError(BaseError):
    """Out of band error."""


class OutOfBandManagerNotImplementedError(BaseError):
    """Out of band error for unimplemented functionality."""


class OutOfBandManager:
    """Class for managing out of band messages."""

    def __init__(self, session: ProfileSession):
        """
        Initialize a OutOfBandManager.

        Args:
            session: The profile session for this out of band manager
        """
        self._session = session
        self._logger = logging.getLogger(__name__)

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

            # Multitenancy: add routing for key to handle inbound messages using relay
            multitenant_enabled = self._session.settings.get("multitenant.enabled")
            wallet_id = self._session.settings.get("wallet.id")
            if multitenant_enabled and wallet_id:
                multitenant_mgr = self._session.inject(MultitenantManager)
                await multitenant_mgr.add_wallet_route(
                    wallet_id=wallet_id,
                    recipient_key=connection_key.verkey,
                )

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

    async def receive_invitation(self, invi_msg: InvitationMessage) -> ConnRecord:
        """Receive an out of band invitation message."""

        ledger: BaseLedger = self._session.inject(BaseLedger)

        # There must be exactly 1 service entry
        if len(invi_msg.service_blocks) + len(invi_msg.service_dids) != 1:
            raise OutOfBandManagerError("service array must have exactly one element")

        # Get the single service item
        if invi_msg.service_blocks:
            service = invi_msg.service_blocks[0]

        else:
            # If it's in the did format, we need to convert to a full service block
            service_did = invi_msg.service_dids[0]
            async with ledger:
                verkey = await ledger.get_key_for_did(service_did)
                did_key = naked_to_did_key(verkey)
                endpoint = await ledger.get_endpoint_for_did(service_did)
            service = ServiceMessage.deserialize(
                {
                    "id": "#inline",
                    "type": "did-communication",
                    "recipientKeys": [did_key],
                    "routingKeys": [],
                    "serviceEndpoint": endpoint,
                }
            )

        unq_handshake_protos = {
            DIDCommPrefix.unqualify(proto) for proto in invi_msg.handshake_protocols
        }
        if unq_handshake_protos == {DIDX_INVITATION}:
            if len(invi_msg.request_attach) != 0:
                raise OutOfBandManagerError(
                    "request block must be empty for invitation message type."
                )

            # Transform back to 'naked' verkey
            service.recipient_keys = [
                did_key_to_naked(key) for key in service.recipient_keys or []
            ]
            service.routing_keys = [
                did_key_to_naked(key) for key in service.routing_keys
            ] or []

            didx_mgr = DIDXManager(self._session)
            conn_rec = await didx_mgr.receive_invitation(invi_msg, auto_accept=True)

        elif (
            len(invi_msg.request_attach) == 1
            and DIDCommPrefix.unqualify(invi_msg.request_attach[0].data.json["@type"])
            == PRESENTATION_REQUEST
        ):
            raise OutOfBandManagerNotImplementedError(
                f"{invi_msg.request_attach[0].data.json['@type']} "
                "request type not implemented."
            )
        else:
            raise OutOfBandManagerError("Invalid request type")

        return conn_rec
