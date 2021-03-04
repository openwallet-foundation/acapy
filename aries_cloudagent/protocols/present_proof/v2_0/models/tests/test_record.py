from unittest import TestCase as UnitTestCase

from ......messaging.models.base_record import BaseExchangeRecord, BaseExchangeSchema

from ..pres_exchange import V20PresExRecord


class BasexRecordImpl(BaseExchangeRecord):
    class Meta:
        schema_class = "BasexRecordImplSchema"

    RECORD_TYPE = "record"


class BasexRecordImplSchema(BaseExchangeSchema):
    class Meta:
        model_class = BasexRecordImpl


class TestRecord(UnitTestCase):
    def test_record(self):
        record = V20PresExRecord(
            pres_ex_id="pxid",
            thread_id="thid",
            connection_id="conn_id",
            initiator="init",
            role="role",
            state="state",
            pres_proposal={"pres": "prop"},
            pres_request={"pres": "req"},
            pres={"pres": "pres"},
            verified="false",
            auto_present=True,
            error_msg="error",
        )

        assert record.pres_ex_id == "pxid"

        assert record.record_value == {
            "connection_id": "conn_id",
            "initiator": "init",
            "role": "role",
            "state": "state",
            "pres_proposal": {"pres": "prop"},
            "pres_request": {"pres": "req"},
            "pres": {"pres": "pres"},
            "verified": "false",
            "auto_present": True,
            "error_msg": "error",
            "trace": False,
        }

        bx_record = BasexRecordImpl()
        assert record != bx_record
