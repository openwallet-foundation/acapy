"""Store state for Mediation requests."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....config.injection_context import InjectionContext

from .....messaging.models.base_record import BaseRecord, BaseRecordSchema
from .....storage.base import StorageNotFoundError, StorageDuplicateError


class MediationRecord(BaseRecord):
    """Class representing stored route information.

    Args:
        connection id:
        terms:
    """

    class Meta:
        """RouteRecord metadata."""

        schema_class = "MediationRecordSchema"

    RECORD_TYPE = "mediation_requests"
    RECORD_ID_NAME = "mediation_id"
    TAG_NAMES = {"state",  "role", "connection_id"}

    STATE_REQUEST_RECEIVED = "request_received"
    STATE_GRANTED = "granted"
    STATE_DENIED = "denied"

    ROLE_CLIENT = "client"
    ROLE_SERVER = "server"

    def __init__(
        self,
        *,
        mediation_id: str = None,
        state: str = None,
        role: str = None,
        connection_id: str = None,
        mediator_terms: Sequence[str] = None,
        recipient_terms: Sequence[str] = None,
        **kwargs
    ):
        """
        Initialize a MediationRecord instance.

        Args:
            mediation_id:
            state:
            connection_id:
            terms:
        """
        super().__init__(
            mediation_id, state or self.STATE_REQUEST_RECEIVED, **kwargs
        )
        self.role = role if role else self.ROLE_SERVER
        self.connection_id = connection_id
        self.mediator_terms = list(mediator_terms) if mediator_terms else []
        self.recipient_terms = list(recipient_terms) if recipient_terms else []

    @property
    def mediation_id(self) -> str:
        """Get Mediation ID."""
        return self._id

    @classmethod
    async def retrieve_by_connection_id(
        cls, context: InjectionContext, connection_id: str
    ):
        """Retrieve a route record by recipient key."""
        tag_filter = {"connection_id": connection_id}
        return await cls.retrieve_by_tag_filter(context, tag_filter)

    @classmethod
    async def exists_for_connection_id(
        cls, context: InjectionContext, connection_id: str
    ) -> bool:
        """Return whether a mediation record exists for the given connection."""
        tag_filter = {"connection_id": connection_id}
        try:
            record = await cls.retrieve_by_tag_filter(context, tag_filter)
        except StorageNotFoundError:
            return False
        except StorageDuplicateError:
            return True

        return bool(record)


class MediationRecordSchema(BaseRecordSchema):
    """MediationRecordSchema schema."""

    class Meta:
        """MediationRecordSchema metadata."""

        model_class = MediationRecord
        unknown = EXCLUDE

    mediation_id = fields.Str(required=False)
    role = fields.Str(required=True)
    connection_id = fields.Str(required=True)
    mediator_terms = fields.List(fields.Str(), required=False)
    recipient_terms = fields.List(fields.Str(), required=False)
