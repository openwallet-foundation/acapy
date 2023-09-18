"""Manager for performing Linked Data Proof signatures over JSON-LD formatted W3C VCs."""


from typing import Optional

from aries_cloudagent.vc.ld_proofs.constants import (
    SECURITY_CONTEXT_BBS_URL,
    SECURITY_CONTEXT_ED25519_2020_URL,
)
from aries_cloudagent.vc.ld_proofs.document_loader import DocumentLoader

from ...core.profile import Profile
from ...wallet.base import BaseWallet
from ...wallet.default_verification_key_strategy import BaseVerificationKeyStrategy
from ...wallet.did_info import DIDInfo
from ...wallet.error import WalletNotFoundError
from ...wallet.key_type import BLS12381G2, ED25519
from ..ld_proofs.crypto.wallet_key_pair import WalletKeyPair
from ..ld_proofs.purposes.authentication_proof_purpose import AuthenticationProofPurpose
from ..ld_proofs.purposes.credential_issuance_purpose import CredentialIssuancePurpose
from ..ld_proofs.purposes.proof_purpose import ProofPurpose
from ..ld_proofs.suites.bbs_bls_signature_2020 import BbsBlsSignature2020
from ..ld_proofs.suites.ed25519_signature_2018 import Ed25519Signature2018
from ..ld_proofs.suites.ed25519_signature_2020 import Ed25519Signature2020
from ..ld_proofs.suites.linked_data_proof import LinkedDataProof
from .issue import issue as ldp_issue
from .models.credential import VerifiableCredential
from .models.linked_data_proof import LDProof
from .models.options import LDProofVCOptions


SUPPORTED_ISSUANCE_PROOF_PURPOSES = {
    CredentialIssuancePurpose.term,
    AuthenticationProofPurpose.term,
}
SUPPORTED_ISSUANCE_SUITES = {Ed25519Signature2018, Ed25519Signature2020}
SIGNATURE_SUITE_KEY_TYPE_MAPPING = {
    Ed25519Signature2018: ED25519,
    Ed25519Signature2020: ED25519,
}


# We only want to add bbs suites to supported if the module is installed
if BbsBlsSignature2020.BBS_SUPPORTED:
    SUPPORTED_ISSUANCE_SUITES.add(BbsBlsSignature2020)
    SIGNATURE_SUITE_KEY_TYPE_MAPPING[BbsBlsSignature2020] = BLS12381G2


PROOF_TYPE_SIGNATURE_SUITE_MAPPING = {
    suite.signature_type: suite for suite in SIGNATURE_SUITE_KEY_TYPE_MAPPING
}


# key_type -> set of signature types mappings
KEY_TYPE_SIGNATURE_TYPE_MAPPING = {
    key_type: {
        suite.signature_type
        for suite, kt in SIGNATURE_SUITE_KEY_TYPE_MAPPING.items()
        if kt == key_type
    }
    for key_type in SIGNATURE_SUITE_KEY_TYPE_MAPPING.values()
}


class VcLdpManagerError(Exception):
    """Generic VcLdpManager Error."""


