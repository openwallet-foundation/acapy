import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError

from ....cache.base import BaseCache
from ....config.injection_context import InjectionContext
from ....storage.base import BaseStorage, StorageRecord

from ...responder import BaseResponder, MockResponder
from ...util import time_now

from ..base import BaseModel, BaseModelError, BaseModelSchema


class ModelImpl(BaseModel):
    class Meta:
        schema_class = "SchemaImpl"

    def __init__(self, *, attr=None):
        self.attr = attr


class SchemaImpl(BaseModelSchema):
    class Meta:
        model_class = ModelImpl
        unknown = EXCLUDE

    attr = fields.String(required=True)

    @validates_schema
    def validate_fields(self, data, **kwargs):
        if data["attr"] != "succeeds":
            raise ValidationError("")


class TestBase(AsyncTestCase):
    def test_model_validate_fails(self):
        model = ModelImpl(attr="string")
        with self.assertRaises(ValidationError):
            model.validate()

    def test_model_validate_succeeds(self):
        model = ModelImpl(attr="succeeds")
        model = model.validate()
        assert model.attr == "succeeds"

    def test_ser_x(self):
        model = ModelImpl(attr="hello world")
        with async_mock.patch.object(
            model, "_get_schema_class", async_mock.MagicMock()
        ) as mock_get_schema_class:
            mock_get_schema_class.return_value = async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    dump=async_mock.MagicMock(side_effect=ValidationError("error"))
                )
            )
            with self.assertRaises(BaseModelError):
                model.serialize()

    def test_from_json_x(self):
        data = "{}{}"
        with self.assertRaises(BaseModelError):
            ModelImpl.from_json(data)
