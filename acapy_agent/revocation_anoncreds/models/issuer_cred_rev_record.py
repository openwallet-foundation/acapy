"""Issuer credential revocation information."""

from typing import Any, Optional, Sequence

from marshmallow import fields

from ...core.profile import ProfileSession
from ...messaging.models.base_record import BaseRecord, BaseRecordSchema
from ...messaging.valid import UUID4_EXAMPLE


class IssuerCredRevRecord(BaseRecord):
    """Represents credential revocation information to retain post-issue."""

    class Meta:
        """IssuerCredRevRecord metadata."""

        schema_class = "IssuerCredRevRecordSchemaAnonCreds"

    RECORD_TYPE = "issuer_cred_rev"
    RECORD_ID_NAME = "record_id"
    RECORD_TOPIC = "issuer_cred_rev"
    TAG_NAMES = {
        "cred_ex_id",
        "cred_ex_version",
        "cred_def_id",
        "rev_reg_id",
        "cred_rev_id",
        "state",
    }

    STATE_ISSUED = "issued"
    STATE_REVOKED = "revoked"

    VERSION_1 = "1"
    VERSION_2 = "2"

    def __init__(
        self,
        *,
        record_id: Optional[str] = None,
        state: Optional[str] = None,
        cred_ex_id: Optional[str] = None,
        rev_reg_id: Optional[str] = None,
        cred_rev_id: Optional[str] = None,
        cred_def_id: Optional[str] = None,  # Marshmallow formalism: leave None
        cred_ex_version: Optional[str] = None,
        **kwargs,
    ):
        """Initialize a new IssuerCredRevRecord."""
        super().__init__(record_id, state or IssuerCredRevRecord.STATE_ISSUED, **kwargs)
        self.cred_ex_id = cred_ex_id
        self.rev_reg_id = rev_reg_id
        self.cred_rev_id = cred_rev_id
        self.cred_def_id = ":".join(rev_reg_id.split(":")[-7:-2])
        self.cred_ex_version = cred_ex_version

    @property
    def record_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @classmethod
    async def query_by_ids(
        cls,
        session: ProfileSession,
        *,
        cred_def_id: Optional[str] = None,
        rev_reg_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Sequence["IssuerCredRevRecord"]:
        """Retrieve issuer cred rev records by cred def id and/or rev reg id.

        Args:
            session: the profile session to use
            cred_def_id: the cred def id by which to filter
            rev_reg_id: the rev reg id by which to filter
            state: a state value by which to filter
        """
        tag_filter = {
            **{"cred_def_id": cred_def_id for _ in [""] if cred_def_id},
            **{"rev_reg_id": rev_reg_id for _ in [""] if rev_reg_id},
            **{"state": state for _ in [""] if state},
        }

        return await cls.query(session, tag_filter)

    @classmethod
    async def retrieve_by_ids(
        cls,
        session: ProfileSession,
        rev_reg_id: str,
        cred_rev_id: str,
        *,
        for_update: bool = False,
    ) -> "IssuerCredRevRecord":
        """Retrieve an issuer cred rev record by rev reg id and cred rev id."""
        return await cls.retrieve_by_tag_filter(
            session,
            {"rev_reg_id": rev_reg_id},
            {"cred_rev_id": cred_rev_id},
            for_update=for_update,
        )

    @classmethod
    async def retrieve_by_cred_ex_id(
        cls,
        session: ProfileSession,
        cred_ex_id: str,
    ) -> "IssuerCredRevRecord":
        """Retrieve an issuer cred rev record by rev reg id and cred rev id."""
        return await cls.retrieve_by_tag_filter(session, {"cred_ex_id": cred_ex_id})

    async def set_state(self, session: ProfileSession, state: Optional[str] = None):
        """Change the issuer cred rev record state (default issued)."""
        self.state = state or IssuerCredRevRecord.STATE_ISSUED
        await self.save(session, reason=f"Marked {self.state}")

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class IssuerCredRevRecordSchemaAnonCreds(BaseRecordSchema):
    """Schema to allow de/serialization of credential revocation records."""

    class Meta:
        """IssuerCredRevRecordSchema metadata."""

        model_class = IssuerCredRevRecord

    record_id = fields.Str(
        required=False,
        metadata={
            "description": "Issuer credential revocation record identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    state = fields.Str(
        required=False,
        metadata={
            "description": "Issue credential revocation record state",
            "example": IssuerCredRevRecord.STATE_ISSUED,
        },
    )
    cred_ex_id = fields.Str(
        required=False,
        metadata={
            "description": "Credential exchange record identifier at credential issue",
            "example": UUID4_EXAMPLE,
        },
    )
    rev_reg_id = fields.Str(
        required=False,
        metadata={"description": "Revocation registry identifier"},
    )
    cred_def_id = fields.Str(
        required=False,
        metadata={"description": "Credential definition identifier"},
    )
    cred_rev_id = fields.Str(
        required=False,
        metadata={"description": "Credential revocation identifier"},
    )
    cred_ex_version = fields.Str(
        required=False, metadata={"description": "Credential exchange version"}
    )
