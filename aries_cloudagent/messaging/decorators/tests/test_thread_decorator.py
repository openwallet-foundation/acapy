from ..thread_decorator import ThreadDecorator

from unittest import TestCase


class TestThreadDecorator(TestCase):
    thread_id = "tid-001"
    parent_id = "tid-000"
    sender_order = 1
    received_orders = {"did": 2}

    def test_init(self):
        decorator = ThreadDecorator(
            thid=self.thread_id,
            pthid=self.parent_id,
            sender_order=self.sender_order,
            received_orders=self.received_orders,
        )
        assert decorator.thid == self.thread_id
        assert decorator.pthid == self.parent_id
        assert decorator.sender_order == self.sender_order
        assert decorator.received_orders == self.received_orders

    def test_serialize_load(self):
        decorator = ThreadDecorator(
            thid=self.thread_id,
            pthid=self.parent_id,
            sender_order=self.sender_order,
            received_orders=self.received_orders,
        )

        dumped = decorator.serialize()
        loaded = ThreadDecorator.deserialize(dumped)

        assert loaded.thid == self.thread_id
        assert loaded.pthid == self.parent_id
        assert loaded.sender_order == self.sender_order
        assert loaded.received_orders == self.received_orders

        loaded.pthid = "dummy"
        assert loaded.pthid == "dummy"
