"""This class represents cred def information for anoncreds."""


class AnoncredsCredDefInfo:
    """Represents the credential definition information for anonymous credentials."""

    def __init__(self, issuer_id: str):
        """Initialize the cred def information."""
        self.issuer_id = issuer_id
