"""An object for containing information on an individual route."""

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError

from .....core.profile import ProfileSession
from .....messaging.models.base_record import BaseRecord, BaseRecordSchema


class RouteRecord(BaseRecord):
    """Class representing stored route information."""

    class Meta:
        """RouteRecord metadata."""

        schema_class = "RouteRecordSchema"

    RECORD_TYPE = "forward_route"
    RECORD_ID_NAME = "record_id"
    ROLE_CLIENT = "client"
    ROLE_SERVER = "server"
    TAG_NAMES = {"connection_id", "role", "recipient_key", "wallet_id"}

    def __init__(
        self,
        *,
        record_id: str = None,
        role: str = None,
        connection_id: str = None,
        wallet_id: str = None,
        recipient_key: str = None,
        **kwargs
    ):
        """Initialize route record.

        Args:
            record_id (str): record_id optionally specify record id manually
            role (str): role of agent, client or server
            connection_id (str): connection_id associated with record
            wallet_id: The id of the wallet for the route. Used for multitenant relay
            recipient_key (str): recipient_key associated with record
            kwargs: additional args for BaseRecord
        """
        super().__init__(record_id, None, **kwargs)
        self.role = role or self.ROLE_SERVER
        self.connection_id = connection_id
        self.wallet_id = wallet_id
        self.recipient_key = recipient_key

    def __eq__(self, other: "RouteRecord"):
        """Equality check."""
        if not isinstance(other, RouteRecord):
            return False
        return (
            self.record_id == other.record_id
            and self.record_tags == other.record_tags
            and self.record_value == other.record_value
        )

    @property
    def record_id(self) -> str:
        """Get record ID."""
        return self._id

    @classmethod
    async def retrieve_by_recipient_key(
        cls, session: ProfileSession, recipient_key: str
    ) -> "RouteRecord":
        """Retrieve a route record by recipient key.

        Args:
            session (ProfileSession): session
            recipient_key (str): key to look up

        Returns:
            RouteRecord: retrieved route record

        """
        tag_filter = {"recipient_key": recipient_key}
        return await cls.retrieve_by_tag_filter(session, tag_filter)

    @classmethod
    async def retrieve_by_connection_id(
        cls, session: ProfileSession, connection_id: str
    ) -> "RouteRecord":
        """Retrieve a route record by connection ID.

        Args:
            session (ProfileSession): session
            connection_id (str): ID to look up

        Returns:
            RouteRecord: retrieved route record

        """
        tag_filter = {"connection_id": connection_id}
        return await cls.retrieve_by_tag_filter(session, tag_filter)

    @property
    def record_value(self) -> dict:
        """Accessor for JSON record value."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "connection_id",
                "wallet_id",
                "recipient_key",
            )
        }


class RouteRecordSchema(BaseRecordSchema):
    """RouteRecord schema."""

    class Meta:
        """RouteRecordSchema metadata."""

        model_class = RouteRecord
        unknown = EXCLUDE

    record_id = fields.Str()
    role = fields.Str(required=False)
    connection_id = fields.Str()
    wallet_id = fields.Str()
    recipient_key = fields.Str(required=True)

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields.

        Args:
            data: The data to validate

        Raises:
            ValidationError: If any of the fields do not validate

        """

        if not (data.get("connection_id") or data.get("wallet_id")):
            raise ValidationError(
                "Either connection_id or wallet_id must be set for route"
            )
