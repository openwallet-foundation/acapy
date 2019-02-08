"""
Base classes for Models and Schemas
"""

from abc import ABC
import sys

from marshmallow import (
    Schema, fields, post_dump, pre_load, post_load,
)


def resolve_class(cls, relative_cls: type):
    if isinstance(cls, str):
        mod = sys.modules[relative_cls.__module__]
        cls = getattr(mod, cls)
    return cls

def resolve_meta_property(obj, prop_name: str, defval=None):
    cls = obj.__class__
    found = defval
    while cls:
        Meta = getattr(cls, 'Meta', None)
        if Meta and hasattr(Meta, prop_name):
            found = getattr(Meta, prop_name)
            break
        cls = cls.__bases__[0]
        if cls is object:
            break
    return found


class BaseModel(ABC):
    class Meta:
        schema_class = None

    def __init__(self):
        if not self.Meta.schema_class:
            raise TypeError(
                "Can't instantiate abstract class {} with no schema_class".format(
                    self.__class__.__name__))

    @classmethod
    def _get_schema_class(cls):
        return resolve_class(cls.Meta.schema_class, cls)

    @property
    def Schema(self) -> type:
        """
        Accessor for the model's schema class
        """
        return self._get_schema_class()

    @classmethod
    def deserialize(cls, obj):
        """
        Convert from JSON representation to a model instance
        """
        schema = cls._get_schema_class()()
        return schema.loads(obj) if isinstance(obj, str) else schema.load(obj)

    def serialize(self, as_string=False):
        """
        Create a JSON representation of the model instance
        """
        schema = self.Schema()
        return schema.dumps(self) if as_string else schema.dump(self)

    def __repr__(self):
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ', '.join(items))


class BaseModelSchema(Schema):
    class Meta:
        model_class = None
        skip_values = [None]
        ordered = True

    def __init__(self, *args, **kwargs):
        super(BaseModelSchema, self).__init__(*args, **kwargs)
        if not self.Meta.model_class:
            raise TypeError(
                "Can't instantiate abstract class {} with no model_class".format(
                    self.__class__.__name__))

    @classmethod
    def _get_model_class(cls):
        return resolve_class(cls.Meta.model_class, cls)

    @property
    def Model(self) -> type:
        """
        Accessor for the schema's model class
        """
        return self._get_model_class()

    @pre_load
    def skip_dump_only(self, data):
        # not sure why this is necessary, seems like a bug
        to_remove = {
            field_obj.data_key or field_name
            for field_name, field_obj in self.fields.items()
            if field_obj.dump_only
        }
        for field_name in to_remove:
            if field_name in data:
                del data[field_name]
        return data

    @post_load
    def make_model(self, data: dict):
        return self.Model(**data)

    @post_dump
    def remove_skipped_values(self, data):
        skip_vals = resolve_meta_property(self, 'skip_values', [])
        return {
            key: value for key, value in data.items()
            if value not in skip_vals
        }
