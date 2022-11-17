"""An object for containing the response pagination information."""

from marshmallow import EXCLUDE, fields

from .....messaging.models.base import BaseModel, BaseModelSchema


class Paginated(BaseModel):
    """Class representing the pagination details of a response."""

    class Meta:
        """Paginated metadata."""

        schema_class = "PaginatedSchema"

    def __init__(
        self,
        *,
        start: int = None,
        end: int = None,
        limit: int = None,
        total: int = None,
        **kwargs
    ):
        """
        Initialize a Paginated instance.

        Args:
            start: The first record offset
            end: The last record offset
            limit: Enforced limit on the number of records
            total: Total number of records available

        """
        super().__init__(**kwargs)
        self.start = start
        self.end = end
        self.limit = limit
        self.total = total


class PaginatedSchema(BaseModelSchema):
    """Paginated schema."""

    class Meta:
        """PaginatedSchema metadata."""

        model_class = Paginated
        unknown = EXCLUDE

    start = fields.Int(required=False, strict=True)
    end = fields.Int(required=False, strict=True)
    limit = fields.Int(required=False, strict=True)
    total = fields.Int(required=False, strict=True)
