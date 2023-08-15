from unittest import TestCase

from marshmallow import EXCLUDE, fields

from ....messaging.models.base import BaseModel, BaseModelSchema
from ..base import DECORATOR_PREFIX, BaseDecoratorSet


class SampleDecorator(BaseModel):
    """Sample model for base decorator tests."""

    class Meta:
        """Sample decorator metadata."""

        schema_class = "SampleDecoratorSchema"

    def __init__(self, score: int, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.score = score


class SampleDecoratorSchema(BaseModelSchema):
    """Sample schema decorator for base decorator tests."""

    class Meta:
        model_class = SampleDecorator
        unknown = EXCLUDE

    score = fields.Int(required=True, metadata={"strict": True})


class TestBaseDecoratorSet(TestCase):
    def test_base_decorator_set(self):
        MODELS = {"a": SampleDecorator}
        deco_set = BaseDecoratorSet(MODELS)
        assert type(deco_set) == BaseDecoratorSet
        assert not deco_set.fields
        assert deco_set.models == MODELS
        assert deco_set.prefix == DECORATOR_PREFIX
        assert BaseDecoratorSet.__name__ in str(deco_set)

        deco_set_copy = deco_set.copy()
        assert type(deco_set_copy) == BaseDecoratorSet
        assert deco_set_copy == deco_set
        assert not deco_set_copy.fields
        assert deco_set_copy.models == MODELS
        assert deco_set_copy.prefix == DECORATOR_PREFIX

        assert not deco_set.has_field("x")
        deco_set.field("x")
        assert not deco_set.has_field("x")  # empty
        assert not len(deco_set.field("x"))
        deco_set.remove_field("x")
        assert not deco_set.has_field("x")

        deco_set.add_model("c", SampleDecorator)
        assert "c" in deco_set.models
        deco_set.remove_model("c")
        assert "c" not in deco_set.models

        deco_set["a"] = None  #
        deco_set.load_decorator("a", None)
        assert "a" not in deco_set

        deco_set["a"] = {"score": 23}
        deco_set["a"] = SampleDecorator(23)
        deco_set.load_decorator("a", None)
