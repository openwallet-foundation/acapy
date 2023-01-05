"""Base classes for Models and Schemas."""

import logging
import json

from abc import ABC
from collections import namedtuple
from typing import Mapping, Optional, Type, TypeVar, Union, cast, overload
from typing_extensions import Literal

from marshmallow import Schema, post_dump, pre_load, post_load, ValidationError, EXCLUDE

from ...core.error import BaseError
from ...utils.classloader import ClassLoader

LOGGER = logging.getLogger(__name__)

SerDe = namedtuple("SerDe", "ser de")


def resolve_class(the_cls, relative_cls: Optional[type] = None) -> type:
    """
    Resolve a class.

    Args:
        the_cls: The class to resolve
        relative_cls: Relative class to resolve from

    Returns:
        The resolved class

    Raises:
        ClassNotFoundError: If the class could not be loaded

    """
    resolved = None
    if isinstance(the_cls, type):
        resolved = the_cls
    elif isinstance(the_cls, str):
        default_module = relative_cls and relative_cls.__module__
        resolved = ClassLoader.load_class(the_cls, default_module)
    else:
        raise TypeError(
            f"Could not resolve class from {the_cls}; incorrect type {type(the_cls)}"
        )
    return resolved


def resolve_meta_property(obj, prop_name: str, defval=None):
    """
    Resolve a meta property.

    Args:
        prop_name: The property to resolve
        defval: The default value

    Returns:
        The meta property

    """
    if isinstance(obj, type):
        cls = obj
    else:
        cls = obj.__class__
    found = defval
    while cls:
        Meta = getattr(cls, "Meta", None)
        if Meta and hasattr(Meta, prop_name):
            found = getattr(Meta, prop_name)
            break
        cls = cls.__bases__[0]
        if cls is object:
            break
    return found


class BaseModelError(BaseError):
    """Base exception class for base model errors."""


ModelType = TypeVar("ModelType", bound="BaseModel")


