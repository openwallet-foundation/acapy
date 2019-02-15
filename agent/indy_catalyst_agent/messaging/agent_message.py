import uuid

from typing import Dict

from marshmallow import (
    fields,
    pre_load,
    post_load,
    pre_dump,
    post_dump,
    ValidationError,
)

from ..models.base import (
    BaseModel,
    BaseModelSchema,
    resolve_class,
    resolve_meta_property,
)
from ..models.field_signature import FieldSignature
from ..models.thread_decorator import ThreadDecorator, ThreadDecoratorSchema
from ..wallet.base import BaseWallet


class AgentMessage(BaseModel):
    class Meta:
        handler_class = None
        schema_class = None
        message_type = None

    def __init__(
        self,
        _id: str = None,
        _signatures: Dict[str, FieldSignature] = None,
        _thread: ThreadDecorator = None,
    ):
        super(AgentMessage, self).__init__()
        self._message_id = _id or str(uuid.uuid4())
        self._message_thread = _thread
        self._message_signatures = _signatures.copy() if _signatures else {}
        if not self.Meta.message_type:
            raise TypeError(
                "Can't instantiate abstract class {} with no message_type".format(
                    self.__class__.__name__
                )
            )
        # Not required for now
        # if not self.Meta.handler_class:
        #    raise TypeError(
        #        "Can't instantiate abstract class {} with no handler_class".format(
        #            self.__class__.__name__))

    @classmethod
    def _get_handler_class(cls):
        """ """
        return resolve_class(cls.Meta.handler_class, cls)

    @property
    def Handler(self) -> type:
        """Accessor for the agent message's handler class"""
        return self._get_handler_class()

    @property
    def _type(self) -> str:
        """Accessor for the message type identifier"""
        return self.Meta.message_type

    @property
    def _id(self) -> str:
        """Accessor for the unique message identifier"""
        return self._message_id

    @_id.setter
    def _id(self, val: str):
        """
        Set the unique message identifier
        """
        self._message_id = val

    @property
    def _signatures(self) -> Dict[str, FieldSignature]:
        """Fetch the dictionary of defined field signatures"""
        return self._message_signatures.copy()

    def get_signature(self, field_name: str) -> FieldSignature:
        """
        Get the signature for a named field
        """
        return self._message_signatures.get(field_name)

    def set_signature(self, field_name: str, signature: FieldSignature):
        """
        Add or replace the signature for a named field
        """
        self._message_signatures[field_name] = signature

    async def sign_field(
        self, field_name: str, signer: str, wallet: BaseWallet, timestamp=None
    ) -> FieldSignature:
        """
        Create and store a signature for a named field
        """
        value = getattr(self, field_name, None)
        if value is None:
            raise ValueError(
                "{} field has no value for signature: {}".format(
                    self.__class__.__name__, field_name
                )
            )
        sig = await FieldSignature.create(value, signer, wallet, timestamp)
        self.set_signature(field_name, sig)
        return sig

    async def verify_signed_field(
        self, field_name: str, wallet: BaseWallet, signer: str = None
    ) -> str:
        """
        Verify a specific field signature

        Returns: the verkey of the signer
        """
        if field_name not in self._message_signatures:
            raise ValueError("Missing field signature: {}".format(field_name))
        sig = self._message_signatures[field_name]
        if not await sig.verify(wallet):
            raise ValueError(
                "Field signature verification failed: {}".format(field_name)
            )
        if signer is not None and sig.signer != signer:
            raise ValueError(
                "Signer of signature does not match: {}".format(field_name)
            )
        return sig.signer

    async def verify_signatures(self, wallet: BaseWallet) -> bool:
        """
        Verify all associated field signatures
        """
        for sig in self._message_signatures.values():
            if not await sig.verify(wallet):
                return False
        return True

    @property
    def _thread(self) -> ThreadDecorator:
        """Accessor for the message's thread decorator"""
        return self._message_thread

    @_thread.setter
    def _thread(self, val: ThreadDecorator):
        """
        Setter for the message's thread decorator
        """
        self._message_thread = val


class AgentMessageSchema(BaseModelSchema):
    class Meta:
        model_class = None
        signed_fields = None

    # Avoid clobbering keywords
    _type = fields.Str(data_key="@type", dump_only=True, required=False)
    _id = fields.Str(data_key="@id", required=False)

    # Thread decorator value
    _thread = fields.Nested(ThreadDecoratorSchema, data_key="~thread", required=False)

    def __init__(self, *args, **kwargs):
        super(AgentMessageSchema, self).__init__(*args, **kwargs)
        if not self.Meta.model_class:
            raise TypeError(
                "Can't instantiate abstract class {} with no model_class".format(
                    self.__class__.__name__
                )
            )
        self._signatures = {}

    @pre_load
    def parse_signed_fields(self, data):
        expect_fields = resolve_meta_property(self, "signed_fields") or ()
        found = {}
        for field_name, field_value in data.items():
            if field_name.endswith("~sig"):
                pfx = field_name[:-4]
                if not pfx:
                    raise ValidationError("Unsupported message property: ~sig")
                if pfx not in expect_fields:
                    raise ValidationError(
                        "Encountered unexpected field signature: {}".format(pfx)
                    )
                if pfx in data:
                    raise ValidationError(
                        "Message defines both field signature and value: {}".format(pfx)
                    )
                sig = FieldSignature.deserialize(field_value)
                found[pfx] = sig
                del data[field_name]
                data[pfx], _ts = sig.decode()
        for field_name in expect_fields:
            if field_name not in found:
                raise ValidationError("Expected field signature: {}".format(field_name))
        self._signatures = found
        return data

    @post_load
    def populate_signatures(self, obj):
        for field_name, sig in self._signatures.items():
            obj.set_signature(field_name, sig)
        return obj

    @pre_dump
    def copy_signatures(self, obj):
        self._signatures = obj._signatures
        expect_fields = resolve_meta_property(self, "signed_fields") or ()
        for field_name in expect_fields:
            if field_name not in self._signatures:
                raise ValidationError(
                    "Missing signature for field: {}".format(field_name)
                )
        return obj

    @post_dump
    def replace_signatures(self, data):
        for field_name, sig in self._signatures.items():
            del data[field_name]
            data["{}~sig".format(field_name)] = sig.serialize()
        return data
