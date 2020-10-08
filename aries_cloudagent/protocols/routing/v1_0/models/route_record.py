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
    TAG_NAMES = {"connection_id", "recipient_key"}

    def __init__(
        self,
        *,
        record_id: str = None,
        connection_id: str = None,
        recipient_key: str = None,
        **kwargs
    ):
        """
        Initialize a RouteRecord instance.

        Args:
            recipient_key: The recipient verkey of the route

        """
        super().__init__(record_id, None, **kwargs)
        self.connection_id = connection_id
        self.recipient_key = recipient_key

    @property
    def record_id(self) -> str:
        """Get record ID."""
        return self._id

    @classmethod
    async def retrieve_by_recipient_key(
        cls, context: InjectionContext, recipient_key: str
    ):
        """Retrieve a route record by recipient key."""
        tag_filter = {"recipient_key": recipient_key}
        # TODO post filter out our mediation requests?
        return await cls.retrieve_by_tag_filter(context, tag_filter)

    @classmethod
    async def retrieve_by_connection_id(
        cls, context: InjectionContext, connection_id: str
    ):
        """Retrieve a route record by recipient key."""
        tag_filter = {"connection_id": connection_id}
        # TODO post filter out our mediation requests?
        return await cls.retrieve_by_tag_filter(context, tag_filter)


class RouteRecordSchema(BaseRecordSchema):
    """RouteRecord schema."""

    class Meta:
        """RouteRecordSchema metadata."""

        model_class = RouteRecord
        unknown = EXCLUDE

    record_id = fields.Str(required=False)
    connection_id = fields.Str(required=True)
    recipient_key = fields.Str(required=True)
