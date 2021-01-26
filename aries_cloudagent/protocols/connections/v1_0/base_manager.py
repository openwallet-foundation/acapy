"""
Class to provide some common utilities.

For Connection, DIDExchange and OutOfBand Manager.
"""

from ....core.profile import ProfileSession
from ....connections.models.conn_record import ConnRecord
from ....wallet.base import BaseWallet
from .messages.connection_invitation import ConnectionInvitation
from ....ledger.base import BaseLedger
from ....core.error import BaseError
from ....connections.models.connection_target import ConnectionTarget
from ....wallet.util import did_key_to_naked
import logging
from typing import Sequence, Tuple
from ....connections.models.diddoc import DIDDoc
from ....storage.base import BaseStorage
from ....storage.record import StorageRecord


class BaseConnectionManagerError(BaseError):
    """BaseConnectionManager error."""


class BaseConnectionManager:
    """Class to provide utilities regarding connection_targets."""

    RECORD_TYPE_DID_DOC = "did_doc"
    RECORD_TYPE_DID_KEY = "did_key"

    def __init__(self, session: ProfileSession):
        """
        Initialize a BaseConnectionManager.

        Args:
            session: The profile session for this presentation
        """
        self._logger = logging.getLogger(__name__)
        self._session = session

    async def fetch_connection_targets(
        self, connection: ConnRecord
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection target from a `ConnRecord`.

        Args:
            connection: The connection record (with associated `DIDDoc`)
                used to generate the connection target
        """

        if not connection.my_did:
            self._logger.debug("No local DID associated with connection")
            return None

        wallet = self._session.inject(BaseWallet)
        my_info = await wallet.get_local_did(connection.my_did)
        results = None

        if (
            ConnRecord.State.get(connection.state)
            in (ConnRecord.State.INVITATION, ConnRecord.State.REQUEST)
            and ConnRecord.Role.get(connection.their_role) is ConnRecord.Role.RESPONDER
        ):
            invitation = await connection.retrieve_invitation(self._session)
            if isinstance(invitation, ConnectionInvitation):  # conn protocol invitation
                if invitation.did:
                    # populate recipient keys and endpoint from the ledger
                    ledger = self._session.inject(BaseLedger, required=False)
                    if not ledger:
                        raise BaseConnectionManagerError(
                            "Cannot resolve DID without ledger instance"
                        )
                    async with ledger:
                        endpoint = await ledger.get_endpoint_for_did(invitation.did)
                        recipient_keys = [await ledger.get_key_for_did(invitation.did)]
                        routing_keys = []
                else:
                    endpoint = invitation.endpoint
                    recipient_keys = invitation.recipient_keys
                    routing_keys = invitation.routing_keys
            else:  # out-of-band invitation
                if invitation.service_dids:
                    # populate recipient keys and endpoint from the ledger
                    ledger = self._session.inject(BaseLedger, required=False)
                    if not ledger:
                        raise BaseConnectionManagerError(
                            "Cannot resolve DID without ledger instance"
                        )
                    async with ledger:
                        endpoint = await ledger.get_endpoint_for_did(
                            invitation.service_dids[0]
                        )
                        recipient_keys = [
                            await ledger.get_key_for_did(invitation.service_dids[0])
                        ]
                        routing_keys = []
                else:
                    endpoint = invitation.service_blocks[0].service_endpoint
                    recipient_keys = [
                        did_key_to_naked(k)
                        for k in invitation.service_blocks[0].recipient_keys
                    ]
                    routing_keys = [
                        did_key_to_naked(k)
                        for k in invitation.service_blocks[0].routing_keys
                    ]

            results = [
                ConnectionTarget(
                    did=connection.their_did,
                    endpoint=endpoint,
                    label=invitation.label,
                    recipient_keys=recipient_keys,
                    routing_keys=routing_keys,
                    sender_key=my_info.verkey,
                )
            ]
        else:
            if not connection.their_did:
                self._logger.debug("No target DID associated with connection")
                return None

            did_doc, _ = await self.fetch_did_document(connection.their_did)
            results = self.diddoc_connection_targets(
                did_doc, my_info.verkey, connection.their_label
            )

        return results

    def diddoc_connection_targets(
        self, doc: DIDDoc, sender_verkey: str, their_label: str = None
    ) -> Sequence[ConnectionTarget]:
        """Get a list of connection targets from a DID Document.

        Args:
            doc: The DID Document to create the target from
            sender_verkey: The verkey we are using
            their_label: The connection label they are using
        """

        if not doc:
            raise BaseConnectionManagerError("No DIDDoc provided for connection target")
        if not doc.did:
            raise BaseConnectionManagerError("DIDDoc has no DID")
        if not doc.service:
            raise BaseConnectionManagerError("No services defined by DIDDoc")

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

    async def fetch_did_document(self, did: str) -> Tuple[DIDDoc, StorageRecord]:
        """Retrieve a DID Document for a given DID.

        Args:
            did: The DID to search for
        """
        storage = self._session.inject(BaseStorage)
        record = await storage.find_record(self.RECORD_TYPE_DID_DOC, {"did": did})
        return DIDDoc.from_json(record.value), record
