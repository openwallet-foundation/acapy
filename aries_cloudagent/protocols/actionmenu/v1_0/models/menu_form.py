"""Record used to represent the form associated with an action menu option."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....messaging.models.base import BaseModel, BaseModelSchema

from .menu_form_param import MenuFormParam, MenuFormParamSchema


class MenuForm(BaseModel):
    """Instance of a form associated with an action menu item."""

    class Meta:
        """Menu form metadata."""

        schema_class = "MenuFormSchema"

    def __init__(
        self,
        *,
        title: str = None,
        description: str = None,
        params: Sequence[MenuFormParam] = None,
        submit_label: str = None,
    ):
        """
        Initialize a MenuForm instance.

        Args:
            title: The menu form title
            description: Additional descriptive text for the menu form
            params: A list of form parameters
            submit_label: An alternative label for the form submit button
        """
        self.title = title
        self.description = description
        self.params = list(params) if params else []
        self.submit_label = submit_label


class MenuFormSchema(BaseModelSchema):
    """MenuForm schema."""

    class Meta:
        """MenuFormSchema metadata."""

        model_class = MenuForm
        unknown = EXCLUDE

    title = fields.Str(
        required=False,
        description="Menu form title",
        example="Preferences",
    )
    description = fields.Str(
        required=False,
        description="Additional descriptive text for menu form",
        example="Window preference settings",
    )
    params = fields.List(
        fields.Nested(MenuFormParamSchema()),
        required=False,
        description="List of form parameters",
    )
    submit_label = fields.Str(
        required=False,
        data_key="submit-label",
        description="Alternative label for form submit button",
        example="Send",
    )
