from .ControllerProofPurpose import ControllerProofPurpose
from datetime import datetime, timedelta
from typing import Awaitable


class AuthenticationProofPurpose(ControllerProofPurpose):
  def __init__(
      self,
      controller: dict,
      challenge: str,
      date: datetime,
      domain: str = None,
      max_timestamp_delta: timedelta = None):
    super(ControllerProofPurpose, self).__init__(
        'authentication', controller, date, max_timestamp_delta)
    self.challenge = challenge
    self.domain = domain

  async def validate(
      self, proof: dict, verification_method: dict,
      document_loader: callable) -> Awaitable[dict]:
    try:
      if proof['challenge'] != self.challenge:
        raise Exception(
            f'The challenge is not expected; challenge={proof["challenge"]}, expected=[self.challenge]'
        )

      if self.domain and (proof['domain'] != self.domain):
        raise Exception(
            f'The domain is not as expected; domain={proof["domain"]}, expected={self.domain}'
        )

      return await super(ControllerProofPurpose, self).validate(
          proof, verification_method, document_loader)
    except Exception as e:
      return {'valid': False, 'eror': e}

  async def update(self, proof: dict) -> Awaitable[dict]:
    proof = await super().update(proof)
    proof['challenge'] = self.challenge

    if self.domain:
      proof['domain'] = self.domain

    return proof
