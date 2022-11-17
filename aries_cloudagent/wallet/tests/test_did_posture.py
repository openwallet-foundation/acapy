from asynctest import TestCase as AsyncTestCase

from ..did_posture import DIDPosture


class TestDIDPosture(AsyncTestCase):
    async def test_did_posture(self):
        assert DIDPosture.PUBLIC is DIDPosture.get("PUBLIC")
        assert DIDPosture.POSTED is DIDPosture.get("POSTED")
        assert DIDPosture.WALLET_ONLY is DIDPosture.get("WALLET_ONLY")
        assert DIDPosture.get("no-such-type") is None
        assert DIDPosture.get(None) is None

        assert DIDPosture.PUBLIC is DIDPosture.get({"public": True})
        assert DIDPosture.PUBLIC is DIDPosture.get({"public": True, "posted": True})
        assert DIDPosture.POSTED is DIDPosture.get({"public": False, "posted": True})
        assert DIDPosture.WALLET_ONLY is DIDPosture.get(
            {"public": False, "posted": False}
        )
        assert DIDPosture.WALLET_ONLY is DIDPosture.get({})

        postures = [posture for posture in DIDPosture]
        postures.sort(key=lambda p: p.ordinal)
        assert postures == [
            DIDPosture.PUBLIC,
            DIDPosture.POSTED,
            DIDPosture.WALLET_ONLY,
        ]
