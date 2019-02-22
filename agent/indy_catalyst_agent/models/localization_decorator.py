"""The localization decorator (~l10n) for message localization information
"""

from typing import Sequence

from marshmallow import fields

from .base import BaseModel, BaseModelSchema


class LocalizationDecorator(BaseModel):
    """Class representing the localization decorator."""

    class Meta:
        schema_class = "LocalizationDecoratorSchema"

    def __init__(
        self,
        *,
        locale: str = None,
        localizable: Sequence[str] = None,
        catalogs: Sequence[str] = None,
    ):
        super(LocalizationDecorator, self).__init__()
        self.locale = locale
        self.localizable = list(localizable) if localizable else []
        self.catalogs = list(catalogs) if catalogs else []


class LocalizationDecoratorSchema(BaseModelSchema):
    """Localization decorator schema used in serialization/deserialization"""

    class Meta:
        model_class = LocalizationDecorator

    locale = fields.Str(required=True)
    localizable = fields.List(fields.Str(), required=False)
    catalogs = fields.List(fields.Str(), required=False)
