"""This class represents schema information for anoncreds."""

from typing import Optional


class AnonCredsSchemaInfo:
    """Represents the schema information for anonymous credentials.

    Attributes:
        issuer_id (str): The identifier of the issuer.
        name (Optional[str]): The name of the schema. Defaults to None.
        version (Optional[str]): The version of the schema. Defaults to None.

    Args:
        issuer_id (str): The identifier of the issuer.
        name (Optional[str], optional): The name of the schema. Defaults to None.
        version (Optional[str], optional): The version of the schema. Defaults to None.
    """

    def __init__(
        self, issuer_id: str, name: Optional[str] = None, version: Optional[str] = None
    ):
        """Initialize the schema information."""
        self.issuer_id = issuer_id
        self.name = name
        self.version = version
