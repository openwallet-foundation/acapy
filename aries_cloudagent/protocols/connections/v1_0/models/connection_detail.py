"""An object for containing the connection request/response DID information."""

from marshmallow import EXCLUDE, fields

from pydid import DIDDocument
from .....messaging.models.base import BaseModel, BaseModelSchema
from .....messaging.valid import INDY_DID


class DIDDocWrapper(fields.Field):
    """Field that loads and serializes DIDDocument."""

    def _serialize(self, value, attr, obj, **kwargs):
        """
        Serialize the DIDDocument.

        Args:
            value: The value to serialize

        Returns:
            The serialized DIDDocument

        """
        return value.serialize()

    def _deserialize(self, value, attr, data, **kwargs):
        """
        Deserialize a value into a DIDDocument.

        Args:
            value: The value to deserialize

        Returns:
            The deserialized value

        """
        return DIDDocument.deserialize(value)


class ConnectionDetail(BaseModel):
    """Class representing the details of a connection."""

    class Meta:
        """ConnectionDetail metadata."""

        schema_class = "ConnectionDetailSchema"

    def __init__(self, *, did: str = None, did_doc: DIDDocument = None, **kwargs):
        """
        Initialize a ConnectionDetail instance.

        Args:
            did: DID for the connection detail
            did_doc: DIDDocument for connection detail

        """
        super().__init__(**kwargs)
        self._did = did
        self._did_doc = did_doc

    @property
    def did(self) -> str:
        """
        Accessor for the connection DID.

        Returns:
            The DID for this connection

        """
        return self._did

    @property
    def did_doc(self) -> DIDDocument:
        """
        Accessor for the connection DID Document.

        Returns:
            The DIDDocument for this connection

        """
        return self._did_doc


class ConnectionDetailSchema(BaseModelSchema):
    """ConnectionDetail schema."""

    class Meta:
        """ConnectionDetailSchema metadata."""

        model_class = ConnectionDetail
        unknown = EXCLUDE

    did = fields.Str(
        data_key="DID",
        required=False,
        description="DID for connection detail",
        **INDY_DID
    )
    did_doc = DIDDocWrapper(
        data_key="DIDDoc",
        required=False,
        description="DID document for connection detail",
    )
