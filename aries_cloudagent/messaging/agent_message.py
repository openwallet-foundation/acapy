"""Agent message base class and schema."""

import uuid
from collections import OrderedDict
from re import sub
from typing import Mapping, Optional, Text, Union

from marshmallow import (
    EXCLUDE,
    ValidationError,
    fields,
    post_dump,
    post_load,
    pre_dump,
    pre_load,
)

from ..protocols.didcomm_prefix import DIDCommPrefix
from ..wallet.base import BaseWallet
from .base_message import BaseMessage, DIDCommVersion
from .decorators.base import BaseDecoratorSet
from .decorators.default import DecoratorSet
from .decorators.service_decorator import ServiceDecorator
from .decorators.signature_decorator import SignatureDecorator  # TODO deprecated
from .decorators.thread_decorator import ThreadDecorator
from .decorators.trace_decorator import (
    TRACE_LOG_TARGET,
    TRACE_MESSAGE_TARGET,
    TraceDecorator,
    TraceReport,
)
from .models.base import (
    BaseModel,
    BaseModelError,
    BaseModelSchema,
    resolve_class,
    resolve_meta_property,
)
from .valid import UUID4_EXAMPLE


class AgentMessageError(BaseModelError):
    """Base exception for agent message issues."""


class AgentMessage(BaseModel, BaseMessage):
    """Agent message base class."""

    class Meta:
        """AgentMessage metadata."""

        handler_class = None
        schema_class = None
        message_type = None

    def __init__(
        self,
        _id: str = None,
        _type: Optional[Text] = None,
        _version: Optional[Text] = None,
        _decorators: BaseDecoratorSet = None,
    ):
        """
        Initialize base agent message object.

        Args:
            _id: Agent message id
            _decorators: Message decorators

        Raises:
            TypeError: If message type is missing on subclass Meta class

        """
        super().__init__()
        if _id:
            self._message_id = _id
            self._message_new_id = False
        else:
            self._message_id = str(uuid.uuid4())
            self._message_new_id = True
        self._message_decorators = (
            _decorators if _decorators is not None else DecoratorSet()
        )
        if not self.Meta.message_type:
            raise TypeError(
                "Can't instantiate abstract class {} with no message_type".format(
                    self.__class__.__name__
                )
            )
        if _type:
            self._message_type = _type
        elif _version:
            self._message_type = self.get_updated_msg_type(_version)
        else:
            self._message_type = self.Meta.message_type
        # Not required for now
        # if not self.Meta.handler_class:
        #    raise TypeError(
        #        "Can't instantiate abstract class {} with no handler_class".format(
        #            self.__class__.__name__))

    @classmethod
    def _get_handler_class(cls):
        """
        Get handler class.

        Returns:
            The resolved class defined on `Meta.handler_class`

        """
        return resolve_class(cls.Meta.handler_class, cls)

    @property
    def Handler(self) -> type:
        """
        Accessor for the agent message's handler class.

        Returns:
            Handler class

        """
        return self._get_handler_class()

    @property
    def _type(self) -> str:
        """
        Accessor for the message type identifier.

        Returns:
            Current DIDComm prefix, slash, message type defined on `Meta.message_type`

        """
        return DIDCommPrefix.qualify_current(self._message_type)

    @_type.setter
    def _type(self, msg_type: str):
        """Set the message type identifier."""
        self._message_type = msg_type

    @property
    def _id(self) -> str:
        """
        Accessor for the unique message identifier.

        Returns:
            The id of this message

        """
        return self._message_id

    @_id.setter
    def _id(self, val: str):
        """Set the unique message identifier."""
        self._message_id = val

    @property
    def _decorators(self) -> BaseDecoratorSet:
        """Fetch the message's decorator set."""
        return self._message_decorators

    @_decorators.setter
    def _decorators(self, value: BaseDecoratorSet):
        """Fetch the message's decorator set."""
        self._message_decorators = value

    def get_updated_msg_type(self, version: str) -> str:
        """Update version to Meta.message_type."""
        return sub(r"(\d+\.)?(\*|\d+)", version, self.Meta.message_type)

    def get_signature(self, field_name: str) -> SignatureDecorator:
        """
        Get the signature for a named field.

        Args:
            field_name: Field name to get the signature for

        Returns:
            A SignatureDecorator for the requested field name

        """
        return self._decorators.field(field_name).get("sig")

    def set_signature(self, field_name: str, signature: SignatureDecorator):
        """
        Add or replace the signature for a named field.

        Args:
            field_name: Field to set signature on
            signature: Signature for the field

        """
        self._decorators.field(field_name)["sig"] = signature

    async def sign_field(  # TODO migrate to signed-attachment per RFC 17
        self, field_name: str, signer_verkey: str, wallet: BaseWallet, timestamp=None
    ) -> SignatureDecorator:
        """
        Create and store a signature for a named field.

        Args:
            field_name: Field to sign
            signer_verkey: Verkey of signer
            wallet: Wallet to use for signature
            timestamp: Optional timestamp for signature

        Returns:
            A SignatureDecorator for newly created signature

        Raises:
            ValueError: If field_name doesn't exist on this message

        """
        value = getattr(self, field_name, None)
        if value is None:
            raise BaseModelError(
                "{} field has no value for signature: {}".format(
                    self.__class__.__name__, field_name
                )
            )
        sig = await SignatureDecorator.create(value, signer_verkey, wallet, timestamp)
        self.set_signature(field_name, sig)
        return sig

    async def verify_signed_field(  # TODO migrate to signed-attachment per RFC 17
        self, field_name: str, wallet: BaseWallet, signer_verkey: str = None
    ) -> str:
        """
        Verify a specific field signature.

        Args:
            field_name: The field name to verify
            wallet: Wallet to use for the verification
            signer_verkey: Verkey of signer to use

        Returns:
            The verkey of the signer

        Raises:
            ValueError: If field_name does not exist on this message
            ValueError: If the verification fails
            ValueError: If the verkey of the signature does not match the
            provided verkey

        """
        sig = self.get_signature(field_name)
        if not sig:
            raise BaseModelError("Missing field signature: {}".format(field_name))
        if not await sig.verify(wallet):
            raise BaseModelError(
                "Field signature verification failed: {}".format(field_name)
            )
        if signer_verkey is not None and sig.signer != signer_verkey:
            raise BaseModelError(
                "Signer verkey of signature does not match: {}".format(field_name)
            )
        return sig.signer

    async def verify_signatures(self, wallet: BaseWallet) -> bool:
        """
        Verify all associated field signatures.

        Args:
            wallet: Wallet to use in verification

        Returns:
            True if all signatures verify, else false

        """
        for field in self._decorators.fields.values():
            if "sig" in field and not await field["sig"].verify(wallet):
                return False
        return True

    @property
    def _service(self) -> ServiceDecorator:
        """
        Accessor for the message's service decorator.

        Returns:
            The ServiceDecorator for this message

        """
        return self._decorators.get("service")

    @_service.setter
    def _service(self, val: Union[ServiceDecorator, dict]):
        """
        Setter for the message's service decorator.

        Args:
            val: ServiceDecorator or dict to set as the service
        """
        if val is None:
            self._decorators.pop("service", None)
        else:
            self._decorators["service"] = val

    @property
    def _thread(self) -> ThreadDecorator:
        """
        Accessor for the message's thread decorator.

        Returns:
            The ThreadDecorator for this message

        """
        return self._decorators.get("thread")

    @_thread.setter
    def _thread(self, val: Union[ThreadDecorator, dict]):
        """
        Setter for the message's thread decorator.

        Args:
            val: ThreadDecorator or dict to set as the thread
        """
        if val is None:
            self._decorators.pop("thread", None)
        else:
            self._decorators["thread"] = val

    @property
    def _thread_id(self) -> str:
        """Accessor for the ID associated with this message."""
        if self._thread and self._thread.thid:
            return self._thread.thid
        return self._message_id

    def assign_thread_from(self, msg: "AgentMessage"):
        """
        Copy thread information from a previous message.

        Args:
            msg: The received message containing optional thread information
        """
        if msg:
            thread = msg._thread
            thid = thread and thread.thid or msg._message_id
            pthid = thread and thread.pthid
            self.assign_thread_id(thid, pthid)

    def assign_thread_id(self, thid: str, pthid: str = None):
        """
        Assign a specific thread ID.

        Args:
            thid: The thread identifier
            pthid: The parent thread identifier
        """
        if thid or pthid:
            self._thread = ThreadDecorator(thid=thid, pthid=pthid)
        else:
            self._thread = None

    @property
    def _trace(self) -> TraceDecorator:
        """
        Accessor for the message's trace decorator.

        Returns:
            The TraceDecorator for this message

        """
        return self._decorators.get("trace")

    @_trace.setter
    def _trace(self, val: Union[TraceDecorator, dict]):
        """
        Setter for the message's trace decorator.

        Args:
            val: TraceDecorator or dict to set as the trace
        """
        if val is None:
            self._decorators.pop("trace", None)
        else:
            self._decorators["trace"] = val

    def assign_trace_from(self, msg: "AgentMessage"):
        """
        Copy trace information from a previous message.

        Args:
            msg: The received message containing optional trace information
        """
        if msg and msg._trace:
            # ignore if not a valid type
            if isinstance(msg._trace, TraceDecorator) or isinstance(msg._trace, dict):
                self._trace = msg._trace

    def assign_trace_decorator(self, context, trace):
        """
        Copy trace from a json structure.

        Args:
            trace: string containing trace json stucture
        """
        if trace:
            self.add_trace_decorator(
                target=context.get("trace.target") if context else TRACE_LOG_TARGET,
                full_thread=True,
            )

    def add_trace_decorator(
        self, target: str = TRACE_LOG_TARGET, full_thread: bool = True
    ):
        """
        Create a new trace decorator.

        Args:
            target: The trace target
            full_thread: Full thread flag
        """
        if self._trace:
            # don't replace if there is already a trace decorator
            # (potentially holding trace reports already)
            self._trace._target = target
            self._trace._full_thread = full_thread
        else:
            self._trace = TraceDecorator(target=target, full_thread=full_thread)

    def add_trace_report(self, val: Union[TraceReport, dict]):
        """
        Append a new trace report.

        Args:
            val: The trace target
        """
        if not self._trace:
            self.add_trace_decorator(target=TRACE_MESSAGE_TARGET, full_thread=True)
        self._trace.append_trace_report(val)

    def serialize(self, msg_format: DIDCommVersion = DIDCommVersion.v1, **kwargs):
        """Return serialized message in format specified."""
        if msg_format is DIDCommVersion.v2:
            raise NotImplementedError("DIDComm v2 is not yet supported")

        return super().serialize(**kwargs)

    @classmethod
    def deserialize(
        cls, value: dict, msg_format: DIDCommVersion = DIDCommVersion.v1, **kwargs
    ):
        """Return message object deserialized from value in format specified."""
        if msg_format is DIDCommVersion.v2:
            raise NotImplementedError("DIDComm v2 is not yet supported")

        return super().deserialize(value, **kwargs)


