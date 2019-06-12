"""Issuer Registration."""

from marshmallow import fields, Schema

from indy_catalyst_agent.messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import REGISTER

HANDLER_CLASS = (
    "indy_catalyst_issuer_registration."
    + "handlers.registration_handler.IssuerRegistrationHandlerHandler"
)


class IssuerRegistration(AgentMessage):
    """Class defining the structure of an issuer registration message."""

    class Meta:
        """Issuer Registration metadata class."""

        handler_class = HANDLER_CLASS
        message_type = REGISTER
        schema_class = "IssuerRegistrationSchema"

    def __init__(self, *, issuer_registration: dict, **kwargs):
        """
        Initialize issuer registration object.

        Args:
            issuer_registration: issuer metadata

        """
        super(IssuerRegistration, self).__init__(**kwargs)

        self.issuer_registration = issuer_registration


class IssuerRegistrationSchema(AgentMessageSchema):
    """Issuer registration schema class."""

    class Meta:
        """Issuer registration schema metadata."""

        model_class = IssuerRegistration

    class IssuerRegistrationNestedSchema(Schema):
        """Issuer registration nested schema."""

        class IssuerSchema(Schema):
            """Issuer schema."""

            did = fields.Str(required=True)
            name = fields.Str(required=True)
            abbreviation = fields.Str(required=False)
            email = fields.Str(required=False)
            url = fields.Str(required=False)
            endpoint = fields.Str(required=False)
            logo_b64 = fields.Str(required=False)

        class CredentialType(Schema):
            """Isuer credential type schema."""

            name = fields.Str(required=True)
            schema = fields.Str(required=True)
            version = fields.Str(required=True)
            description = fields.Str(required=False)
            cardinality_fields = fields.List(fields.Dict, required=False)
            credential = fields.Str(required=False)
            mapping = fields.Dict(required=False)
            topic = fields.Str(required=False)
            caregory_labels = fields.List(fields.Str, required=False)
            claim_descriptions = fields.List(fields.Str, required=False)
            claim_labels = fields.List(fields.Str, required=False)
            logo_b64 = fields.Str(required=False)
            credential_def_id = fields.Str(required=True)
            endpoint = fields.Str(required=False)
            visible_fields = fields.List(fields.Str, required=False)

        issuer = fields.Nested(IssuerSchema, required=True)
        credential_types = fields.List(fields.Nested(CredentialType), required=False)

    issuer_registration = fields.Nested(IssuerRegistrationNestedSchema, required=True)
