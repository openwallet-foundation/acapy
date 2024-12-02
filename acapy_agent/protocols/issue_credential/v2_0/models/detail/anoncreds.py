"""Anoncreds specific credential exchange information with non-secrets storage."""

from typing import Any, Mapping, Optional, Sequence

from marshmallow import EXCLUDE, fields

from ......core.profile import ProfileSession
from ......messaging.models.base_record import BaseRecord, BaseRecordSchema
from ......messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_REV_REG_ID_EXAMPLE,
    UUID4_EXAMPLE,
)
from .. import UNENCRYPTED_TAGS


class V20CredExRecordAnoncreds(BaseRecord):
    """Credential exchange anoncreds detail record."""

    class Meta:
        """V20CredExRecordAnoncreds metadata."""

        schema_class = "V20CredExRecordAnoncredsSchema"

    RECORD_ID_NAME = "cred_ex_anoncreds_id"
    RECORD_TYPE = "anoncreds_cred_ex_v20"
    TAG_NAMES = {"~cred_ex_id"} if UNENCRYPTED_TAGS else {"cred_ex_id"}
    RECORD_TOPIC = "issue_credential_v2_0_anoncreds"

    def __init__(
        self,
        cred_ex_anoncreds_id: Optional[str] = None,
        *,
        cred_ex_id: Optional[str] = None,
        cred_id_stored: Optional[str] = None,
        cred_request_metadata: Optional[Mapping] = None,
        rev_reg_id: Optional[str] = None,
        cred_rev_id: Optional[str] = None,
        **kwargs,
    ):
        """Initialize anoncreds credential exchange record details."""
        super().__init__(cred_ex_anoncreds_id, **kwargs)

        self.cred_ex_id = cred_ex_id
        self.cred_id_stored = cred_id_stored
        self.cred_request_metadata = cred_request_metadata
        self.rev_reg_id = rev_reg_id
        self.cred_rev_id = cred_rev_id

    @property
    def cred_ex_anoncreds_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this credential exchange."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "cred_id_stored",
                "cred_request_metadata",
                "rev_reg_id",
                "cred_rev_id",
            )
        }

    @classmethod
    async def query_by_cred_ex_id(
        cls,
        session: ProfileSession,
        cred_ex_id: str,
    ) -> Sequence["V20CredExRecordAnoncreds"]:
        """Retrieve credential exchange anoncreds detail record(s) by its cred ex id."""
        return await cls.query(
            session=session,
            tag_filter={"cred_ex_id": cred_ex_id},
        )

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class V20CredExRecordAnoncredsSchema(BaseRecordSchema):
    """Credential exchange anoncreds detail record detail schema."""

    class Meta:
        """Credential exchange anoncreds detail record schema metadata."""

        model_class = V20CredExRecordAnoncreds
        unknown = EXCLUDE

    cred_ex_anoncreds_id = fields.Str(
        required=False,
        metadata={"description": "Record identifier", "example": UUID4_EXAMPLE},
    )
    cred_ex_id = fields.Str(
        required=False,
        metadata={
            "description": "Corresponding v2.0 credential exchange record identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    cred_id_stored = fields.Str(
        required=False,
        metadata={
            "description": "Credential identifier stored in wallet",
            "example": UUID4_EXAMPLE,
        },
    )
    cred_request_metadata = fields.Dict(
        required=False,
        metadata={"description": "Credential request metadata for anoncreds holder"},
    )
    rev_reg_id = fields.Str(
        required=False,
        metadata={
            "description": "Revocation registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )
    cred_rev_id = fields.Str(
        required=False,
        metadata={
            "description": (
                "Credential revocation identifier within revocation registry"
            ),
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
    )
