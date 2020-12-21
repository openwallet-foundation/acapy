"""Admin API mediation schemas for parater validation."""

from marshmallow import fields, validate
from .....messaging.models.openapi import OpenAPISchema
from .....messaging.valid import UUIDFour
from .mediation_record import MediationRecord

MEDIATION_STATE_SCHEMA = fields.Str(
    description="Mediation state (optional)",
    required=False,
    validate=validate.OneOf(
        [
            getattr(MediationRecord, m)
            for m in vars(MediationRecord)
            if m.startswith("STATE_")
        ]
    ),
    example="'request_received'," "'granted' or 'denied'",
)


MEDIATION_ID_SCHEMA = {
    "validate": UUIDFour(),
    "example": UUIDFour.EXAMPLE,
}  # TODO: is mediation req id a did?


CONNECTION_ID_SCHEMA = fields.UUID(  # TODO: move this into connections.
    description="Connection identifier (optional)",
    required=False,
    example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
)


MEDIATOR_TERMS_SCHEMA = fields.List(
    fields.Str(
        description="Indicate terms that the mediator "
        "requires the recipient to agree to"
    ),
    required=False,
    description="List of mediator rules for recipient",
)


RECIPIENT_TERMS_SCHEMA = fields.List(
    fields.Str(
        description="Indicate terms that the recipient "
        "requires the mediator to agree to"
    ),
    required=False,
    description="List of recipient rules for mediation",
)


ROLE_SCHEMA = fields.Str(
    description="Role of the mediator request record.",
    validate=validate.OneOf(
        [
            getattr(MediationRecord, m)
            for m in vars(MediationRecord)
            if m.startswith("ROLE_")
        ]
    ),
    example="client",
)


ENDPOINT_SCHEMA = fields.Str(
    description="endpoint on which messages destined "
    "for the recipient are received.",
    example="http://192.168.56.102:8020/",
)


ROUTING_KEYS_SCHEMA = fields.List(
    fields.Str(description="Keys to use for forward message packaging"),
    required=False,
)


class MediationRecordReportSchema(OpenAPISchema):
    """MediationRecordSchema schema."""

    mediation_id = MEDIATION_ID_SCHEMA
    conn_id = CONNECTION_ID_SCHEMA
    mediator_terms = MEDIATOR_TERMS_SCHEMA
    recipient_terms = RECIPIENT_TERMS_SCHEMA
    endpoint = ENDPOINT_SCHEMA
    routing_keys = ROUTING_KEYS_SCHEMA