class AgentMessageSchema(BaseModelSchema):
    """AgentMessage schema."""

    class Meta:
        """AgentMessageSchema metadata."""

        model_class = None
        signed_fields = None
        unknown = EXCLUDE

    # Avoid clobbering keywords
    _type = fields.Str(
        data_key="@type",
        dump_only=True,
        required=False,
        metadata={
            "description": "Message type",
            "example": "https://didcomm.org/my-family/1.0/my-message-type",
        },
    )
    _id = fields.Str(
        data_key="@id",
        required=False,
        metadata={"description": "Message identifier", "example": UUID4_EXAMPLE},
    )

    def __init__(self, *args, **kwargs):
        """
        Initialize an instance of AgentMessageSchema.

        Raises:
            TypeError: If Meta.model_class has not been set

        """
        super().__init__(*args, **kwargs)
        self._decorators = DecoratorSet()
        self._decorators_dict = None
        self._signatures = {}

    @pre_load
    def extract_decorators(self, data: Mapping, **kwargs):
        """
        Pre-load hook to extract the decorators and check the signed fields.

        Args:
            data: Incoming data to parse

        Returns:
            Parsed and modified data

        Raises:
            ValidationError: If a field signature does not correlate
            to a field in the message
            ValidationError: If the message defines both a field signature
            and a value for the same field
            ValidationError: If there is a missing field signature

        """
        processed = self._decorators.extract_decorators(data, self.__class__)

        expect_fields = resolve_meta_property(self, "signed_fields") or ()
        found_signatures = {}
        for field_name, field in self._decorators.fields.items():
            if "sig" in field:
                if field_name not in expect_fields:
                    raise ValidationError(
                        f"Encountered unexpected field signature: {field_name}"
                    )
                if field_name in processed:
                    raise ValidationError(
                        f"Message defines both field signature and value: {field_name}"
                    )
                found_signatures[field_name] = field["sig"]
                processed[field_name], _ = field["sig"].decode()  # _ = timestamp
        for field_name in expect_fields:
            if field_name not in found_signatures:
                raise ValidationError(f"Expected field signature: {field_name}")
        return processed

    @post_load
    def populate_decorators(self, obj, **kwargs):
        """
        Post-load hook to populate decorators on the message.

        Args:
            obj: The AgentMessage object

        Returns:
            The AgentMessage object with populated decorators

        """
        obj._decorators = self._decorators
        return obj

    @pre_dump
    def check_dump_decorators(self, obj, **kwargs):
        """
        Pre-dump hook to validate and load the message decorators.

        Args:
            obj: The AgentMessage object

        Raises:
            BaseModelError: If a decorator does not validate

        """
        decorators = obj._decorators.copy()
        signatures = OrderedDict()
        for name, field in decorators.fields.items():
            if "sig" in field:
                signatures[name] = field["sig"].serialize()
                del field["sig"]
        self._decorators_dict = decorators.to_dict()
        self._signatures = signatures

        # check existence of signatures
        expect_fields = resolve_meta_property(self, "signed_fields") or ()
        for field_name in expect_fields:
            if field_name not in self._signatures:
                raise BaseModelError(
                    "Missing signature for field: {}".format(field_name)
                )

        return obj

    @post_dump
    def dump_decorators(self, data, **kwargs):
        """
        Post-dump hook to write the decorators to the serialized output.

        Args:
            obj: The serialized data

        Returns:
            The modified data

        """
        result = OrderedDict()
        for key in ("@type", "@id"):
            if key in data:
                result[key] = data.pop(key)
        result.update(self._decorators_dict)
        result.update(data)
        return result

    @post_dump
    def replace_signatures(self, data, **kwargs):
        """
        Post-dump hook to write the signatures to the serialized output.

        Args:
            obj: The serialized data

        Returns:
            The modified data

        """
        for field_name, sig in self._signatures.items():
            del data[field_name]
            data["{}~sig".format(field_name)] = sig
        return data
