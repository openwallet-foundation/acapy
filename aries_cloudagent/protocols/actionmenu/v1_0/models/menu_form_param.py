"""Record used to represent a parameter in a menu form."""

from marshmallow import EXCLUDE, fields

from .....messaging.models.base import BaseModel, BaseModelSchema


class MenuFormParam(BaseModel):
    """Instance of a menu form param associated with an action menu option."""

    class Meta:
        """Menu form param metadata."""

        schema_class = "MenuFormParamSchema"

    def __init__(
        self,
        *,
        name: str = None,
        title: str = None,
        default: str = None,
        description: str = None,
        input_type: str = None,
        required: bool = None,
    ):
        """
        Initialize a MenuFormParam instance.

        Args:
            name: The parameter name
            title: The parameter title
            default: A default value for the parameter
            description: Additional descriptive text for the menu form parameter
            input_type: Input type
            required: Whether the parameter is required

        """
        self.name = name
        self.title = title
        self.default = default
        self.description = description
        self.input_type = input_type
        self.required = required


class MenuFormParamSchema(BaseModelSchema):
    """MenuFormParam schema."""

    class Meta:
        """MenuFormParamSchema metadata."""

        model_class = MenuFormParam
        unknown = EXCLUDE

    name = fields.Str(
        required=True,
        description="Menu parameter name",
        example="delay",
    )
    title = fields.Str(
        required=True, description="Menu parameter title", example="Delay in seconds"
    )
    default = fields.Str(
        required=False,
        description="Default parameter value",
        example="0",
    )
    description = fields.Str(
        required=False,
        description="Additional descriptive text for menu form parameter",
        example="Delay in seconds before starting",
    )
    input_type = fields.Str(
        required=False,
        description="Menu form parameter input type",
        example="int",
        data_key="type",
    )
    required = fields.Bool(
        required=False,
        description="Whether parameter is required",
        example="False",
    )
