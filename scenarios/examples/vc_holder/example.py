"""Test VC Holder multi-tenancy isolation."""

import asyncio
from os import getenv

from acapy_controller import Controller
from acapy_controller.logging import logging_to_stdout
from acapy_controller.models import CreateWalletResponse
from acapy_controller.protocols import DIDResult

AGENCY = getenv("AGENCY", "http://agency:3001")


async def main():
    """Test Controller protocols."""
    async with Controller(base_url=AGENCY) as agency:
        issuer = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": "Issuer",
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )
        alice = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": "Alice",
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )
        bob = await agency.post(
            "/multitenancy/wallet",
            json={
                "label": "Bob",
                "wallet_type": "askar",
            },
            response=CreateWalletResponse,
        )

    async with (
        Controller(
            base_url=AGENCY, wallet_id=alice.wallet_id, subwallet_token=alice.token
        ) as alice,
        Controller(
            base_url=AGENCY, wallet_id=bob.wallet_id, subwallet_token=bob.token
        ) as bob,
        Controller(
            base_url=AGENCY, wallet_id=issuer.wallet_id, subwallet_token=issuer.token
        ) as issuer,
    ):
        public_did = (
            await issuer.post(
                "/wallet/did/create",
                json={"method": "key", "options": {"key_type": "ed25519"}},
                response=DIDResult,
            )
        ).result
        assert public_did
        cred = await issuer.post(
            "/vc/credentials/issue",
            json={
                "credential": {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1",
                        "https://www.w3.org/2018/credentials/examples/v1",
                    ],
                    "id": "http://example.edu/credentials/1872",
                    "credentialSubject": {
                        "id": "did:example:ebfeb1f712ebc6f1c276e12ec21"
                    },
                    "issuer": public_did.did,
                    "issuanceDate": "2024-12-10T10:00:00Z",
                    "type": ["VerifiableCredential", "AlumniCredential"],
                },
                "options": {
                    "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "domain": "example.com",
                    "proofPurpose": "assertionMethod",
                    "proofType": "Ed25519Signature2018",
                },
            },
        )
        await alice.post(
            "/vc/credentials/store",
            json={"verifiableCredential": cred["verifiableCredential"]},
        )
        result = await bob.get("/vc/credentials")
        assert len(result["results"]) == 0


if __name__ == "__main__":
    logging_to_stdout()
    asyncio.run(main())
