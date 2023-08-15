"""Represents an action menu."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import MENU, PROTOCOL_PACKAGE
from ..models.menu_option import MenuOption, MenuOptionSchema

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.menu_handler.MenuHandler"


class Menu(AgentMessage):
    """Class representing an action menu."""

    class Meta:
        """Metadata for an action menu."""

        handler_class = HANDLER_CLASS
        message_type = MENU
        schema_class = "MenuSchema"

    def __init__(
        self,
        *,
        title: str = None,
        description: str = None,
        errormsg: str = None,
        options: Sequence[MenuOption] = None,
        **kwargs,
    ):
        """
        Initialize a menu object.

        Args:
            title: The menu title
            description: Introductory text for the menu
            errormsg: An optional error message to display
            options: A sequence of menu options
        """
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        self.options = list(options) if options else []


class MenuSchema(AgentMessageSchema):
    """Menu schema class."""

    class Meta:
        """Menu schema metadata."""

        model_class = Menu
        unknown = EXCLUDE

    title = fields.Str(
        required=False, metadata={"description": "Menu title", "example": "My Menu"}
    )
    description = fields.Str(
        required=False,
        metadata={
            "description": "Introductory text for the menu",
            "example": "This menu presents options",
        },
    )
    errormsg = fields.Str(
        required=False,
        metadata={
            "description": "An optional error message to display in menu header",
            "example": "Error: item not found",
        },
    )
    options = fields.List(
        fields.Nested(MenuOptionSchema),
        required=True,
        metadata={"description": "List of menu options"},
    )
