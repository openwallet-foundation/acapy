"""Agent message base class and schema."""

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

from ..wallet.base import BaseWallet

from .models.base import (
    BaseModel,
    BaseModelError,
    BaseModelSchema,
    resolve_class,
    resolve_meta_property,
)
from .models.field_signature import FieldSignature
from .decorators.localization_decorator import (
    LocalizationDecorator,
    LocalizationDecoratorSchema,
)
from .decorators.thread_decorator import ThreadDecorator, ThreadDecoratorSchema
from .decorators.timing_decorator import TimingDecorator, TimingDecoratorSchema
from .decorators.transport_decorator import TransportDecorator, TransportDecoratorSchema


class AgentMessageError(BaseModelError):
    """Base exception for agent message issues."""


class AgentMessage(BaseModel):
    """Agent message base class."""

    class Meta:
        """AgentMessage metadata."""

        handler_class = None
        schema_class = None
        message_type = None

    def __init__(
        self,
        _id: str = None,
        _l10n: LocalizationDecorator = None,
        _signatures: Dict[str, FieldSignature] = None,
        _thread: ThreadDecorator = None,
        _timing: TimingDecorator = None,
        _transport: TransportDecorator = None,
    ):
        """
        Initialize base agent message object.

        Args:
            _id: Agent message id
            _l10n: LocalizationDecorator instance
            _signatures: Message signatures
            _thread: ThreadDecorator instance
            _timing: TimingDecorator instance
            _transport: TransportDecorator instance

        Raises:
            TypeError: If message type is missing on subclass Meta class

        """
        super(AgentMessage, self).__init__()
        if _id:
            self._message_id = _id
            self._message_new_id = False
        else:
            self._message_id = str(uuid.uuid4())
            self._message_new_id = True
        self._message_l10n = _l10n
        self._message_thread = _thread
        self._message_timing = _timing
        self._message_transport = _transport
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
            Message type defined on `Meta.message_type`

        """
        return self.Meta.message_type

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
    def _l10n(self) -> LocalizationDecorator:
        """Accessor for the localization decorator."""
        return self._message_l10n

    @_l10n.setter
    def _l10n(self, val: LocalizationDecorator):
        """Set the localization decorator."""
        self._message_l10n = val

    @property
    def _signatures(self) -> Dict[str, FieldSignature]:
        """
        Fetch the dictionary of defined field signatures.

        Returns:
            A copy of the message_signatures for this message.

        """
        return self._message_signatures.copy()

    def get_signature(self, field_name: str) -> FieldSignature:
        """
        Get the signature for a named field.

        Args:
            field_name: Field name to get signatures for

        Returns:
            A FieldSignature for the requested field name

        """
        return self._message_signatures.get(field_name)

    def set_signature(self, field_name: str, signature: FieldSignature):
        """
        Add or replace the signature for a named field.

        Args:
            field_name: Field to set signature on
            signature: Signature for the field

        """
        self._message_signatures[field_name] = signature

    async def sign_field(
        self, field_name: str, signer_verkey: str, wallet: BaseWallet, timestamp=None
    ) -> FieldSignature:
        """
        Create and store a signature for a named field.

        Args:
            field_name: Field to sign
            signer_verkey: Verkey of signer
            wallet: Wallet to use for signature
            timestamp: Optional timestamp for signature

        Returns:
            A FieldSignature for newly created signature

        Raises:
            ValueError: If field_name doesn't exist on this message

        """
        value = getattr(self, field_name, None)
        if value is None:
            raise ValueError(
                "{} field has no value for signature: {}".format(
                    self.__class__.__name__, field_name
                )
            )
        sig = await FieldSignature.create(value, signer_verkey, wallet, timestamp)
        self.set_signature(field_name, sig)
        return sig

    async def verify_signed_field(
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
        if field_name not in self._message_signatures:
            raise ValueError("Missing field signature: {}".format(field_name))
        sig = self._message_signatures[field_name]
        if not await sig.verify(wallet):
            raise ValueError(
                "Field signature verification failed: {}".format(field_name)
            )
        if signer_verkey is not None and sig.signer != signer_verkey:
            raise ValueError(
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
        for sig in self._message_signatures.values():
            if not await sig.verify(wallet):
                return False
        return True

    @property
    def _thread(self) -> ThreadDecorator:
        """
        Accessor for the message's thread decorator.

        Returns:
            The ThreadDecorator for this message

        """
        return self._message_thread

    @_thread.setter
    def _thread(self, val: ThreadDecorator):
        """
        Setter for the message's thread decorator.

        Args:
            val: ThreadDecorator to set as the thread
        """
        self._message_thread = val

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
            thid = msg._thread and msg._thread.thid or msg._message_id
            pthid = msg._thread and msg._thread.pthid
            self.assign_thread_id(thid, pthid)

    def assign_thread_id(self, thid: str, pthid: str = None):
        """
        Assign a specific thread ID.

        Args:
            thid: The thread identifier
            pthid: The parent thread identifier
        """
        self._thread = ThreadDecorator(thid=thid, pthid=pthid)

    @property
    def _timing(self) -> TimingDecorator:
        """Accessor for the timing decorator."""
        return self._message_timing

    @_timing.setter
    def _timing(self, val: TimingDecorator):
        """Set the timing decorator."""
        self._message_timing = val

    @property
    def _transport(self) -> TransportDecorator:
        """Accessor for the transport decorator."""
        return self._message_transport

    @_transport.setter
    def _transport(self, val: TransportDecorator):
        """Set the transport decorator."""
        self._message_transport = val


class AgentMessageSchema(BaseModelSchema):
    """AgentMessage schema."""

    class Meta:
        """AgentMessageSchema metadata."""

        model_class = None
        signed_fields = None

    # Avoid clobbering keywords
    _type = fields.Str(data_key="@type", dump_only=True, required=False)
    _id = fields.Str(data_key="@id", required=False)

    # Localization decorator
    _l10n = fields.Nested(LocalizationDecoratorSchema, data_key="~l10n", required=False)

    # Thread decorator
    _thread = fields.Nested(ThreadDecoratorSchema, data_key="~thread", required=False)

    # Timing decorator
    _timing = fields.Nested(TimingDecoratorSchema, data_key="~timing", required=False)

    # Transport decorator
    _transport = fields.Nested(
        TransportDecoratorSchema, data_key="~transport", required=False
    )

    def __init__(self, *args, **kwargs):
        """
        Initialize an instance of AgentMessageSchema.

        Raises:
            TypeError: If Meta.model_class has not been set

        """
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
        """
        Pre-load hook to parse all of the signed fields.

        Args:
            data: Incoming data to parse

        Returns:
            Parsed and modified data

        Raises:
            ValidationError: If the field name prefix does not exist
            ValidationError: If the field signature does not correlate
                to a field in the message
            ValidationError: If the message defines both a field signature
                and a value
            ValidationError: If there is a missing field signature

        """
        expect_fields = resolve_meta_property(self, "signed_fields") or ()
        found_signatures = {}
        processed = {}
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
                found_signatures[pfx] = sig
                processed[pfx], _ts = sig.decode()
            else:
                processed[field_name] = field_value
        for field_name in expect_fields:
            if field_name not in found_signatures:
                raise ValidationError("Expected field signature: {}".format(field_name))
        self._signatures = found_signatures
        return processed

    @post_load
    def populate_signatures(self, obj):
        """
        Post-load hook to populate signatures on the message.

        Args:
            obj: The AgentMessage object

        Returns:
            The AgentMessage object with populated signatures

        """
        for field_name, sig in self._signatures.items():
            obj.set_signature(field_name, sig)
        return obj

    @pre_dump
    def copy_signatures(self, obj):
        """
        Pre-dump hook to copy the message signatures into the serialized output.

        Args:
            obj: The AgentMessage object

        Returns:
            The modified object

        Raises:
            ValidationError: If a signature is missing

        """
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
        """
        Post-dump hook to write the signatures to the serialized output.

        Args:
            obj: The serialized data

        Returns:
            The modified data

        """
        for field_name, sig in self._signatures.items():
            del data[field_name]
            data["{}~sig".format(field_name)] = sig.serialize()
        return data
