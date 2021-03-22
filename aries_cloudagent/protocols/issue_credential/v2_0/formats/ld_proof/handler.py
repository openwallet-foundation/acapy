"""V2.0 issue-credential linked data proof credential format handler."""


import logging
import json
from typing import Mapping

from marshmallow import RAISE

from ......vc.vc_ld.models.credential_schema import VerifiableCredentialSchema
from ......vc.vc_ld.models.credential import LDProof, VerifiableCredential
from ......vc.vc_ld import issue, verify_credential
from ......vc.ld_proofs import (
    Ed25519Signature2018,
    Ed25519WalletKeyPair,
    LinkedDataProof,
    CredentialIssuancePurpose,
    ProofPurpose,
    get_default_document_loader,
)
from ......wallet.error import WalletNotFoundError
from ......wallet.base import BaseWallet
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

LOGGER = logging.getLogger(__name__)

# TODO: move to vc/proof library
SUPPORTED_PROOF_TYPES = {"Ed25519Signature2018"}


class LDProofCredFormatHandler(V20CredFormatHandler):
    """Linked data proof credential format handler."""

    format = V20CredFormat.Format.LD_PROOF

    @classmethod
    def validate_fields(cls, message_type: str, attachment_data: Mapping) -> None:
        mapping = {
            CRED_20_PROPOSAL: LDProofVCDetailSchema,
            CRED_20_OFFER: LDProofVCDetailSchema,
            CRED_20_REQUEST: LDProofVCDetailSchema,
            CRED_20_ISSUE: VerifiableCredentialSchema,
        }

        # Get schema class
        Schema = mapping[message_type]

        # Validate, throw if not valid
        # TODO: unknown should not raise
        Schema(unknown=RAISE).load(attachment_data)

    async def _assert_can_issue_with_did_and_proof_type(
        self, did: str, proof_type: str
    ):
        try:
            # We only support ed signatures at the moment
            if proof_type != "Ed25519Signature2018":
                raise V20CredFormatError(
                    f"Unable to sign credential with proof type {proof_type}"
                )
            await self._did_info_for_did(did)
        except WalletNotFoundError:
            raise V20CredFormatError(
                f"Issuer did {did} not found. Unable to issue credential with this DID."
            )

    async def _did_info_for_did(self, did: str):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)

            # If the did starts with did:sov we need to query without
            if did.startswith("did:sov:"):
                return await wallet.get_local_did(did.replace("did:sov:", ""))
            # All other methods we can just query
            else:
                return await wallet.get_local_did(did)

    async def _get_suite_for_detail(self, detail: LDProofVCDetail) -> LinkedDataProof:
        did = detail.credential.issuer_id
        proof_type = detail.options.proof_type

        await self._assert_can_issue_with_did_and_proof_type(
            did, detail.options.proof_type
        )

        proof = LDProof(
            created=detail.options.created,
            domain=detail.options.domain,
            challenge=detail.options.challenge,
        )

        did_info = await self._did_info_for_did(did)
        verification_method = self._get_verification_method(did)

        async with self.profile.session() as session:
            # TODO: maybe keypair should start session and inject wallet (for shorter sessions)
            wallet = session.inject(BaseWallet)

            # TODO: make enum or something?
            # TODO: how to abstract keypair from this step?
            if proof_type == "Ed25519Signature2018":
                return Ed25519Signature2018(
                    verification_method=verification_method,
                    proof=proof.serialize(),
                    key_pair=Ed25519WalletKeyPair(
                        wallet=wallet, public_key_base58=did_info.verkey
                    ),
                )
            else:
                raise V20CredFormatError(f"Unsupported proof type {proof_type}")

    # TODO: move to better place
    # TODO: integrate with did resolver classes (did)
    def _get_verification_method(self, did: str):
        if did.startswith("did:sov:"):
            # TODO: is this correct? uniresolver uses #key-1, SICPA uses #1
            return did + "#1"
        elif did.startswith("did:key:"):
            return DIDKey.from_did(did).key_id
        else:
            raise V20CredFormatError(
                f"Unable to get retrieve verification method for did {did}"
            )

    # TODO: move to better place
    # TODO: probably needs more input parameters
    def _get_proof_purpose(self, proof_purpose: str = None) -> ProofPurpose:
        PROOF_PURPOSE_MAP = {
            "assertionMethod": CredentialIssuancePurpose,
            # TODO: authentication
            # "authentication": AuthenticationProofPurpose,
        }

        # assertionMethod is default
        if not proof_purpose:
            proof_purpose = "assertionMethod"

        if proof_purpose not in PROOF_PURPOSE_MAP:
            raise V20CredFormatError(f"Unsupported proof purpose {proof_purpose}")

        # TODO: constructor parameters
        return PROOF_PURPOSE_MAP[proof_purpose]()

    async def create_proposal(
        self, cred_ex_record: V20CredExRecord, proposal_data: Mapping
    ) -> CredFormatAttachment:
        return self.get_format_data(CRED_20_PROPOSAL, proposal_data)

    async def receive_proposal(
        self, cred_ex_record: V20CredExRecord, cred_proposal_message: V20CredProposal
    ) -> None:
        """Receive linked data proof credential proposal"""
        # Structure validation is already done when message is received
        # no additional checking is required here
        pass

    async def create_offer(
        self, cred_ex_record: V20CredExRecord, offer_data: Mapping = None
    ) -> CredFormatAttachment:
        # TODO:
        #   - Check if all fields in credentialSubject are present in context (dropped attributes)
        #   - offer data is not passed at the moment

        # use proposal data otherwise
        if not offer_data and cred_ex_record.cred_proposal:
            offer_data = V20CredProposal.deserialize(
                cred_ex_record.cred_proposal
            ).attachment(self.format)
        else:
            raise V20CredFormatError(
                "Cannot create linked data proof offer without proposal or input data"
            )

        detail = LDProofVCDetail.deserialize(offer_data)

        await self._assert_can_issue_with_did_and_proof_type(
            detail.credential.issuer_id, detail.options.proof_type
        )

        return self.get_format_data(CRED_20_OFFER, detail.serialize())

    async def receive_offer(
        self, cred_ex_record: V20CredExRecord, cred_offer_message: V20CredOffer
    ) -> None:
        # TODO: anything to validate here?
        pass

    async def create_request(
        self, cred_ex_record: V20CredExRecord, request_data: Mapping = None
    ) -> CredFormatAttachment:
        # holder_did = request_data.get("holder_did") if request_data else None
        # TODO: add build_detail method that takes the record
        # and looks for the best detail to build (dependant on messages and role)

        # TODO: request data now contains holder did. This should
        # contain the data from the API (if starting from request)
        # if request_data:
        #     detail = LDProofVCDetail.deserialize(request_data)
        # Otherwise use offer if possible
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

            # TODO: do we want to set the credential subject id?
            # if (
            #     not cred_detail["credential"]["credentialSubject"].get("id")
            #     and holder_did
            # ):
            #     async with self.profile.session() as session:
            #         wallet = session.inject(BaseWallet)

            #         did_info = await wallet.get_local_did(holder_did)
            #         did_key = DIDKey.from_public_key_b58(
            #             did_info.verkey, KeyType.ED25519
            #         )

            #         cred_detail["credential"]["credentialSubject"]["id"] = did_key.did
        else:
            raise V20CredFormatError(
                "Cannot create linked data proof request without offer or input data"
            )

        detail = LDProofVCDetail.deserialize(request_data)

        return self.get_format_data(CRED_20_REQUEST, detail.serialize())

    async def receive_request(
        self, cred_ex_record: V20CredExRecord, cred_request_message: V20CredRequest
    ) -> None:
        # If we sent an offer, check if request matches this
        if cred_ex_record.cred_offer:
            cred_request_detail = LDProofVCDetail.deserialize(
                cred_request_message.attachment(self.format)
            )

            cred_offer_detail = LDProofVCDetail.deserialize(
                V20CredOffer.deserialize(cred_ex_record.cred_offer).attachment(
                    self.format
                )
            )

            # TODO: probably some fields can be different
            # so maybe do partial check?
            # e.g. options.challenge may be filled in request
            # OR credentialSubject.id
            # TODO: Send problem report if no match?
            assert cred_offer_detail == cred_request_detail

    async def issue_credential(
        self, cred_ex_record: V20CredExRecord, retries: int = 5
    ) -> CredFormatAttachment:
        # TODO: we need to be sure the request is matched against the offer
        # and only fields that are allowed to change can change
        detail_dict = V20CredRequest.deserialize(
            cred_ex_record.cred_request
        ).attachment(self.format)

        detail = LDProofVCDetail.deserialize(detail_dict)

        suite = await self._get_suite_for_detail(detail)
        proof_purpose = self._get_proof_purpose(detail.options.proof_purpose)

        # best to pass profile, session, ...?
        document_loader = get_default_document_loader(profile=self.profile)
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
        # TODO: validate? I think structure is already validated on a higher lever
        # And crypto stuff is better handled in store_credential
        pass

    async def store_credential(
        self, cred_ex_record: V20CredExRecord, cred_id: str = None
    ) -> None:
        cred_dict: dict = V20CredIssue.deserialize(
            cred_ex_record.cred_issue
        ).attachment(self.format)

        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)

            # TODO: extract to suite provider or something
            suites = [
                Ed25519Signature2018(
                    key_pair=Ed25519WalletKeyPair(wallet=wallet),
                )
            ]

            result = await verify_credential(
                credential=cred_dict,
                suites=suites,
                document_loader=get_default_document_loader(self.profile),
            )

            if not result.verified:
                raise V20CredFormatError(f"Received invalid credential: {result}")

            vc_holder = session.inject(VCHolder)
            credential = VerifiableCredential.deserialize(cred_dict)

            # TODO: tags
            vc_record = VCRecord(
                contexts=credential.context_urls,
                types=credential.type,
                issuer_id=credential.issuer_id,
                subject_ids=[credential.credential_subject_ids],
                schema_ids=[],  # Schemas not supported yet
                value=json.dumps(credential.serialize()),
                given_id=credential.id,
                record_id=cred_id,
            )
            await vc_holder.store_credential(vc_record)
