"""Linked data proof specific credential exchange information with non-secrets storage."""

from typing import Any, Sequence

from marshmallow import EXCLUDE, fields

from ......core.profile import ProfileSession
from ......messaging.models.base_record import BaseRecord, BaseRecordSchema
from ......messaging.valid import UUID4_EXAMPLE
from .. import UNENCRYPTED_TAGS


class V20CredExRecordLDProof(BaseRecord):
    """Credential exchange linked data proof detail record."""

    class Meta:
        """V20CredExRecordLDProof metadata."""

        schema_class = "V20CredExRecordLDProofSchema"

    RECORD_ID_NAME = "cred_ex_ld_proof_id"
    RECORD_TYPE = "ld_proof_cred_ex_v20"
    TAG_NAMES = {"~cred_ex_id"} if UNENCRYPTED_TAGS else {"cred_ex_id"}
    RECORD_TOPIC = "issue_credential_v2_0_ld_proof"

    def __init__(
        self,
        cred_ex_ld_proof_id: str = None,
        *,
        cred_ex_id: str = None,
        cred_id_stored: str = None,
        **kwargs,
    ):
        """Initialize LD Proof credential exchange record details."""
        super().__init__(cred_ex_ld_proof_id, **kwargs)

        self.cred_ex_id = cred_ex_id
        self.cred_id_stored = cred_id_stored

    @property
    def cred_ex_ld_proof_id(self) -> str:
        """Accessor for the ID associated with this exchange."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this credential exchange."""
        return {prop: getattr(self, prop) for prop in ("cred_id_stored",)}

    @classmethod
    async def query_by_cred_ex_id(
        cls,
        session: ProfileSession,
        cred_ex_id: str,
    ) -> Sequence["V20CredExRecordLDProof"]:
        """Retrieve a credential exchange LDProof detail record by its cred ex id."""
        return await cls.query(
            session=session,
            tag_filter={"cred_ex_id": cred_ex_id},
        )

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class V20CredExRecordLDProofSchema(BaseRecordSchema):
    """Credential exchange linked data proof detail record detail schema."""

    class Meta:
        """Credential exchange linked data proof detail record schema metadata."""

        model_class = V20CredExRecordLDProof
        unknown = EXCLUDE

    cred_ex_ld_proof_id = fields.Str(
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
