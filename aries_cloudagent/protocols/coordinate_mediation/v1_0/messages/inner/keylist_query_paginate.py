"""Inner structure of KeylistQuery. Represents KeylistQuery.paginate."""

from marshmallow import fields

from ......messaging.models.base import BaseModel, BaseModelSchema


class KeylistQueryPaginate(BaseModel):
    """Class representing a keylist query pagination."""

    class Meta:
        """Keylist query pagination metadata."""

        schema_class = "KeylistQueryPaginateSchema"

    def __init__(self, limit: int, offset: int, **kwargs):
        """
        Initialize keylist query pagination object.

        Args:
            limit: limit for response count
            offset: offset value

        """
        super().__init__(**kwargs)
        self.limit = limit
        self.offset = offset


class KeylistQueryPaginateSchema(BaseModelSchema):
    """Keylist query pagination schema."""

    class Meta:
        """Keylist query pagination schema metadata."""

        model_class = KeylistQueryPaginate

    limit = fields.Int(
        required=False,
        metadata={"description": "Limit for keylist query", "example": 30},
    )
    offset = fields.Int(
        required=False, metadata={"description": "Offset value for query", "example": 0}
    )
