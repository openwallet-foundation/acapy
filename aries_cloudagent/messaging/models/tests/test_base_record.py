import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock
from marshmallow import fields

from ....cache.base import BaseCache
from ....config.injection_context import InjectionContext
from ....storage.base import BaseStorage, StorageDuplicateError, StorageRecord
from ....storage.basic import BasicStorage

from ...responder import BaseResponder, MockResponder
from ...util import time_now

from ..base_record import BaseRecord, BaseRecordSchema


class BaseRecordImpl(BaseRecord):
    class Meta:
        schema_class = "BaseRecordImplSchema"

    RECORD_TYPE = "record"
    CACHE_ENABLED = True


class BaseRecordImplSchema(BaseRecordSchema):
    class Meta:
        model_class = BaseRecordImpl


class ARecordImpl(BaseRecord):
    class Meta:
        schema_class = "ARecordImplSchema"

    RECORD_TYPE = "a-record"
    CACHE_ENABLED = False
    RECORD_ID_NAME = "ident"
    TAG_NAMES = {"code"}

    def __init__(self, *, ident=None, a, b, code, **kwargs):
        super().__init__(ident, **kwargs)
        self.a = a
        self.b = b
        self.code = code

    @property
    def record_value(self) -> dict:
        return {"a": self.a, "b": self.b}


class ARecordImplSchema(BaseRecordSchema):
    class Meta:
        model_class = BaseRecordImpl

    ident = fields.Str(attribute="_id")
    a = fields.Str()
    b = fields.Str()
    code = fields.Str()


class UnencTestImpl(BaseRecord):
    TAG_NAMES = {"~a", "~b", "c"}


