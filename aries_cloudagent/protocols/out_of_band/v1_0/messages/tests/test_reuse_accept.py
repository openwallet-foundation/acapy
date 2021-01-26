import pytest
from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase
from ......messaging.models.base import BaseModelError
from ..reuse_accept import HandshakeReuseAccept, HandshakeReuseAcceptSchema

class TestReuseAcceptMessage(TestCase):
    """Test request schema."""

    reuse_accept_msg = HandshakeReuseAccept()
    reuse_accept_msg.assign_thread_id(thid="test_thid", pthid="test_pthid")

    def test_init(self):
        """Test initialization of Handshake Reuse message."""
        assert isinstance(self.reuse_accept_msg, HandshakeReuseAccept)
        assert isinstance(self.reuse_accept_msg._id, str)
        assert len(self.reuse_accept_msg._id) > 4
        assert self.reuse_accept_msg._thread.thid == "test_thid"
        assert self.reuse_accept_msg._thread.pthid == "test_pthid"

    def test_make_model(self):
        data = self.reuse_accept_msg.serialize()
        model_instance = HandshakeReuseAccept.deserialize(data)
        assert isinstance(model_instance, HandshakeReuseAccept)

