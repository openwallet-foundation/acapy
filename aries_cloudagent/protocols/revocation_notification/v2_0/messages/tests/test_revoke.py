"""Test Revoke Message."""

from ..revoke import Revoke


def test_instantiate():
    msg = Revoke(
        revocation_format="indy-anoncreds",
        credential_id="test-id",
        comment="test",
    )
    assert msg.revocation_format == "indy-anoncreds"
    assert msg.credential_id == "test-id"
    assert msg.comment == "test"
