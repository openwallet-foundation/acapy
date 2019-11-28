from unittest import TestCase as UnitTestCase

from ..presentation_exchange import V10PresentationExchange


class TestRecord(UnitTestCase):
    def test_record(self):
        record = V10PresentationExchange(
            presentation_exchange_id="pxid",
            connection_id="connid",
            thread_id="thid",
            initiator="init",
            role="role",
            state="state",
            presentation_proposal_dict={"prop": "dict"},
            presentation_request={"pres": "req"},
            presentation={"pres": "indy"},
            verified=False,
            auto_present=True,
            error_msg="error",
        )

        assert record.presentation_exchange_id == "pxid"

        assert record.record_value == {
            "connection_id": "connid",
            "initiator": "init",
            "presentation_proposal_dict": {"prop": "dict"},
            "presentation_request": {"pres": "req"},
            "presentation": {"pres": "indy"},
            "role": "role",
            "state": "state",
            "auto_present": True,
            "error_msg": "error",
            "verified": False,
        }
