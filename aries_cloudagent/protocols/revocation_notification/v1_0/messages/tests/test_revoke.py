"""Test Revoke Message."""

from ..revoke import Revoke


def test_instantiate():
    msg = Revoke(thread_id="test", comment="test")
    assert msg.thread_id == "test"
    assert msg.comment == "test"
