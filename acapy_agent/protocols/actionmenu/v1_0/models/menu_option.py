"""Record used to represent individual menu options in an action menu."""

from typing import Optional

from marshmallow import EXCLUDE, fields

from .....messaging.models.base import BaseModel, BaseModelSchema
from .menu_form import MenuForm, MenuFormSchema


class MenuOption(BaseModel):
    """Instance of a menu option associated with an action menu."""

    class Meta:
        """Menu option metadata."""

        schema_class = "MenuOptionSchema"

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        disabled: Optional[bool] = None,
        form: Optional[MenuForm] = None,
    ):
        """Initialize a MenuOption instance.

        Args:
            name: The menu option name (unique ID)
            title: The menu option title
            description: Additional descriptive text for the menu option
            disabled: If the option should be shown as disabled
            form: A form to display when the option is selected

        """
        self.name = name
        self.title = title
        self.description = description
        self.disabled = disabled
        self.form = form


class MenuOptionSchema(BaseModelSchema):
    """MenuOption schema."""

    class Meta:
        """MenuOptionSchema metadata."""

        model_class = MenuOption
        unknown = EXCLUDE

    name = fields.Str(
        required=True,
        metadata={
            "description": "Menu option name (unique identifier)",
            "example": "window_prefs",
        },
    )
    title = fields.Str(
        required=True,
        metadata={"description": "Menu option title", "example": "Window Preferences"},
    )
    description = fields.Str(
        required=False,
        metadata={
            "description": "Additional descriptive text for menu option",
            "example": "Window display preferences",
        },
    )
    disabled = fields.Bool(
        required=False,
        metadata={
            "description": "Whether to show option as disabled",
            "example": "False",
        },
    )
    form = fields.Nested(MenuFormSchema(), required=False)
