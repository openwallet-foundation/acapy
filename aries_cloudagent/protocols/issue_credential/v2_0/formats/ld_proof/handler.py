"""V2.0 issue-credential linked data proof credential format handler."""


import logging
import json
from typing import List, Mapping


from ......vc.vc_ld import issue, verify_credential
from ......vc.ld_proofs import (
    Ed25519Signature2018,
    Ed25519WalletKeyPair,
    did_key_document_loader,
    LinkedDataProof,
)
from ......wallet.error import WalletNotFoundError
from ......wallet.base import BaseWallet
from ......wallet.util import did_key_to_naked, naked_to_did_key
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

LOGGER = logging.getLogger(__name__)

# TODO: move to vc util
def get_id(obj) -> str:
    if type(obj) is str:
        return obj

    if "id" not in obj:
        return

    return obj["id"]


# TODO: move to vc/proof library
SUPPORTED_PROOF_TYPES = {"Ed25519Signature2018"}


class LDProofCredFormatHandler(V20CredFormatHandler):
    """Linked data proof credential format handler."""

    format = V20CredFormat.Format.LD_PROOF

    @classmethod
    def validate_fields(cls, message_type: str, attachment_data: dict) -> None:
        # TODO: validate LDProof credential filter
        pass

    async def _assert_can_sign_with_did(self, did: str):
        async with self.profile.session() as session:
            try:
                wallet = session.inject(BaseWallet)

                # Check if issuer is something we can issue with
                assert did.startswith("did:key")
                verkey = did_key_to_naked(did)
                await wallet.get_local_did_for_verkey(verkey)
            except WalletNotFoundError:
                raise V20CredFormatError(
                    f"Issuer did {did} not found. Unable to issue credential with this DID."
                )

    async def _assert_can_sign_with_types(self, proof_types: List[str]):
        # Check if all proof types are supported
        if not set(proof_types).issubset(SUPPORTED_PROOF_TYPES):
            raise V20CredFormatError(
                f"Unsupported proof type(s): {proof_types - SUPPORTED_PROOF_TYPES}."
            )

    async def _get_suite_for_type(self, did: str, proof_type: str) -> LinkedDataProof:
        await self._assert_can_sign_with_types([proof_type])

        async with self.profile.session() as session:
            # TODO: maybe keypair should start session and inject wallet (for shorter sessions)
            wallet = session.inject(BaseWallet)

            if proof_type == "Ed25519Signature2018":
                verification_method = self._get_verification_method(did)
                verkey = did_key_to_naked(did)

                return Ed25519Signature2018(
                    verification_method=verification_method,
                    key_pair=Ed25519WalletKeyPair(
                        wallet=wallet, public_key_base58=verkey
                    ),
                )
            else:
                raise V20CredFormatError(f"Unsupported proof type {proof_type}")

    def _get_verification_method(self, did: str):
        verification_method = did + "#" + did.replace("did:key:", "")

        return verification_method

    async def create_proposal(
        self, cred_ex_record: V20CredExRecord, proposal_data: Mapping
    ) -> CredFormatAttachment:
        self.validate_fields(CRED_20_PROPOSAL, filter)

        return self.get_format_data(CRED_20_PROPOSAL, filter)

    async def receive_proposal(
        self, cred_ex_record: V20CredExRecord, cred_proposal_message: V20CredProposal
    ) -> None:
        # TODO: anything to validate here?
        pass

    async def create_offer(
        self, cred_ex_record: V20CredExRecord, offer_data: Mapping = None
    ) -> CredFormatAttachment:
        # TODO:
        #   - Use offer data
        #   - Check if all fields in credentialSubject are present in context
        #   - Check if all required fields are present (according to RFC). Or is the API going to do this?
        #   - Other checks (credentialStatus, credentialSchema, etc...)

        detail: dict = V20CredProposal.deserialize(
            cred_ex_record.cred_proposal
        ).attachment(self.format)

        credential = detail["credential"]
        options = detail["options"]

        await self._assert_can_sign_with_did(credential["issuer"])
        await self._assert_can_sign_with_types(options["proofType"])

        self.validate_fields(CRED_20_OFFER, detail)
        return self.get_format_data(CRED_20_OFFER, detail)

    async def receive_offer(
        self, cred_ex_record: V20CredExRecord, cred_offer_message: V20CredOffer
    ) -> None:
        # TODO: anything to validate here?
        pass

    async def create_request(
        self, cred_ex_record: V20CredExRecord, request_data: Mapping = None
    ) -> CredFormatAttachment:
        holder_did = request_data.get("holder_did") if request_data else None

        if cred_ex_record.cred_offer:
            cred_detail = V20CredOffer.deserialize(
                cred_ex_record.cred_offer
            ).attachment(self.format)

            if not cred_detail["credential"]["credentialSubject"]["id"] and holder_did:
                async with self.profile.session() as session:
                    wallet = session.inject(BaseWallet)

                    did_info = await wallet.get_local_did(holder_did)
                    did_key = naked_to_did_key(did_info.verkey)

                    cred_detail["credential"]["credentialSubject"]["id"] = did_key

        else:
            # TODO: start from request
            cred_detail = None

        self.validate_fields(CRED_20_REQUEST, cred_detail)
        return self.get_format_data(CRED_20_REQUEST, cred_detail)

    async def receive_request(
        self, cred_ex_record: V20CredExRecord, cred_request_message: V20CredRequest
    ) -> None:
        # TODO: check if request matches offer. (If not send problem report?)
        # TODO: validate
        pass

    async def issue_credential(
        self, cred_ex_record: V20CredExRecord, retries: int = 5
    ) -> CredFormatAttachment:
        if cred_ex_record.cred_offer:
            # TODO: match offer with request. Use request (because of credential subject id)
            cred_detail = V20CredOffer.deserialize(
                cred_ex_record.cred_offer
            ).attachment(self.format)
        else:
            cred_detail = V20CredRequest.deserialize(
                cred_ex_record.cred_request
            ).attachment(self.format)

        issuer_did = get_id(cred_detail["credential"]["issuer"])
        proof_types = cred_detail["options"]["proofType"]

        if len(proof_types) > 1:
            raise V20CredFormatError(
                "Issuing credential with multiple proof types not supported."
            )

        await self._assert_can_sign_with_did(issuer_did)
        suite = await self._get_suite_for_type(issuer_did, proof_types[0])

        # TODO: proof options
        vc = await issue(credential=cred_detail["credential"], suite=suite)

        self.validate_fields(CRED_20_ISSUE, vc)
        return self.get_format_data(CRED_20_ISSUE, vc)

    async def receive_credential(
        self, cred_ex_record: V20CredExRecord, cred_issue_message: V20CredIssue
    ) -> None:
        # TODO: validate
        pass

    async def store_credential(
        self, cred_ex_record: V20CredExRecord, cred_id: str = None
    ) -> None:
        # TODO: validate credential structure (prob in receive credential?)
        credential: dict = V20CredIssue.deserialize(
            cred_ex_record.cred_issue
        ).attachment(self.format)

        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)

            verification_method = credential.get("proof", {}).get("verificationMethod")

            if type(verification_method) is not str:
                raise V20CredFormatError(
                    "Invalid verification method on received credential"
                )
            verkey = did_key_to_naked(verification_method.split("#")[0])

            # TODO: API rework.
            suite = Ed25519Signature2018(
                verification_method=verification_method,
                key_pair=Ed25519WalletKeyPair(wallet=wallet, public_key_base58=verkey),
            )

            result = await verify_credential(
                credential=credential,
                suite=suite,
                document_loader=did_key_document_loader,
            )

            if not result.get("verified"):
                raise V20CredFormatError(
                    f"Received invalid credential: {result}",
                )

            vc_holder = session.inject(VCHolder)

            # TODO: tags
            vc_record = VCRecord(
                contexts=credential.get("@context"),
                types=credential.get("type"),
                issuer_id=get_id(credential.get("issuer")),
                # TODO: subject may be array
                subject_ids=[credential.get("credentialSubject").get("id")],
                schema_ids=[],
                value=json.dumps(credential),
                given_id=credential.get("id"),
                record_id=cred_id,
            )
            await vc_holder.store_credential(vc_record)
