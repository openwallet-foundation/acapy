import json
import logging
from collections import namedtuple

from api_indy.tob_anchor.boot import indy_client, indy_holder_id
from vonx.common.eventloop import run_coro


LOGGER = logging.getLogger(__name__)


Filter = namedtuple("Filter", "claim_name claim_value")


class ProofException(Exception):
    pass


class ProofManager(object):
    """
    Class to manage creation of indy proofs.
    """

    def __init__(self, proof_request: dict, credential_ids: set = None) -> None:
        """Constructor

        Arguments:
            proof_request {dict} -- valid indy proof request
        """

        self.proof_request = proof_request
        self.credential_ids = credential_ids
        self.filters = []

    def add_filter(self, claim_name: str, claim_value: str):
        self.filters.append(Filter(claim_name, claim_value))

    def construct_proof(self):
        return run_coro(self.construct_proof_async())

    async def construct_proof_async(self):
        proof = await indy_client().construct_proof(
            indy_holder_id(),
            self.proof_request,
            None, # wql filters
            self.credential_ids,
        )

        return proof.proof
