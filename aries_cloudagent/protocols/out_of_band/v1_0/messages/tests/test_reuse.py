"""Test Reuse Message."""
import pytest

from asynctest import TestCase as AsyncTestCase
from unittest import mock, TestCase

from ......messaging.models.base import BaseModelError

from ..reuse import HandshakeReuse, HandshakeReuseSchema


class TestReuseMessage(TestCase):
    """Test request schema."""

    def setUp(self):
        self.reuse_msg = HandshakeReuse()

    def test_init(self):
        """Test initialization of Handshake Reuse message."""
        self.reuse_msg.assign_thread_id(thid="test_thid", pthid="test_pthid")
        assert isinstance(self.reuse_msg, HandshakeReuse)
        assert isinstance(self.reuse_msg._id, str)
        assert len(self.reuse_msg._id) > 4
        assert self.reuse_msg._thread.thid == "test_thid"
        assert self.reuse_msg._thread.pthid == "test_pthid"

    def test_make_model(self):
        """Make reuse model."""
        self.reuse_msg.assign_thread_id(thid="test_thid", pthid="test_pthid")
        data = self.reuse_msg.serialize()
        model_instance = HandshakeReuse.deserialize(data)
        assert isinstance(model_instance, HandshakeReuse)

    def test_pre_dump_x(self):
        """Exercise pre-dump serialization requirements."""
        with pytest.raises(BaseModelError):
            data = self.reuse_msg.serialize()

    def test_assign_msg_type_version_to_model_inst(self):
        test_msg = HandshakeReuse()
        assert "1.1" in test_msg._type
        assert "1.1" in HandshakeReuse.Meta.message_type
        test_msg = HandshakeReuse(version="1.2")
        assert "1.2" in test_msg._type
        assert "1.1" in HandshakeReuse.Meta.message_type
