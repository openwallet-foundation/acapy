from ..models import BaseModel, BaseModelSchema
from ..models.thread_decorator import ThreadDecorator, ThreadDecoratorSchema

from marshmallow import fields


class AgentMessage(BaseModel):
    class Meta:
        handler_class = None
        schema_class = None
        message_type = None

    def __init__(self, _id: str = None, _thread: ThreadDecorator = None):
        super(AgentMessage, self).__init__()
        self._message_id = _id
        self._message_thread = _thread
        if not self.Meta.message_type:
            raise TypeError(
                "Can't instantiate abstract class {} with no message_type".format(
                    self.__class__.__name__))
        # Not required for now
        #if not self.Meta.handler_class:
        #    raise TypeError(
        #        "Can't instantiate abstract class {} with no handler_class".format(
        #            self.__class__.__name__))

    @property
    def Handler(self):
        return self.Meta.handler_class

    @property
    def _handler(self):
        return self.Handler(self)

    @property
    def _type(self) -> str:
        return self.Meta.message_type

    @property
    def _id(self) -> str:
        return self._message_id

    @_id.setter
    def _id(self, val: str):
        self._message_id = val

    @property
    def _thread(self) -> ThreadDecorator:
        return self._message_thread

    @_thread.setter
    def _thread(self, val: ThreadDecorator):
        self._message_thread = val


class AgentMessageSchema(BaseModelSchema):
    class Meta:
        model_class = None

    def __init__(self, *args, **kwargs):
        super(AgentMessageSchema, self).__init__(*args, **kwargs)
        if not self.Meta.model_class:
            raise TypeError(
                "Can't instantiate abstract class {} with no model_class".format(
                    self.__class__.__name__))

    # Avoid clobbering keywords
    _type = fields.Str(data_key="@type", dump_only=True, required=False)
    _id = fields.Str(data_key="@id", required=False)
    # Decorator value
    _thread = fields.Nested(ThreadDecoratorSchema, data_key="~thread", required=False)