class VcLdpManager:
    """Class for managing Linked Data Proof signatures over JSON-LD formatted W3C VCs."""

    def __init__(self, profile: Profile):
        """Initialize the VC LD Proof Manager."""
        self.profile = profile

    async def _did_info_for_did(self, did: str) -> DIDInfo:
        """Get the did info for specified did.

        If the did starts with did:sov it will remove the prefix for
        backwards compatibility with not fully qualified did.

        Args:
            did (str): The did to retrieve from the wallet.

        Raises:
            WalletNotFoundError: If the did is not found in the wallet.

        Returns:
            DIDInfo: did information

        """
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)

            # If the did starts with did:sov we need to query without
            if did.startswith("did:sov:"):
                return await wallet.get_local_did(did.replace("did:sov:", ""))

            # All other methods we can just query
            return await wallet.get_local_did(did)

    async def _assert_can_issue_with_id_and_proof_type(
        self, issuer_id: str, proof_type: str
    ):
        """Assert that it is possible to issue using the specified id and proof type.

        Args:
            issuer_id (str): The issuer id
            proof_type (str): the signature suite proof type

        Raises:
            VcLdpManagerError:
                - If the proof type is not supported
                - If the issuer id is not a did
                - If the did is not found in th wallet
                - If the did does not support to create signatures for the proof type

        """
        try:
            # Check if it is a proof type we can issue with
            if proof_type not in PROOF_TYPE_SIGNATURE_SUITE_MAPPING.keys():
                raise VcLdpManagerError(
                    f"Unable to sign credential with unsupported proof type {proof_type}."
                    f" Supported proof types: {PROOF_TYPE_SIGNATURE_SUITE_MAPPING.keys()}"
                )

            if not issuer_id.startswith("did:"):
                raise VcLdpManagerError(
                    f"Unable to issue credential with issuer id: {issuer_id}."
                    " Only issuance with DIDs is supported"
                )

            # Retrieve did from wallet. Will throw if not found
            did = await self._did_info_for_did(issuer_id)

            # Raise error if we cannot issue a credential with this proof type
            # using this DID from
            did_proof_types = KEY_TYPE_SIGNATURE_TYPE_MAPPING[did.key_type]
            if proof_type not in did_proof_types:
                raise VcLdpManagerError(
                    f"Unable to issue credential with issuer id {issuer_id} and proof "
                    f"type {proof_type}. DID only supports proof types {did_proof_types}"
                )

        except WalletNotFoundError:
            raise VcLdpManagerError(
                f"Issuer did {issuer_id} not found."
                " Unable to issue credential with this DID."
            )

    async def _get_suite(
        self,
        *,
        proof_type: str,
        verification_method: Optional[str] = None,
        proof: Optional[dict] = None,
        did_info: Optional[DIDInfo] = None,
    ):
        """Get signature suite for issuance of verification."""
        session = await self.profile.session()
        wallet = session.inject(BaseWallet)

        # Get signature class based on proof type
        SignatureClass = PROOF_TYPE_SIGNATURE_SUITE_MAPPING[proof_type]

        # Generically create signature class
        return SignatureClass(
            verification_method=verification_method,
            proof=proof,
            key_pair=WalletKeyPair(
                wallet=wallet,
                key_type=SIGNATURE_SUITE_KEY_TYPE_MAPPING[SignatureClass],
                public_key_base58=did_info.verkey if did_info else None,
            ),
        )

    def _get_proof_purpose(
        self,
        *,
        proof_purpose: Optional[str] = None,
        challenge: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> ProofPurpose:
        """Get the proof purpose for a credential.

        Args:
            proof_purpose (str): The proof purpose string value
            challenge (str, optional): Challenge
            domain (str, optional): domain

        Raises:
            VcLdpManagerError:
                - If the proof purpose is not supported.
                - [authentication] If challenge is missing.

        Returns:
            ProofPurpose: Proof purpose instance that can be used for issuance.

        """
        # Default proof purpose is assertionMethod
        proof_purpose = proof_purpose or CredentialIssuancePurpose.term

        if proof_purpose == CredentialIssuancePurpose.term:
            return CredentialIssuancePurpose()
        elif proof_purpose == AuthenticationProofPurpose.term:
            # assert challenge is present for authentication proof purpose
            if not challenge:
                raise VcLdpManagerError(
                    f"Challenge is required for '{proof_purpose}' proof purpose."
                )

            return AuthenticationProofPurpose(challenge=challenge, domain=domain)
        else:
            raise VcLdpManagerError(
                f"Unsupported proof purpose: {proof_purpose}. "
                f"Supported  proof types are: {SUPPORTED_ISSUANCE_PROOF_PURPOSES}"
            )

    async def _prepare_credential(
        self,
        credential: VerifiableCredential,
        options: LDProofVCOptions,
        holder_did: Optional[str] = None,
    ) -> VerifiableCredential:
        # Add BBS context if not present yet
        assert options and isinstance(options, LDProofVCOptions)
        assert credential and isinstance(credential, VerifiableCredential)
        if (
            options.proof_type == BbsBlsSignature2020.signature_type
            and SECURITY_CONTEXT_BBS_URL not in credential.context_urls
        ):
            credential.add_context(SECURITY_CONTEXT_BBS_URL)
        # Add ED25519-2020 context if not present yet
        elif (
            options.proof_type == Ed25519Signature2020.signature_type
            and SECURITY_CONTEXT_ED25519_2020_URL not in credential.context_urls
        ):
            credential.add_context(SECURITY_CONTEXT_ED25519_2020_URL)

        # Permit late binding of credential subject:
        # IFF credential subject doesn't already have an id, add holder_did as
        # credentialSubject.id (if provided)
        subject = credential.credential_subject

        # TODO if credential subject is a list, we're only binding the first...
        # How should this be handled?
        if isinstance(subject, list):
            subject = subject[0]

        if not subject:
            raise VcLdpManagerError("Credential subject is required")

        if holder_did and holder_did.startswith("did:key") and "id" not in subject:
            subject["id"] = holder_did

        return credential

    async def _get_suite_for_credential(
        self, credential: VerifiableCredential, options: LDProofVCOptions
    ) -> LinkedDataProof:
        issuer_id = credential.issuer_id
        proof_type = options.proof_type

        if not issuer_id:
            raise VcLdpManagerError("Credential issuer id is required")

        if not proof_type:
            raise VcLdpManagerError("Proof type is required")

        # Assert we can issue the credential based on issuer + proof_type
        await self._assert_can_issue_with_id_and_proof_type(issuer_id, proof_type)

        # Create base proof object with options
        proof = LDProof(
            created=options.created,
            domain=options.domain,
            challenge=options.challenge,
        )

        did_info = await self._did_info_for_did(issuer_id)
        verkey_id_strategy = self.profile.context.inject(BaseVerificationKeyStrategy)
        verification_method = (
            options.verification_method
            or await verkey_id_strategy.get_verification_method_id_for_did(
                issuer_id, self.profile, proof_purpose="assertionMethod"
            )
        )

        if verification_method is None:
            raise VcLdpManagerError(
                f"Unable to get retrieve verification method for did {issuer_id}"
            )

        suite = await self._get_suite(
            proof_type=proof_type,
            verification_method=verification_method,
            proof=proof.serialize(),
            did_info=did_info,
        )

        return suite

    async def issue(self, credential: VerifiableCredential, options: LDProofVCOptions):
        """Sign a VC with a Linked Data Proof."""
        credential = await self._prepare_credential(credential, options)

        # Get signature suite, proof purpose and document loader
        suite = await self._get_suite_for_credential(credential, options)
        proof_purpose = self._get_proof_purpose(
            proof_purpose=options.proof_purpose,
            challenge=options.challenge,
            domain=options.domain,
        )
        document_loader = self.profile.inject(DocumentLoader)

        # issue the credential
        vc = await ldp_issue(
            credential=credential.serialize(),
            suite=suite,
            document_loader=document_loader,
            purpose=proof_purpose,
        )
        return vc

    async def verify_presentation(self):
        """Verify a VP with a Linked Data Proof."""

    async def verify_credential(self):
        """Verify a VC with a Linked Data Proof."""
