"""V2.0 issue-credential linked data proof credential format handler."""

import logging
from typing import Mapping

from marshmallow import RAISE

from ......vc.vc_ld import (
    issue,
    verify_credential,
    VerifiableCredentialSchema,
    LDProof,
    VerifiableCredential,
)
from ......vc.ld_proofs import (
    Ed25519Signature2018,
    BbsBlsSignature2020,
    WalletKeyPair,
    LinkedDataProof,
    CredentialIssuancePurpose,
    ProofPurpose,
    get_default_document_loader,
    AuthenticationProofPurpose,
    SECURITY_CONTEXT_BBS_URL,
)
from ......wallet.crypto import KeyType
from ......wallet.error import WalletNotFoundError
from ......wallet.base import BaseWallet, DIDInfo
from ......did.did_key import DIDKey
from ......storage.vc_holder.base import VCHolder
from ......storage.vc_holder.vc_record import VCRecord

from ...message_types import (
    CRED_20_ISSUE,
    CRED_20_OFFER,
    CRED_20_PROPOSAL,
    CRED_20_REQUEST,
)
from ...messages.cred_format import V20CredFormat
from ...messages.cred_offer import V20CredOffer
from ...messages.cred_proposal import V20CredProposal
from ...messages.cred_issue import V20CredIssue
from ...messages.cred_request import V20CredRequest
from ...models.cred_ex_record import V20CredExRecord
from ..handler import CredFormatAttachment, V20CredFormatError, V20CredFormatHandler
from .models.cred_detail_schema import LDProofVCDetailSchema
from .models.cred_detail import LDProofVCDetail
from ...models.detail.ld_proof import V20CredExRecordLDProof

LOGGER = logging.getLogger(__name__)

SUPPORTED_ISSUANCE_PROOF_PURPOSES = {
    CredentialIssuancePurpose.term,
    AuthenticationProofPurpose.term,
}

SUPPORTED_ISSUANCE_SUITES = {Ed25519Signature2018, BbsBlsSignature2020}

SIGNATURE_SUITE_KEY_TYPE_MAPPING = {
    Ed25519Signature2018: KeyType.ED25519,
    BbsBlsSignature2020: KeyType.BLS12381G2,
}

PROOF_TYPE_SIGNATURE_SUITE_MAPPING = {
    suite.signature_type: suite
    for suite, key_type in SIGNATURE_SUITE_KEY_TYPE_MAPPING.items()
}

KEY_TYPE_SIGNATURE_SUITE_MAPPING = {
    key_type: suite for suite, key_type in SIGNATURE_SUITE_KEY_TYPE_MAPPING.items()
}


