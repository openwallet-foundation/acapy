"""DID Key operator class."""

from ...wallet.key_type import KeyType
from ...wallet.did_method import KEY
from ...wallet.base import BaseWallet


class DidKeyOperator:
    """Operator for managing key dids."""

    def __init__(self, profile):
        """Initialize a new `DidKeyOperator` instance."""
        self.profile = profile


    async def register_did(
        self,
        key_type: KeyType,
    ):
        """Register a new key DID.

        Args:
            key_type: The key type to use for the DID

        Returns:
            A `DIDDocument` instance representing the created DID

        Raises:
            DidWebOperatorError: If the an error occures during did registration

        """
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
        info = await wallet.create_local_did(
            method=KEY, key_type=key_type
        )
        return await self.create_did_doc(info.did)
    
    async def create_did_doc(
        self,
        did: str,
    ):
        """Creates a DID doc based on a did:key value.

        Args:
            did: The did:key value

        Returns:
            A `DIDDocument` instance representing the created DID

        Raises:
            DidWebOperatorError: If the an error occures during did registration

        """
        verification_method = f'{did}#'+did.split(':')[-1]
        return {
            "@context": [
                'https://www.w3.org/ns/did/v1',
                'https://w3id.org/security/multikey/v1'
            ],
            "id": did,
            "verificationMethod": [
                {
                    "id": verification_method,
                    "type": "MultiKey",
                    "controller": did,
                    "publicKeyMultibase": did.split(':')[-1],
                },
            ],
            "authentication": [verification_method],
            "assertionMethod": [verification_method],
            "capabilityDelegation": [verification_method],
            "capabilityInvocation": [verification_method],
            "keyAgreement": [],
        }