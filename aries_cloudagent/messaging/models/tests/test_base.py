from asynctest import TestCase as AsyncTestCase, mock as async_mock

from marshmallow import EXCLUDE, INCLUDE, fields, validates_schema, ValidationError

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


class ModelImplWithUnknown(BaseModel):
    class Meta:
        schema_class = "SchemaImplWithUnknown"

    def __init__(self, *, attr=None, **kwargs):
        self.attr = attr
        self.extra = kwargs


class SchemaImplWithUnknown(BaseModelSchema):
    class Meta:
        model_class = ModelImplWithUnknown
        unknown = INCLUDE

    attr = fields.String(required=True)

    @validates_schema
    def validate_fields(self, data, **kwargs):
        if data["attr"] != "succeeds":
            raise ValidationError("")


class ModelImplWithoutUnknown(BaseModel):
    class Meta:
        schema_class = "SchemaImplWithoutUnknown"

    def __init__(self, *, attr=None):
        self.attr = attr


class SchemaImplWithoutUnknown(BaseModelSchema):
    class Meta:
        model_class = ModelImplWithoutUnknown

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

    def test_model_with_unknown(self):
        model = ModelImplWithUnknown(attr="succeeds")
        model = model.validate()
        assert model.attr == "succeeds"

        model = ModelImplWithUnknown.deserialize(
            {"attr": "succeeds", "another": "value"}
        )
        assert model.extra
        assert model.extra["another"] == "value"
        assert model.attr == "succeeds"

    def test_model_without_unknown_default_exclude(self):
        model = ModelImplWithoutUnknown(attr="succeeds")
        model = model.validate()
        assert model.attr == "succeeds"

        assert ModelImplWithoutUnknown.deserialize(
            {"attr": "succeeds", "another": "value"}
        )