class LDProofCredFormatHandler(V20CredFormatHandler):
    """Linked data proof credential format handler."""

    format = V20CredFormat.Format.LD_PROOF

    @classmethod
    def validate_fields(cls, message_type: str, attachment_data: Mapping) -> None:
        """Validate attachment data for a specific message type.

        Uses marshmallow schemas to validate if format specific attachment data
        is valid for the specified message type. Only does structural and type
        checks, does not validate if .e.g. the issuer value is valid.


        Args:
            message_type (str): The message type to validate the attachment data for.
                Should be one of the message types as defined in message_types.py
            attachment_data (Mapping): [description]
                The attachment data to valide

        Raises:
            Exception: When the data is not valid.

        """
        mapping = {
            CRED_20_PROPOSAL: LDProofVCDetailSchema,
            CRED_20_OFFER: LDProofVCDetailSchema,
            CRED_20_REQUEST: LDProofVCDetailSchema,
            CRED_20_ISSUE: VerifiableCredentialSchema,
        }

        # Get schema class
        Schema = mapping[message_type]

        # Validate, throw if not valid
        Schema(unknown=RAISE).load(attachment_data)

    async def _assert_can_issue_with_id_and_proof_type(
        self, issuer_id: str, proof_type: str
    ):
        """Assert that it is possible to issue using the specified id and proof type.

        Args:
            issuer_id (str): The issuer id
            proof_type (str): the signature suite proof type

        Raises:
            V20CredFormatError:
                - If the proof type is not supported
                - If the issuer id is not a did
                - If the did is not found in th wallet
                - If the did does not support to create signatures for the proof type

        """
        try:
            # Check if it is a proof type we can issue with
            if proof_type not in PROOF_TYPE_SIGNATURE_SUITE_MAPPING.keys():
                raise V20CredFormatError(
                    f"Unable to sign credential with unsupported proof type {proof_type}"
                    f". Supported proof types: {PROOF_TYPE_SIGNATURE_SUITE_MAPPING.keys()}"
                )

            if not issuer_id.startswith("did:"):
                raise V20CredFormatError(
                    f"Unable to issue credential with issuer id: {issuer_id}."
                    " Only issuance with DIDs is supported"
                )

            # Retrieve did from wallet. Will throw if not found
            did = await self._did_info_for_did(issuer_id)

            # Raise error if we cannot issue a credential with this proof type
            # using this DID from
            did_proof_type = KEY_TYPE_SIGNATURE_SUITE_MAPPING[
                did.key_type
            ].signature_type
            if proof_type != did_proof_type:
                raise V20CredFormatError(
                    f"Unable to issue credential with issuer id {issuer_id} and proof "
                    f"type {proof_type}. DID only supports proof type {did_proof_type}"
                )

        except WalletNotFoundError:
            raise V20CredFormatError(
                f"Issuer did {issuer_id} not found."
                " Unable to issue credential with this DID."
            )

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

    async def _get_suite_for_detail(self, detail: LDProofVCDetail) -> LinkedDataProof:
        issuer_id = detail.credential.issuer_id
        proof_type = detail.options.proof_type

        # Assert we can issue the credential based on issuer + proof_type
        await self._assert_can_issue_with_id_and_proof_type(
            issuer_id, detail.options.proof_type
        )

        # Create base proof object with options from detail
        proof = LDProof(
            created=detail.options.created,
            domain=detail.options.domain,
            challenge=detail.options.challenge,
        )

        did_info = await self._did_info_for_did(issuer_id)
        verification_method = self._get_verification_method(issuer_id)

        suite = await self._get_suite(
            proof_type=proof_type,
            verification_method=verification_method,
            proof=proof.serialize(),
            did_info=did_info,
        )

        return suite

    async def _get_suite(
        self,
        *,
        proof_type: str,
        verification_method: str = None,
        proof: dict = None,
        did_info: DIDInfo = None,
    ):
        """Get signature suite for issuance of verification."""
        async with self.profile.session() as session:
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

    def _get_verification_method(self, did: str):
        """Get the verification method for a did."""

        if did.startswith("did:key:"):
            return DIDKey.from_did(did).key_id
        else:
            raise V20CredFormatError(
                f"Unable to get retrieve verification method for did {did}"
            )

    def _get_proof_purpose(
        self, *, proof_purpose: str, challenge: str = None, domain: str = None
    ) -> ProofPurpose:
        """Get the proof purpose for a credential detail.

        Args:
            proof_purpose (str): The proof purpose string value
            challenge (str, optional): Challenge
            domain (str, optional): domain

        Raises:
            V20CredFormatError:
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
                raise V20CredFormatError(
                    f"Challenge is required for '{proof_purpose}' proof purpose."
                )

            return AuthenticationProofPurpose(challenge=challenge, domain=domain)
        else:
            raise V20CredFormatError(
                f"Unsupported proof purse: {proof_purpose}. "
                f"Supported  proof types are: {SUPPORTED_ISSUANCE_PROOF_PURPOSES}"
            )

    async def _prepare_detail(self, detail: LDProofVCDetail) -> LDProofVCDetail:
        # Add BBS context if not present yet
        if (
            detail.options.proof_type == BbsBlsSignature2020.signature_type
            and SECURITY_CONTEXT_BBS_URL not in detail.credential.context_urls
        ):
            detail.credential.add_context(SECURITY_CONTEXT_BBS_URL)

    async def create_proposal(
        self, cred_ex_record: V20CredExRecord, proposal_data: Mapping
    ) -> CredFormatAttachment:
        """Create linked data proof credential proposal."""
        detail = LDProofVCDetail.deserialize(proposal_data)
        detail = await self._prepare_detail(detail)

        return self.get_format_data(CRED_20_PROPOSAL, detail.serialize())

    async def receive_proposal(
        self, cred_ex_record: V20CredExRecord, cred_proposal_message: V20CredProposal
    ) -> None:
        """Receive linked data proof credential proposal."""

    async def create_offer(
        self, cred_ex_record: V20CredExRecord
    ) -> CredFormatAttachment:
        """Create linked data proof credential offer."""
        if not cred_ex_record.cred_proposal:
            raise V20CredFormatError(
                "Cannot create linked data proof offer without proposal or input data"
            )

        # Parse proposal. Data is stored in proposal if we received a proposal
        # but also when we create an offer (manager does some weird stuff)
        offer_data = V20CredProposal.deserialize(
            cred_ex_record.cred_proposal
        ).attachment(self.format)
        detail = LDProofVCDetail.deserialize(offer_data)
        detail = await self._prepare_detail(detail)

        # Make sure we can issue with the did and proof type
        await self._assert_can_issue_with_id_and_proof_type(
            detail.credential.issuer_id, detail.options.proof_type
        )

        return self.get_format_data(CRED_20_OFFER, detail.serialize())

    async def receive_offer(
        self, cred_ex_record: V20CredExRecord, cred_offer_message: V20CredOffer
    ) -> None:
        """Receive linked data proof credential offer."""

    async def create_request(
        self, cred_ex_record: V20CredExRecord
    ) -> CredFormatAttachment:
        """Create linked data proof credential request."""
        if cred_ex_record.cred_offer:
            request_data = V20CredOffer.deserialize(
                cred_ex_record.cred_offer
            ).attachment(self.format)
        # API data is stored in proposal (when starting from request)
        # It is a bit of a strage flow IMO.
        elif cred_ex_record.cred_proposal:
            request_data = V20CredProposal.deserialize(
                cred_ex_record.cred_proposal
            ).attachment(self.format)
        else:
            raise V20CredFormatError(
                "Cannot create linked data proof request without offer or input data"
            )

        detail = LDProofVCDetail.deserialize(request_data)
        detail = await self._prepare_detail(detail)

        return self.get_format_data(CRED_20_REQUEST, detail.serialize())

    async def receive_request(
        self, cred_ex_record: V20CredExRecord, cred_request_message: V20CredRequest
    ) -> None:
        """Receive linked data proof request."""

    async def issue_credential(
        self, cred_ex_record: V20CredExRecord, retries: int = 5
    ) -> CredFormatAttachment:
        """Issue linked data proof credential."""
        detail_dict = V20CredRequest.deserialize(
            cred_ex_record.cred_request
        ).attachment(self.format)
        detail = LDProofVCDetail.deserialize(detail_dict)
        detail = await self._prepare_detail(detail)

        # Get signature suite, proof purpose and document loader
        suite = await self._get_suite_for_detail(detail)
        proof_purpose = self._get_proof_purpose(
            proof_purpose=detail.options.proof_purpose,
            challenge=detail.options.challenge,
            domain=detail.options.domain,
        )
        document_loader = get_default_document_loader(profile=self.profile)

        # issue the credential
        vc = await issue(
            credential=detail.credential.serialize(),
            suite=suite,
            document_loader=document_loader,
            purpose=proof_purpose,
        )

        return self.get_format_data(CRED_20_ISSUE, vc)

    async def receive_credential(
        self, cred_ex_record: V20CredExRecord, cred_issue_message: V20CredIssue
    ) -> None:
        """Receive linked data proof credential."""
        cred_dict = cred_issue_message.attachment(self.format)
        detail_dict = V20CredRequest.deserialize(
            cred_ex_record.cred_request
        ).attachment(self.format)

        vc = VerifiableCredential.deserialize(cred_dict)
        detail = LDProofVCDetail.deserialize(detail_dict)

        # Remove values from cred that are not part of detail
        cred_dict.pop("proof")
        credential_status = cred_dict.pop("credentialStatus", None)
        detail_status = detail.options.credential_status

        if cred_dict != detail_dict["credential"]:
            raise V20CredFormatError(
                f"Received credential for cred_ex_id {cred_ex_record.cred_ex_id} does not"
                " match requested credential"
            )

        # both credential and detail contain status. Check for equalness
        if credential_status and detail_status:
            if credential_status.get("type") != detail_status.get("type"):
                raise V20CredFormatError(
                    "Received credential status type does not match credential request"
                )
        # Either credential or detail contains status. Throw error
        elif (credential_status and not detail_status) or (
            not credential_status and detail_status
        ):
            raise V20CredFormatError(
                "Received credential status contains credential status"
                " that does not match credential request"
            )

        # TODO: if created wasn't present in the detail options, should we verify
        # it is ~now (e.g. some time in the past + future)?
        # Check if created property matches
        if detail.options.created and vc.proof.created != detail.options.created:
            raise V20CredFormatError(
                "Received credential proof.created does not"
                " match options.created from credential request"
            )

        # Check if proof type matches
        if vc.proof.type != detail.options.proof_type:
            raise V20CredFormatError(
                "Received credential proof.type does not"
                " match options.proofType from credential request"
            )

    async def store_credential(
        self, cred_ex_record: V20CredExRecord, cred_id: str = None
    ) -> None:
        """Store linked data proof credential."""
        # Get attachment data
        cred_dict: dict = V20CredIssue.deserialize(
            cred_ex_record.cred_issue
        ).attachment(self.format)

        # Deserialize objects
        credential = VerifiableCredential.deserialize(cred_dict)

        # Get signature suite, proof purpose and document loader
        suite = await self._get_suite(proof_type=credential.proof.type)

        purpose = self._get_proof_purpose(
            proof_purpose=credential.proof.proof_purpose,
            challenge=credential.proof.challenge,
            domain=credential.proof.domain,
        )
        document_loader = get_default_document_loader(self.profile)

        # Verify the credential
        result = await verify_credential(
            credential=cred_dict,
            suites=[suite],
            document_loader=document_loader,
            purpose=purpose,
        )

        if not result.verified:
            raise V20CredFormatError(f"Received invalid credential: {result}")

        # create VC record for storage
        vc_record = VCRecord(
            contexts=credential.context_urls,
            types=credential.type,
            issuer_id=credential.issuer_id,
            subject_ids=credential.credential_subject_ids,
            schema_ids=[],  # Schemas not supported yet
            proof_types=[credential.proof.type],
            cred_value=credential.serialize(),
            given_id=credential.id,
            record_id=cred_id,
            cred_tags=None,  # Tags should be derived from credential values
        )

        # Create detail record with cred_id_stored
        detail_record = V20CredExRecordLDProof(
            cred_ex_id=cred_ex_record.cred_ex_id, cred_id_stored=vc_record.record_id
        )

        # save credential and detail record
        async with self.profile.session() as session:
            vc_holder = session.inject(VCHolder)

            await vc_holder.store_credential(vc_record)
            await detail_record.save(session, reason="store credential v2.0")
