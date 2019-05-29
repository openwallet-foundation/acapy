import logging

from vonx.common.eventloop import run_coro

from api_indy.tob_anchor.boot import indy_client, indy_holder_id

LOGGER = logging.getLogger(__name__)


class CredentialOfferManager(object):
    """
    Handles credential offer from issuer.
    """
    def __init__(self, credential_offer: dict, credential_def_id: str) -> None:
        self.credential_offer = credential_offer
        self.credential_def_id = credential_def_id

    def generate_credential_request(self):
        """Generates a credential request

        Returns:
            tuple -- credential_request, credential_request_metadata
        """
        async def run():
            cred_req = await indy_client().create_credential_request(
                indy_holder_id(),
                self.credential_offer,
                self.credential_def_id,
            )
            return cred_req.data, cred_req.metadata

        return run_coro(run())
