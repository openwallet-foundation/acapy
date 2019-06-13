"""Record used to represent a parameter in a menu form."""

from marshmallow import fields

from ...models.base import BaseModel, BaseModelSchema


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

    name = fields.Str(required=True)
    title = fields.Str(required=True)
    default = fields.Str(required=False)
    description = fields.Str(required=False)
    input_type = fields.Str(required=False, data_key="type")
    required = fields.Bool(required=False)
