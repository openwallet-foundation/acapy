from datetime import datetime, timedelta
from typing import Awaitable
from .ControllerProofPurpose import ControllerProofPurpose


class PublicKeyProofPurpose(ControllerProofPurpose):
    def __init__(
        self, controller: dict, date: datetime, max_timestamp_delta: timedelta = None
    ):
        super().__init__("publicKey", controller, date, max_timestamp_delta)

    async def update(self, proof: dict) -> Awaitable[dict]:
        return proof

    async def match(self, proof: dict) -> Awaitable[bool]:
        return proof.get("proofPurpose") is None


__all__ = [PublicKeyProofPurpose]
