from unittest import TestCase

from marshmallow import EXCLUDE, fields

from ...models.base import BaseModel, BaseModelSchema

from ..base import BaseDecoratorSet
from ..default import DecoratorSet, DEFAULT_MODELS


class SimpleModel(BaseModel):
    class Meta:
        schema_class = "SimpleModelSchema"

    def __init__(self, *, value: str = None, handled_decorator: str = None, **kwargs):
        super().__init__(**kwargs)
        self.handled_decorator = handled_decorator
        self.value = value


class SimpleModelSchema(BaseModelSchema):
    class Meta:
        model_class = SimpleModel
        unknown = EXCLUDE

    value = fields.Str(required=True)
    handled_decorator = fields.Str(required=False, data_key="handled~decorator")


class TestDecoratorSet(TestCase):
    def test_deco_set(self):
        deco_set = DecoratorSet()
        assert all(k in deco_set.models for k in DEFAULT_MODELS)

    def test_extract(self):
        decor_value = {}
        message = {"~decorator": decor_value, "one": "TWO"}

        decors = BaseDecoratorSet()
        remain = decors.extract_decorators(message)

        # check original is unmodified
        assert "~decorator" in message

        assert decors["decorator"] is decor_value
        assert remain == {"one": "TWO"}

    def test_dict(self):
        decors = BaseDecoratorSet()
        decors["test"] = "TEST"
        assert decors["test"] == "TEST"
        result = decors.to_dict()
        assert result == {"~test": "TEST"}

    def test_decorator_model(self):
        decor_value = {}
        message = {"~test": {"value": "TEST"}}

        decors = BaseDecoratorSet()
        decors.add_model("test", SimpleModel)
        remain = decors.extract_decorators(message, SimpleModelSchema)

        tested = decors["test"]
        assert isinstance(tested, SimpleModel) and tested.value == "TEST"

        result = decors.to_dict()
        assert result == message

    def test_field_decorator(self):
        decor_value = {}
        message = {"test~decorator": decor_value, "one": "TWO"}

        decors = BaseDecoratorSet()
        remain = decors.extract_decorators(message, SimpleModelSchema)

        # check original is unmodified
        assert "test~decorator" in message

        assert decors.field("test")
        assert decors.field("test")["decorator"] is decor_value
        assert remain == {"one": "TWO"}
        assert "test~decorator" in decors.to_dict()

    def test_skip_decorator(self):
        decor_value = {}
        message = {"handled~decorator": decor_value, "one": "TWO"}

        decors = BaseDecoratorSet()
        remain = decors.extract_decorators(message, SimpleModelSchema)

        # check original is unmodified
        assert "handled~decorator" in message

        assert not decors.field("handled")
        assert remain == message
        assert not decors.to_dict()
