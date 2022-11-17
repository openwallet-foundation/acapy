"""Test Reuse Accept Message."""
import pytest

from asynctest import TestCase as AsyncTestCase
from unittest import mock, TestCase

from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ..reuse_accept import HandshakeReuseAccept, HandshakeReuseAcceptSchema


class TestReuseAcceptMessage(TestCase):
    """Test request schema."""

    def setUp(self):
        self.reuse_accept_msg = HandshakeReuseAccept()

    def test_init(self):
        """Test initialization of Handshake Reuse message."""
        self.reuse_accept_msg.assign_thread_id(thid="test_thid", pthid="test_pthid")
        assert isinstance(self.reuse_accept_msg, HandshakeReuseAccept)
        assert isinstance(self.reuse_accept_msg._id, str)
        assert len(self.reuse_accept_msg._id) > 4
        assert self.reuse_accept_msg._thread.thid == "test_thid"
        assert self.reuse_accept_msg._thread.pthid == "test_pthid"

    def test_make_model(self):
        """Make reuse-accept model."""
        self.reuse_accept_msg.assign_thread_id(thid="test_thid", pthid="test_pthid")
        data = self.reuse_accept_msg.serialize()
        model_instance = HandshakeReuseAccept.deserialize(data)
        assert isinstance(model_instance, HandshakeReuseAccept)

    def test_make_model_backward_comp(self):
        """Make reuse-accept model."""
        self.reuse_accept_msg.assign_thread_id(thid="test_thid", pthid="test_pthid")
        data = self.reuse_accept_msg.serialize()
        data["@type"] = DIDCommPrefix.qualify_current(
            "out-of-band/1.0/handshake-reuse-accepted"
        )
        model_instance = HandshakeReuseAccept.deserialize(data)
        assert isinstance(model_instance, HandshakeReuseAccept)

    def test_pre_dump_x(self):
        """Exercise pre-dump serialization requirements."""
        with pytest.raises(BaseModelError):
            data = self.reuse_accept_msg.serialize()

    def test_assign_msg_type_version_to_model_inst(self):
        test_msg = HandshakeReuseAccept()
        assert "1.1" in test_msg._type
        assert "1.1" in HandshakeReuseAccept.Meta.message_type
        test_msg = HandshakeReuseAccept(version="1.2")
        assert "1.2" in test_msg._type
        assert "1.1" in HandshakeReuseAccept.Meta.message_type