class TestBaseRecord(AsyncTestCase):
    def test_init_undef(self):
        with self.assertRaises(TypeError):
            BaseRecord()

    def test_from_storage_values(self):
        record_id = "record_id"
        stored = {"created_at": time_now(), "updated_at": time_now()}
        inst = BaseRecordImpl.from_storage(record_id, stored)
        assert isinstance(inst, BaseRecordImpl)
        assert inst._id == record_id
        assert inst.value == stored

        stored[BaseRecordImpl.RECORD_ID_NAME] = inst._id
        with self.assertRaises(ValueError):
            BaseRecordImpl.from_storage(record_id, stored)

    async def test_post_save_new(self):
        context = InjectionContext(enforce_typing=False)
        mock_storage = async_mock.MagicMock()
        mock_storage.add_record = async_mock.CoroutineMock()
        context.injector.bind_instance(BaseStorage, mock_storage)
        record = BaseRecordImpl()
        with async_mock.patch.object(
            record, "post_save", async_mock.CoroutineMock()
        ) as post_save:
            await record.save(context, reason="reason", webhook=True)
            post_save.assert_called_once_with(context, True, None, True)
        mock_storage.add_record.assert_called_once()

    async def test_post_save_exist(self):
        context = InjectionContext(enforce_typing=False)
        mock_storage = async_mock.MagicMock()
        mock_storage.update_record_value = async_mock.CoroutineMock()
        mock_storage.update_record_tags = async_mock.CoroutineMock()
        context.injector.bind_instance(BaseStorage, mock_storage)
        record = BaseRecordImpl()
        last_state = "last_state"
        record._last_state = last_state
        record._id = "id"
        with async_mock.patch.object(
            record, "post_save", async_mock.CoroutineMock()
        ) as post_save:
            await record.save(context, reason="reason", webhook=False)
            post_save.assert_called_once_with(context, False, last_state, False)
        mock_storage.update_record_value.assert_called_once()
        mock_storage.update_record_tags.assert_called_once()

    async def test_cache(self):
        assert not await BaseRecordImpl.get_cached_key(None, None)
        await BaseRecordImpl.set_cached_key(None, None, None)
        await BaseRecordImpl.clear_cached_key(None, None)
        context = InjectionContext(enforce_typing=False)
        mock_cache = async_mock.MagicMock(BaseCache, autospec=True)
        context.injector.bind_instance(BaseCache, mock_cache)
        record = BaseRecordImpl()
        cache_key = "cache_key"
        cache_result = await BaseRecordImpl.get_cached_key(context, cache_key)
        mock_cache.get.assert_awaited_once_with(cache_key)
        assert cache_result is mock_cache.get.return_value

        await record.set_cached_key(context, cache_key, record)
        mock_cache.set.assert_awaited_once_with(cache_key, record, record.CACHE_TTL)

        await record.clear_cached_key(context, cache_key)
        mock_cache.clear.assert_awaited_once_with(cache_key)

    async def test_retrieve_cached_id(self):
        context = InjectionContext(enforce_typing=False)
        mock_storage = async_mock.MagicMock(BaseStorage, autospec=True)
        context.injector.bind_instance(BaseStorage, mock_storage)
        record_id = "record_id"
        stored = {"created_at": time_now(), "updated_at": time_now()}
        with async_mock.patch.object(
            BaseRecordImpl, "get_cached_key"
        ) as get_cached_key, async_mock.patch.object(
            BaseRecordImpl, "cache_key"
        ) as cache_key:
            get_cached_key.return_value = stored
            result = await BaseRecordImpl.retrieve_by_id(context, record_id, True)
            cache_key.assert_called_once_with(record_id)
            get_cached_key.assert_awaited_once_with(context, cache_key.return_value)
            mock_storage.get_record.assert_not_called()
            assert isinstance(result, BaseRecordImpl)
            assert result._id == record_id
            assert result.value == stored

    async def test_retrieve_by_tag_filter_multi_x_delete(self):
        context = InjectionContext(enforce_typing=False)
        basic_storage = BasicStorage()
        context.injector.bind_instance(BaseStorage, basic_storage)
        records = []
        for i in range(3):
            records.append(ARecordImpl(a="1", b=str(i), code="one"))
            await records[i].save(context)
        with self.assertRaises(StorageDuplicateError):
            await ARecordImpl.retrieve_by_tag_filter(
                context, {"code": "one"}, {"a": "1"}
            )
        await records[0].delete_record(context)

    async def test_save_x(self):
        context = InjectionContext(enforce_typing=False)
        basic_storage = BasicStorage()
        context.injector.bind_instance(BaseStorage, basic_storage)
        rec = ARecordImpl(a="1", b="0", code="one")
        with async_mock.patch.object(
            context, "inject", async_mock.CoroutineMock()
        ) as mock_inject:
            mock_inject.return_value = async_mock.MagicMock(
                add_record=async_mock.CoroutineMock(side_effect=ZeroDivisionError())
            )
            with self.assertRaises(ZeroDivisionError):
                await rec.save(context)

    async def test_neq(self):
        a_rec = ARecordImpl(a="1", b="0", code="one")
        b_rec = BaseRecordImpl()
        assert a_rec != b_rec

    async def test_retrieve_uncached_id(self):
        context = InjectionContext(enforce_typing=False)
        mock_storage = async_mock.MagicMock(BaseStorage, autospec=True)
        context.injector.bind_instance(BaseStorage, mock_storage)
        record_id = "record_id"
        record_value = {"created_at": time_now(), "updated_at": time_now()}
        stored = StorageRecord(
            BaseRecordImpl.RECORD_TYPE, json.dumps(record_value), {}, record_id
        )
        with async_mock.patch.object(
            BaseRecordImpl, "set_cached_key"
        ) as set_cached_key, async_mock.patch.object(
            BaseRecordImpl, "cache_key"
        ) as cache_key:
            mock_storage.get_record.return_value = stored
            result = await BaseRecordImpl.retrieve_by_id(context, record_id, False)
            mock_storage.get_record.assert_awaited_once_with(
                BaseRecordImpl.RECORD_TYPE, record_id, {"retrieveTags": False}
            )
            set_cached_key.assert_awaited_once_with(
                context, cache_key.return_value, record_value
            )
            assert isinstance(result, BaseRecordImpl)
            assert result._id == record_id
            assert result.value == record_value

    async def test_query(self):
        context = InjectionContext(enforce_typing=False)
        mock_storage = async_mock.MagicMock(BaseStorage, autospec=True)
        context.injector.bind_instance(BaseStorage, mock_storage)
        record_id = "record_id"
        record_value = {"created_at": time_now(), "updated_at": time_now()}
        tag_filter = {"tag": "filter"}
        stored = StorageRecord(
            BaseRecordImpl.RECORD_TYPE, json.dumps(record_value), {}, record_id
        )

        mock_storage.search_records.return_value.__aiter__.return_value = [stored]
        result = await BaseRecordImpl.query(context, tag_filter)
        mock_storage.search_records.assert_called_once_with(
            BaseRecordImpl.RECORD_TYPE, tag_filter, None, {"retrieveTags": False}
        )
        assert result and isinstance(result[0], BaseRecordImpl)
        assert result[0]._id == record_id
        assert result[0].value == record_value

    @async_mock.patch("builtins.print")
    def test_log_state(self, mock_print):
        test_param = "test.log"
        context = InjectionContext(settings={test_param: 1})
        with async_mock.patch.object(
            BaseRecordImpl, "LOG_STATE_FLAG", test_param
        ) as cls:
            record = BaseRecordImpl()
            record.log_state(context, msg="state", params={"a": "1", "b": "2"})
        mock_print.assert_called_once()

    @async_mock.patch("builtins.print")
    def test_skip_log(self, mock_print):
        context = InjectionContext()
        record = BaseRecordImpl()
        record.log_state(context, "state")
        mock_print.assert_not_called()

    async def test_webhook(self):
        context = InjectionContext()
        mock_responder = MockResponder()
        context.injector.bind_instance(BaseResponder, mock_responder)
        record = BaseRecordImpl()
        payload = {"test": "payload"}
        topic = "topic"
        await record.send_webhook(context, None, None)  # cover short circuit
        await record.send_webhook(context, "hello", None)  # cover short circuit
        await record.send_webhook(context, payload, topic=topic)
        assert mock_responder.webhooks == [(topic, payload)]

    async def test_tag_prefix(self):
        tags = {"~x": "a", "y": "b"}
        assert UnencTestImpl.strip_tag_prefix(tags) == {"x": "a", "y": "b"}

        tags = {"a": "x", "b": "y", "c": "z"}
        assert UnencTestImpl.prefix_tag_filter(tags) == {"~a": "x", "~b": "y", "c": "z"}

        tags = {"$not": {"a": "x", "b": "y", "c": "z"}}
        expect = {"$not": {"~a": "x", "~b": "y", "c": "z"}}
        actual = UnencTestImpl.prefix_tag_filter(tags)
        assert {**expect} == {**actual}

        tags = {"$or": [{"a": "x"}, {"c": "z"}]}
        assert UnencTestImpl.prefix_tag_filter(tags) == {
            "$or": [{"~a": "x"}, {"c": "z"}]
        }
