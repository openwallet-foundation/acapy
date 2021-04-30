import logging

from pydid import DID, DIDDocument, DIDDocumentBuilder, VerificationSuite
from pydid.validation import serialize

# from ..core.profile import Profile
from ..wallet.base import BaseWallet

from ..core.profile import ProfileSession
from .util import retrieve_did_document, save_did_document

LOGGER = logging.getLogger(__name__)

VERIFICATION_METHOD_TYPE = "Ed25519VerificationKey2018"
AGENT_SERVICE_TYPE = "did-communication"
SUITE = VerificationSuite(VERIFICATION_METHOD_TYPE, "publicKeyBase58")


class DIDWeb():
    """Class for managing a did:web DID document."""

    def __init__(self, session: ProfileSession):
        """
        Initialize DIDWeb.

        Args:
            session: The current profile session
        """
        self._session = session

    @property
    def session(self) -> ProfileSession:
        """
        Accessor for the current profile session.

        Returns:
            The current profile session

        """
        return self._session
    
    # @property
    # def did_document(self) -> DIDDocument:
    #     return self._did_document
    
    # @property
    # def did_document_as_json(self) -> str:
    #     LOGGER.info(self._did_document.to_json())
    #     return self._did_document.to_json()

    async def create_from_wallet(
        self, did: DID
    ) -> str:
        """Add content from wallet to DID document."""
        wallet = self.session.inject(BaseWallet, required=False)
        public_did_obj = await wallet.get_public_did()
        recipient_key = public_did_obj.verkey
        endpoint = public_did_obj.metadata["endpoint"]
        did_document = DIDDocument
        builder = DIDDocumentBuilder(did)

        vmethod = builder.verification_methods.add(
            ident="key-1", suite=SUITE, material=recipient_key
        )
        builder.authentication.reference(vmethod.id)
        builder.assertion_method.reference(vmethod.id)
        if endpoint:
            builder.services.add_didcomm(
                ident=AGENT_SERVICE_TYPE,
                type_=AGENT_SERVICE_TYPE,
                endpoint=endpoint,
                recipient_keys=[vmethod],
                routing_keys=[],
            )
        did_document = builder.build()
        await save_did_document(did_document, self._session)
        self._did_document = did_document
        return did_document.serialize()

    async def create(self, did_document) -> str:
        await save_did_document(did_document, self._session)
        self._did_document = did_document
        return did_document
       
    async def delete(self):
        await save_did_document(None, self._session)
        return None

    async def retrieve(self) -> str:
        did_document = await retrieve_did_document(self._session)
        if did_document:
            return did_document.serialize()
        else:
            return None

