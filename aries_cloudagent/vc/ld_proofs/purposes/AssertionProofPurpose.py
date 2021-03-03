from .ControllerProofPurpose import ControllerProofPurpose
from datetime import datetime, timedelta


class AssertionProofPurpose(ControllerProofPurpose):
  def __init__(self, date: datetime, max_timestamp_delta: timedelta = None):
    super().__init__('assertionMethod', date, max_timestamp_delta)



__all__ = [AssertionProofPurpose]
