import datetime


class ProofPurpose:
  def __init__(
      self,
      term: str,
      date: datetime.datetime,
      max_timestamp_delta: datetime.timedelta = None):
    self.term = term
    self.date = date
    self.max_timestamp_delta = max_timestamp_delta

  def validate(self, proof: dict) -> bool:
    try:
      if self.max_timestamp_delta is not None:
        expected = self.date.time()
        created = datetime.datetime.strptime(
            proof['created'], "%Y-%m-%dT%H:%M:%SZ")

        if not (created >= (expected - self.max_timestamp_delta) and created <=
                (expected + self.max_timestamp_delta)):
          raise Exception('The proof\'s created timestamp is out of range.')

        return {'valid': True}
    except Exception as err:
      return {"valid": False, "error": err}

  def update(self, proof: dict) -> dict:
    proof['proofPurpose'] = self.term
    return proof

  def match(self, proof: dict) -> bool:
    return proof['proofPurpose'] == self.term
