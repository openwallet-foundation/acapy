"""Classes to manage DID exchanges."""

import logging

# TODO flense this mess
from typing import Sequence, Tuple

from ....cache.base import BaseCache
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
from ....messaging.responder import BaseResponder
from ....storage.base import BaseStorage
from ....storage.error import StorageError, StorageNotFoundError
from ....storage.record import StorageRecord
from ....transport.inbound.receipt import MessageReceipt
from ....wallet.base import BaseWallet, DIDInfo
from ....wallet.crypto import create_keypair, seed_to_did
from ....wallet.error import WalletNotFoundError
from ....wallet.util import bytes_to_b58
from ....protocols.routing.v1_0.manager import RoutingManager

from .messages.connection_invitation import ConnectionInvitation
from .messages.connection_request import ConnectionRequest
from .messages.connection_response import ConnectionResponse
from .messages.problem_report import ProblemReportReason
from .models.connection_detail import ConnectionDetail

# ---

from ....messaging.decorators.attach_decorator import AttachDecorator

from .messages.request import DIDExRequest
from .models.didexchange import DIDExRecord

class DIDExManagerError(BaseError):
    """Connection error."""


class DIDExManager:
    """Class for managing DID exchanges."""

    RECORD_TYPE_DID_DOC = "did_doc"
    RECORD_TYPE_DID_KEY = "did_key"

    def __init__(self, context: InjectionContext):
        """
        Initialize a DIDExManager.

        Args:
            context: The context for this DID exchange manager
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    @property
    def context(self) -> InjectionContext:
        """
        Accessor for the current injection context.

        Returns:
            The injection context for this DID exchange manager

        """
        return self._context

    async def create_did_doc(
        self,
        did_info: DIDInfo,
        inbound_connection_id: str = None,
        svc_endpoints: Sequence[str] = None,
    ) -> DIDDoc:
        """Create our DID document for a given DID.

        Args:
            did_info: The DID information (DID and verkey)
            svc_endpoints: Custom endpoints for the DID document

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
            router = await ConnectionRecord.retrieve_by_id(self.context, router_id)
            if router.state != ConnectionRecord.STATE_ACTIVE:
                raise DIDExManagerError(
                    f"Router connection not active: {router_id}"
                )
            routing_doc, _ = await self.fetch_did_document(router.their_did)
            if not routing_doc.service:
                raise DIDExManagerError(
                    f"No services defined by routing DIDDoc: {router_id}"
                )
            for service in routing_doc.service.values():
                if not service.endpoint:
                    raise DIDExManagerError(
                        "Routing DIDDoc service has no service endpoint"
                    )
                if not service.recip_keys:
                    raise DIDExManagerError(
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
            endpoint_ident = f"indy{endpoint_index}" if endpoint_index else "indy"
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
        """Retrieve a DID Document for a given DID, and its storage record.

        Args:
            did: The DID to search for
        """
        storage: BaseStorage = await self.context.inject(BaseStorage)
        record = await storage.search_records(
            self.RECORD_TYPE_DID_DOC, {"did": did}
        ).fetch_single()
        return (DIDDoc.from_json(record.value), record)
    
    async def send_request(self, endpoint: str, label: str = None) -> DIDInfo:
        """
        Send DID exchange request.

        Args:
            endpoint: endpoint to which to send DID exchange request
            label: label for DID exchange request

        Returns:
            Created DIDInfo for DID exchange

        """

        # use wallet from context
        # take endpoint from parameters
        # generate peer DID with verkey in wallet
        # build DID Doc and sign it
        # create didex request
        # create and store didex record
        # create and store connection record
        # return connection record
        
        wallet: BaseWallet = await self.context.inject(BaseWallet)
        did_info = await wallet.create_local_did()
        did_doc = await self.create_did_doc(did_info, [endpoint])
        attach_data = AttachDecorator.from_aries_msg(did_doc.serialize()).data
        await attach_data.sign(did_doc.verkey, wallet)
        didex_req = DIDExRequest(
            label=label or f"DID exchange - {did_info.did}",
            did=did_info.did,
            did_doc_attach=attach_data
        )
        didex_record = DIDExRecord(
            did_ex_id=did_info.did,
            role=DIDExRecord.ROLE_REQUESTER,
            state=DIDExRecord.STATE_START,
            error_msg=None,
            trace=False,
        )
        conn_rec = ConnectionRecord(
            my_did=did_indy.did,
            their_role=
        )
        await cred_ex_record.save(self.context, reason="create DID exchange")

        return did_info
