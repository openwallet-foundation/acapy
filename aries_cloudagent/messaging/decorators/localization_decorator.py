"""The localization decorator (~l10n) for message localization information."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from ..models.base import BaseModel, BaseModelSchema


class LocalizationDecorator(BaseModel):
    """Class representing the localization decorator."""

    class Meta:
        """LocalizationDecorator metadata."""

        schema_class = "LocalizationDecoratorSchema"

    def __init__(
        self,
        *,
        locale: str = None,
        localizable: Sequence[str] = None,
        catalogs: Sequence[str] = None,
    ):
        """
        Initialize a LocalizationDecorator instance.

        Args:
            locale: The locale of this message
            localizable: The fields which may be localized
            catalogs: A list of URLs for localization resources

        """
        super().__init__()
        self.locale = locale
        self.localizable = list(localizable) if localizable else []
        self.catalogs = list(catalogs) if catalogs else []


class LocalizationDecoratorSchema(BaseModelSchema):
    """Localization decorator schema used in serialization/deserialization."""

    class Meta:
        """LocalizationDecoratorSchema metadata."""

        model_class = LocalizationDecorator
        unknown = EXCLUDE

    locale = fields.Str(
        required=True,
        description="Locale specifier",
        example="en-CA",
    )
    localizable = fields.List(
        fields.Str(
            description="Localizable field",
            example="note",
        ),
        required=False,
        description="List of localizable fields",
    )
    catalogs = fields.List(
        fields.Str(
            description="",
            example="https://192.168.56.111/my-project/catalog.json",
        ),
        required=False,
        description="List of message catalog URIs",
    )
