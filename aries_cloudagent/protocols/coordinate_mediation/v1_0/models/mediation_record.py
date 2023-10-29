"""Store state for Mediation requests."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....core.profile import ProfileSession
from .....messaging.models.base_record import BaseRecord, BaseRecordSchema
from .....messaging.valid import DID_KEY_EXAMPLE, DID_KEY_VALIDATE
from .....storage.base import StorageDuplicateError, StorageNotFoundError


class MediationRecord(BaseRecord):
    """Class representing stored mediation information."""

    class Meta:
        """RouteRecord metadata."""

        schema_class = "MediationRecordSchema"

    RECORD_TYPE = "mediation_requests"
    RECORD_TOPIC = "mediation"
    RECORD_ID_NAME = "mediation_id"
    TAG_NAMES = {"state", "role", "connection_id"}

    STATE_REQUEST = "request"
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
        routing_keys: Sequence[str] = None,
        endpoint: str = None,
        **kwargs,
    ):
        """__init__.

        Args:
            mediation_id (str): (Optional) manually set record ID
            state (str): state, defaults to 'request_received'
            role (str): role in mediation, defaults to 'server'
            connection_id (str): ID of connection requesting or managing mediation
            mediator_terms (Sequence[str]): mediator_terms
            recipient_terms (Sequence[str]): recipient_terms
            routing_keys (Sequence[str]): keys in mediator control used to
            receive incoming messages
            endpoint (str): mediators endpoint
            kwargs: Pass arguments through to BaseRecord.__init__

        """
        super().__init__(mediation_id, state or self.STATE_REQUEST, **kwargs)
        self.role = role if role else self.ROLE_SERVER
        self.connection_id = connection_id
        self.mediator_terms = list(mediator_terms) if mediator_terms else []
        self.recipient_terms = list(recipient_terms) if recipient_terms else []
        self.routing_keys = list(routing_keys) if routing_keys else []
        self.endpoint = endpoint

    def __eq__(self, other: "MediationRecord"):
        """Equality check."""
        if not isinstance(other, MediationRecord):
            return False
        return (
            self.mediation_id == other.mediation_id
            and self.record_tags == other.record_tags
            and self.record_value == other.record_value
        )

    @property
    def mediation_id(self) -> str:
        """Get Mediation ID."""
        return self._id

    @property
    def state(self) -> str:
        """Get Mediation state."""
        return self._state

    @state.setter
    def state(self, state):
        """Setter for state."""
        if state not in [
            MediationRecord.STATE_DENIED,
            MediationRecord.STATE_GRANTED,
            MediationRecord.STATE_REQUEST,
        ]:
            raise ValueError(
                f"{state} is not a valid state, "
                "must be one of ("
                f"{MediationRecord.STATE_DENIED}, "
                f"{MediationRecord.STATE_GRANTED}, "
                f"{MediationRecord.STATE_REQUEST}"
            )
        self._state = state

    @property
    def record_value(self) -> dict:
        """Return values of record as dictionary."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "mediator_terms",
                "recipient_terms",
                "routing_keys",
                "endpoint",
            )
        }

    @classmethod
    async def retrieve_by_connection_id(
        cls, session: ProfileSession, connection_id: str
    ) -> "MediationRecord":
        """Retrieve a mediation record by connection ID.

        Args:
            session (ProfileSession): session
            connection_id (str): connection_id

        Returns:
            MediationRecord: retrieved record

        """
        tag_filter = {"connection_id": connection_id}
        return await cls.retrieve_by_tag_filter(session, tag_filter)

    @classmethod
    async def exists_for_connection_id(
        cls, session: ProfileSession, connection_id: str
    ) -> bool:
        """Return whether a mediation record exists for the given connection.

        Args:
            session (ProfileSession): session
            connection_id (str): connection_id

        Returns:
            bool: whether record exists

        """
        tag_filter = {"connection_id": connection_id}
        try:
            record = await cls.retrieve_by_tag_filter(session, tag_filter)
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
    routing_keys = fields.List(
        fields.Str(validate=DID_KEY_VALIDATE, metadata={"example": DID_KEY_EXAMPLE}),
        required=False,
    )
    endpoint = fields.Str(required=False)
