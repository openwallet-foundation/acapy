import re

from datetime import datetime, timezone
from unittest import mock, TestCase

from ..util import (
    canon,
    datetime_now,
    datetime_to_str,
    encode,
    epoch_to_str,
    I32_BOUND,
    str_to_datetime,
    str_to_epoch,
    time_now,
)


class TestUtil(TestCase):
    def test_parse(self):
        now = datetime_now()
        assert isinstance(now, datetime)
        tests = {
            "2019-05-17 20:51:19.519437Z": datetime(
                2019, 5, 17, 20, 51, 19, 519437, tzinfo=timezone.utc
            ),
            "2019-05-17 20:51:19.519437001Z": datetime(
                2019, 5, 17, 20, 51, 19, 519437, tzinfo=timezone.utc
            ),
            "2019-05-17 20:51:19Z": datetime(
                2019, 5, 17, 20, 51, 19, 0, tzinfo=timezone.utc
            ),
            "2019-05-17 20:51Z": datetime(
                2019, 5, 17, 20, 51, 0, 0, tzinfo=timezone.utc
            ),
            "2019-11-15T22:37:14": datetime(
                2019, 11, 15, 22, 37, 14, tzinfo=timezone.utc
            ),
            "2019-05-17 20:51:19.519437+01:00": datetime(
                2019, 5, 17, 19, 51, 19, 519437, tzinfo=timezone.utc
            ),
            "2019-05-17T20:51:19.519437+0000": datetime(
                2019, 5, 17, 20, 51, 19, 519437, tzinfo=timezone.utc
            ),
            now: now,
        }
        for date_str, expected in tests.items():
            assert str_to_datetime(date_str) == expected
        with self.assertRaises(ValueError):
            str_to_datetime("BAD_DATE")

    def test_format(self):
        now = time_now()
        assert isinstance(now, str)
        tests = {
            datetime(
                2019, 5, 17, 20, 51, 19, 519437, tzinfo=timezone.utc
            ): "2019-05-17T20:51:19.519437Z",
            now: now,
        }
        for datetime_val, expected in tests.items():
            assert datetime_to_str(datetime_val) == expected

    def test_epoch(self):
        dt_now = datetime_now()
        epoch_now = int(dt_now.timestamp())

        assert epoch_now == str_to_epoch(dt_now) and isinstance(epoch_now, int)
        assert epoch_to_str(epoch_now) == datetime_to_str(dt_now.replace(microsecond=0))

    def test_canon(self):
        assert canon("a B c") == "abc"
        assert canon(None) is None
        assert canon("") == ""
        assert canon("canon") == "canon"

    def test_encode(self):
        values = {
            "address2": {
                "raw": "101 Wilson Lane",
                "encoded": "68086943237164982734333428280784300550565381723532936263016368251445461241953",
            },
            "zip": {"raw": "87121", "encoded": "87121"},
            "city": {
                "raw": "SLC",
                "encoded": "101327353979588246869873249766058188995681113722618593621043638294296500696424",
            },
            "address1": {
                "raw": "101 Tela Lane",
                "encoded": "63690509275174663089934667471948380740244018358024875547775652380902762701972",
            },
            "state": {
                "raw": "UT",
                "encoded": "93856629670657830351991220989031130499313559332549427637940645777813964461231",
            },
            "Empty": {
                "raw": "",
                "encoded": "102987336249554097029535212322581322789799900648198034993379397001115665086549",
            },
            "Null": {
                "raw": None,
                "encoded": "99769404535520360775991420569103450442789945655240760487761322098828903685777",
            },
            "str None": {
                "raw": "None",
                "encoded": "99769404535520360775991420569103450442789945655240760487761322098828903685777",
            },
            "bool True": {"raw": True, "encoded": "1"},
            "bool False": {
                "raw": False,
                "encoded": "0",
            },
            "str True": {
                "raw": "True",
                "encoded": "27471875274925838976481193902417661171675582237244292940724984695988062543640",
            },
            "str False": {
                "raw": "False",
                "encoded": "43710460381310391454089928988014746602980337898724813422905404670995938820350",
            },
            "max i32": {"raw": 2147483647, "encoded": "2147483647"},
            "max i32 + 1": {
                "raw": 2147483648,
                "encoded": "26221484005389514539852548961319751347124425277437769688639924217837557266135",
            },
            "min i32": {"raw": -2147483648, "encoded": "-2147483648"},
            "min i32 - 1": {
                "raw": -2147483649,
                "encoded": "68956915425095939579909400566452872085353864667122112803508671228696852865689",
            },
            "float 0.0": {
                "raw": 0.0,
                "encoded": "62838607218564353630028473473939957328943626306458686867332534889076311281879",
            },
            "str 0.0": {
                "raw": "0.0",
                "encoded": "62838607218564353630028473473939957328943626306458686867332534889076311281879",
            },
            "chr 0": {
                "raw": chr(0),
                "encoded": "49846369543417741186729467304575255505141344055555831574636310663216789168157",
            },
            "chr 1": {
                "raw": chr(1),
                "encoded": "34356466678672179216206944866734405838331831190171667647615530531663699592602",
            },
            "chr 2": {
                "raw": chr(2),
                "encoded": "99398763056634537812744552006896172984671876672520535998211840060697129507206",
            },
        }

        for tag, value in values.items():
            print("{}: {} -> {}".format(tag, value["raw"], encode(value["raw"])))
            assert encode(value["raw"]) == value["encoded"]
