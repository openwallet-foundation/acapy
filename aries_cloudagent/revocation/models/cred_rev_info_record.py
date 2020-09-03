"""Issuer revocation registry storage handling."""

import json
import logging
import uuid

LOGGER = logging.getLogger(__name__)


class CredRevInfoRecord(BaseRecord):
    """Non-secrets record per issued credential to retain revocation info."""

    class Meta:
        """CredRevInfoRecord metadata."""

        schema_class = "CredRevInfoRecordSchema"

    RECORD_ID_NAME = "cred_ex_id"
    RECORD_TYPE = "cred_rev_info"
    WEBHOOK_TOPIC = "cred_rev_info"
    LOG_STATE_FLAG = "debug.revocation"
    CACHE_ENABLED = False
    TAG_NAMES = {"state", "cred_ex_id", "rev_reg_id", "cred_rev_id"}

    STATE_ISSUED = "issued"
    STATE_REVOKED = "revoked"

    def __init__(
        self,
        *,
        cred_ex_id: str = None,
        state: str = None,
        rev_reg_id: str = None,
        cred_rev_id: str = None
        **kwargs,
    ):
        """Initialize the credential revocation information record."""
        super().__init__(
            cred_ex_id, state=state or CredRevInfoRecord.STATE_ISSUED, **kwargs
        )
        self.cred_ex_id = cred_ex_id
        self.rev_reg_id = rev_reg_id
        self.cred_rev_id = cred_rev_id

    @property
    def cred_ex_id(self) -> str:
        """Accessor for the record ID, matching its credential exchange record's."""
        return self._id

    async def mark_revoked(self, context: InjectionContext):
        """Change the record state to revoked."""
        self.state = CredRevInfoRecord.STATE_REVOKED
        await self.save(context, reason="Marked as revoked")

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class CredRevInfoRecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of cred rev info records."""

    class Meta:
        """CredRevInfoRecordSchema metadata."""

        model_class = CredRevInfoRecord

    cred_ex_id = fields.Str(
        required=False,
        description=(
            "Record identifier, matching original "
            "credential exchange record identifier"
        ),
        example=UUIDFour.EXAMPLE,
    )
    state = fields.Str(
        required=False,
        description="Credential revocation info record state",
        example=CredRevInfoRecord.STATE_ISSUED,
    )
    rev_reg_id = fields.Str(
        required=False,
        description="Revocation registry identifier",
        **INDY_REV_REG_ID,
    )
    cred_rev_id = fields.Str(
        required=False,
        description="Credential revocation identifier",
        **INDY_CRED_REV_ID,
    )
