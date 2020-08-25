from asynctest import TestCase as AsyncTestCase

from ..did_posture import DIDPosture


class TestDIDPosture(AsyncTestCase):
    async def test_did_posture(self):
        assert DIDPosture.PUBLIC is DIDPosture.get("PUBLIC")
        assert DIDPosture.POSTED is DIDPosture.get("POSTED")
        assert DIDPosture.LOCAL is DIDPosture.get("LOCAL")
        assert DIDPosture.get("no-such-type") is None
        assert DIDPosture.get(None) is None

        assert DIDPosture.PUBLIC is DIDPosture.get({"public": True})
        assert DIDPosture.PUBLIC is DIDPosture.get({"public": True, "posted": True})
        assert DIDPosture.POSTED is DIDPosture.get({"public": False, "posted": True})
        assert DIDPosture.LOCAL is DIDPosture.get({"public": False, "posted": False})
        assert DIDPosture.LOCAL is DIDPosture.get({})
