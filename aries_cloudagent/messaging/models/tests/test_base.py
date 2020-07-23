import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from marshmallow import fields, validates_schema, ValidationError

from ....cache.base import BaseCache
from ....config.injection_context import InjectionContext
from ....storage.base import BaseStorage, StorageRecord

from ...responder import BaseResponder, MockResponder
from ...util import time_now

from ..base import BaseModel, BaseModelSchema


class ModelImpl(BaseModel):
    class Meta:
        schema_class = "SchemaImpl"

    def __init__(self, *, attr=None):
        self.attr = attr


class SchemaImpl(BaseModelSchema):
    class Meta:
        model_class = ModelImpl

    attr = fields.String()

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