class BaseModel(ABC):
    """Base model that provides convenience methods."""

    class Meta:
        """BaseModel meta data."""

        schema_class = None

    def __init__(self):
        """
        Initialize BaseModel.

        Raises:
            TypeError: If schema_class is not set on Meta

        """
        if not self.Meta.schema_class:
            raise TypeError(
                "Can't instantiate abstract class {} with no schema_class".format(
                    self.__class__.__name__
                )
            )

    @classmethod
    def _get_schema_class(cls) -> Type["BaseModelSchema"]:
        """
        Get the schema class.

        Returns:
            The resolved schema class

        """
        resolved = resolve_class(cls.Meta.schema_class, cls)
        if issubclass(resolved, BaseModelSchema):
            return resolved

        raise TypeError(
            f"Resolved class is not a subclass of BaseModelSchema: {resolved}"
        )

    @property
    def Schema(self) -> Type["BaseModelSchema"]:
        """
        Accessor for the model's schema class.

        Returns:
            The schema class

        """
        return self._get_schema_class()

    @overload
    @classmethod
    def deserialize(
        cls: Type[ModelType],
        obj,
        *,
        unknown: Optional[str] = None,
    ) -> ModelType:
        """Convert from JSON representation to a model instance."""
        ...

    @overload
    @classmethod
    def deserialize(
        cls: Type[ModelType],
        obj,
        *,
        none2none: Literal[False],
        unknown: Optional[str] = None,
    ) -> ModelType:
        """Convert from JSON representation to a model instance."""
        ...

    @overload
    @classmethod
    def deserialize(
        cls: Type[ModelType],
        obj,
        *,
        none2none: Literal[True],
        unknown: Optional[str] = None,
    ) -> Optional[ModelType]:
        """Convert from JSON representation to a model instance."""
        ...

    @classmethod
    def deserialize(
        cls: Type[ModelType],
        obj,
        *,
        unknown: Optional[str] = None,
        none2none: bool = False,
    ) -> Optional[ModelType]:
        """
        Convert from JSON representation to a model instance.

        Args:
            obj: The dict to load into a model instance
            unknown: Behaviour for unknown attributes
            none2none: Deserialize None to None

        Returns:
            A model instance for this data

        """
        if obj is None and none2none:
            return None

        schema_cls = cls._get_schema_class()
        schema = schema_cls(
            unknown=unknown or resolve_meta_property(schema_cls, "unknown", EXCLUDE)
        )

        try:
            return cast(
                ModelType,
                schema.loads(obj) if isinstance(obj, str) else schema.load(obj),
            )
        except (AttributeError, ValidationError) as err:
            LOGGER.exception(f"{cls.__name__} message validation error:")
            raise BaseModelError(f"{cls.__name__} schema validation failed") from err

    @overload
    def serialize(
        self,
        *,
        as_string: Literal[True],
        unknown: Optional[str] = None,
    ) -> str:
        """Create a JSON-compatible dict representation of the model instance."""
        ...

    @overload
    def serialize(
        self,
        *,
        unknown: Optional[str] = None,
    ) -> dict:
        """Create a JSON-compatible dict representation of the model instance."""
        ...

    def serialize(
        self,
        *,
        as_string: bool = False,
        unknown: Optional[str] = None,
    ) -> Union[str, dict]:
        """
        Create a JSON-compatible dict representation of the model instance.

        Args:
            as_string: Return a string of JSON instead of a dict

        Returns:
            A dict representation of this model, or a JSON string if as_string is True

        """
        schema_cls = self._get_schema_class()
        schema = schema_cls(
            unknown=unknown or resolve_meta_property(schema_cls, "unknown", EXCLUDE)
        )
        try:
            return (
                schema.dumps(self, separators=(",", ":"))
                if as_string
                else schema.dump(self)
            )
        except (AttributeError, ValidationError) as err:
            LOGGER.exception(f"{self.__class__.__name__} message serialization error:")
            raise BaseModelError(
                f"{self.__class__.__name__} schema validation failed"
            ) from err

    @classmethod
    def serde(cls, obj: Union["BaseModel", Mapping]) -> Optional[SerDe]:
        """Return serialized, deserialized representations of input object."""
        if obj is None:
            return None

        if isinstance(obj, BaseModel):
            return SerDe(obj.serialize(), obj)

        return SerDe(obj, cls.deserialize(obj))

    def validate(self, unknown: Optional[str] = None):
        """Validate a constructed model."""
        schema = self.Schema(unknown=unknown)
        errors = schema.validate(self.serialize())
        if errors:
            raise ValidationError(errors)
        return self

    @classmethod
    def from_json(
        cls,
        json_repr: Union[str, bytes],
        unknown: Optional[str] = None,
    ):
        """
        Parse a JSON string into a model instance.

        Args:
            json_repr: JSON string

        Returns:
            A model instance representation of this JSON

        """
        try:
            parsed = json.loads(json_repr)
        except ValueError as e:
            LOGGER.exception(f"{cls.__name__} message parse error:")
            raise BaseModelError(f"{cls.__name__} JSON parsing failed") from e
        return cls.deserialize(parsed, unknown=unknown)

    def to_json(self, unknown: str = None) -> str:
        """
        Create a JSON representation of the model instance.

        Returns:
            A JSON representation of this message

        """
        return json.dumps(self.serialize(unknown=unknown))

    def __repr__(self) -> str:
        """
        Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        exclude = resolve_meta_property(self, "repr_exclude", [])
        items = (
            "{}={}".format(k, repr(v))
            for k, v in self.__dict__.items()
            if k not in exclude
        )
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))


class BaseModelSchema(Schema):
    """BaseModel schema."""

    class Meta:
        """BaseModelSchema metadata."""

        model_class = None
        skip_values = [None]
        ordered = True

    def __init__(self, *args, **kwargs):
        """
        Initialize BaseModelSchema.

        Raises:
            TypeError: If model_class is not set on Meta

        """
        super().__init__(*args, **kwargs)
        if not self.Meta.model_class:
            raise TypeError(
                "Can't instantiate abstract class {} with no model_class".format(
                    self.__class__.__name__
                )
            )

    @classmethod
    def _get_model_class(cls):
        """
        Get the model class.

        Returns:
            The model class

        """
        return resolve_class(cls.Meta.model_class, cls)

    @property
    def Model(self) -> type:
        """
        Accessor for the schema's model class.

        Returns:
            The model class

        """
        return self._get_model_class()

    @pre_load
    def skip_dump_only(self, data, **kwargs):
        """
        Skip fields that are only expected during serialization.

        Args:
            data: The incoming data to clean

        Returns:
            The modified data

        """
        if not data:
            return data

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
    def make_model(self, data: dict, **kwargs):
        """
        Return model instance after loading.

        Returns:
            A model instance

        """
        try:
            cls_inst = self.Model(**data)
        except TypeError as err:
            if "_type" in str(err) and "_type" in data:
                data["msg_type"] = data["_type"]
                del data["_type"]
            cls_inst = self.Model(**data)
        return cls_inst

    @post_dump
    def remove_skipped_values(self, data, **kwargs):
        """
        Remove values that are are marked to skip.

        Returns:
            Returns this modified data

        """
        skip_vals = resolve_meta_property(self, "skip_values", [])
        return {key: value for key, value in data.items() if value not in skip_vals}
