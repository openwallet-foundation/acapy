import pytest
from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase
from ......messaging.models.base import BaseModelError
from ..reuse import HandshakeReuse, HandshakeReuseSchema


class TestReuseMessage(TestCase):
    """Test request schema."""

    reuse_msg = HandshakeReuse()
    reuse_msg.assign_thread_id(thid="test_thid", pthid="test_pthid")

    def test_init(self):
        """Test initialization of Handshake Reuse message."""
        assert isinstance(self.reuse_msg, HandshakeReuse)
        assert isinstance(self.reuse_msg._id, str)
        assert len(self.reuse_msg._id) > 4
        assert self.reuse_msg._thread.thid == "test_thid"
        assert self.reuse_msg._thread.pthid == "test_pthid"

    def test_make_model(self):
        data = self.reuse_msg.serialize()
        model_instance = HandshakeReuse.deserialize(data)
        assert isinstance(model_instance, HandshakeReuse)
