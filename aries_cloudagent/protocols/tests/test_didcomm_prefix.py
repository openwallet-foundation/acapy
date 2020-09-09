from os import environ

from asynctest import TestCase as AsyncTestCase

from ..didcomm_prefix import DIDCommPrefix


class TestDIDCommPrefix(AsyncTestCase):
    async def test_didcomm_prefix(self):
        DIDCommPrefix.set({})
        assert environ.get("DIDCOMM_PREFIX") == DIDCommPrefix.OLD.value

        DIDCommPrefix.set({"emit_new_didcomm_prefix": True})
        assert environ.get("DIDCOMM_PREFIX") == DIDCommPrefix.NEW.value
        assert DIDCommPrefix.qualify_current("hello") == (
            f"{DIDCommPrefix.NEW.value}/hello"
        )

        DIDCommPrefix.set({"emit_new_didcomm_prefix": False})
        assert environ.get("DIDCOMM_PREFIX") == DIDCommPrefix.OLD.value
        assert DIDCommPrefix.qualify_current("hello") == (
            f"{DIDCommPrefix.OLD.value}/hello"
        )

        old_q_hello = DIDCommPrefix.OLD.qualify("hello")
        new_q_hello = DIDCommPrefix.NEW.qualify("hello")
        assert old_q_hello == f"{DIDCommPrefix.OLD.value}/hello"
        assert new_q_hello == f"{DIDCommPrefix.NEW.value}/hello"

        assert DIDCommPrefix.unqualify(old_q_hello) == "hello"
        assert DIDCommPrefix.unqualify(new_q_hello) == "hello"
        assert DIDCommPrefix.unqualify("already unqualified") == "already unqualified"
        assert DIDCommPrefix.unqualify(None) is None
