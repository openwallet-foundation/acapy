"""An object for containing information on an individual route."""

from marshmallow import EXCLUDE, fields

from .....config.injection_context import InjectionContext

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
    TAG_NAMES = {"connection_id", "role", "recipient_key"}

    def __init__(
        self,
        *,
        record_id: str = None,
        role: str = None,
        connection_id: str = None,
        recipient_key: str = None,
        **kwargs
    ):
        """Initialize route record.

        Args:
            record_id (str): record_id optionally specify record id manually
            role (str): role of agent, client or server
            connection_id (str): connection_id associated with record
            recipient_key (str): recipient_key associated with record
            kwargs: additional args for BaseRecord
        """
        super().__init__(record_id, None, **kwargs)
        self.role = role or self.ROLE_SERVER
        self.connection_id = connection_id
        self.recipient_key = recipient_key

    @property
    def record_id(self) -> str:
        """Get record ID."""
        return self._id

    @classmethod
    async def retrieve_by_recipient_key(
        cls, context: InjectionContext, recipient_key: str
    ) -> "RouteRecord":
        """Retrieve a route record by recipient key.

        Args:
            context (InjectionContext): context
            recipient_key (str): key to look up

        Returns:
            RouteRecord: retrieved route record
        """
        tag_filter = {"recipient_key": recipient_key}
        return await cls.retrieve_by_tag_filter(context, tag_filter)

    @classmethod
    async def retrieve_by_connection_id(
        cls, context: InjectionContext, connection_id: str
    ) -> "RouteRecord":
        """Retrieve a route record by connection ID.

        Args:
            context (InjectionContext): context
            connection_id (str): ID to look up

        Returns:
            RouteRecord: retrieved route record
        """
        tag_filter = {"connection_id": connection_id}
        return await cls.retrieve_by_tag_filter(context, tag_filter)


class RouteRecordSchema(BaseRecordSchema):
    """RouteRecord schema."""

    class Meta:
        """RouteRecordSchema metadata."""

        model_class = RouteRecord
        unknown = EXCLUDE

    record_id = fields.Str(required=False)
    role = fields.Str(required=False)
    connection_id = fields.Str(required=True)
    recipient_key = fields.Str(required=True)
