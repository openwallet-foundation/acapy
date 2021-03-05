"""V2.0 indy issue-credential cred format."""

import logging

import uuid
import json
from typing import Mapping, Tuple


from .....messaging.decorators.attach_decorator import AttachDecorator

from .....wallet.error import WalletNotFoundError
from .....wallet.base import BaseWallet
from .....wallet.util import did_key_to_naked
from ..messages.cred_format import V20CredFormat
from ..messages.cred_offer import V20CredOffer
from ..messages.cred_request import V20CredRequest
from ..models.cred_ex_record import V20CredExRecord
from ..formats.handler import V20CredFormatError, V20CredFormatHandler

LOGGER = logging.getLogger(__name__)

# TODO: move to vc util
def get_id(obj) -> str:
    if type(obj) is str:
        return obj

    if "id" not in obj:
        return

    return obj["id"]


class LDProofCredFormatHandler(V20CredFormatHandler):

    format = V20CredFormat.Format.LD_PROOF

    @classmethod
    def validate_filter(cls, data: Mapping):
        # TODO: validate LDProof credential filter
        pass

    async def create_proposal(
        self, cred_ex_record: V20CredExRecord, filter: Mapping[str, str]
    ) -> Tuple[V20CredFormat, AttachDecorator]:
        id = uuid.uuid4()

        return (
            V20CredFormat(attach_id=id, format_=self.format),
            AttachDecorator.data_base64(filter, ident=id),
        )

    async def receive_offer(
        self, cred_ex_record: V20CredExRecord, cred_offer_message: V20CredOffer
    ):
        pass

    # TODO: add filter
    async def create_offer(
        self, cred_ex_record: V20CredExRecord, filter: Mapping = None
    ) -> Tuple[V20CredFormat, AttachDecorator]:
        wallet = self.profile.inject(BaseWallet)

        # TODO:
        #   - Check if first @context is "https://www.w3.org/2018/credentials/v1"
        #   - Check if first type is "VerifiableCredential"
        #   - Check if all fields in credentialSubject are present in context
        #   - Check if all required fields are present (according to RFC). Or is the API going to do this?
        #   - Other checks (credentialStatus, credentialSchema, etc...)

        try:
            # Check if issuer is something we can issue with
            issuer_did = get_id(filter["issuer"])
            assert issuer_did.startswith(issuer_did, "did:key")
            verkey = did_key_to_naked(issuer_did)
            did_info = await wallet.get_local_did_for_verkey(verkey)

            # Check if all proposed proofTypes are supported
            supported_proof_types = {"Ed25519VerificationKey2018"}
            proof_types = set(filter["proofTypes"])
            if not set(proof_types).issubset(supported_proof_types):
                raise V20CredFormatError(
                    f"Unsupported proof type(s): {proof_types - supported_proof_types}."
                )

        except WalletNotFoundError:
            raise V20CredFormatError(
                f"Issuer did {did_info} not found. Unable to issue credential with this DID."
            )

        id = uuid.uuid4()
        return (
            V20CredFormat(attach_id=id, format_=self.format),
            AttachDecorator.data_base64(filter, ident=id),
        )

    async def create_request(
        self,
        cred_ex_record: V20CredExRecord,
        # TODO subject id?
        holder_did: str = None,
    ):
        if cred_ex_record.cred_offer:
            cred_detail = V20CredOffer.deserialize(cred_ex_record.cred_offer).offer(
                self.format
            )

            if not cred_detail["credentialSubject"]["id"] and holder_did:
                # TODO: holder_did is not always did, must transform first
                cred_detail["credentialSubject"]["id"] = holder_did
        else:
            # TODO: start from request
            cred_detail = None

        id = uuid.uuid4()
        return (
            V20CredFormat(attach_id=id, format_=self.format),
            AttachDecorator.data_base64(cred_detail, ident=id),
        )

    async def receive_request(
        self, cred_ex_record: V20CredExRecord, cred_request_message: V20CredRequest
    ):
        pass

    async def issue_credential(self, cred_ex_record: V20CredExRecord, retries: int = 5):
        if cred_ex_record.cred_offer:
            cred_detail = V20CredOffer.deserialize(cred_ex_record.cred_offer).offer(
                self.format
            )
        else:
            cred_detail = V20CredRequest.deserialize(
                cred_ex_record.cred_request
            ).cred_request(self.format)

        # TODO: create credential
        # TODO: issue with public did:sov
        vc = cred_detail

        id = uuid.uuid4()
        return (
            V20CredFormat(attach_id=id, format_=self.format),
            AttachDecorator.data_base64(json.loads(vc), ident=id),
        )

    async def store_credential(self, cred_ex_record: V20CredExRecord, cred_id: str):
        pass