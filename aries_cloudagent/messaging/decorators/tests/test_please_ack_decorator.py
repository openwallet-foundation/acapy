import json
import pytest
import uuid

from copy import deepcopy
from datetime import datetime, timezone
from time import time
from unittest import TestCase

from ..please_ack_decorator import PleaseAckDecorator


MESSAGE_ID = "abc123"
ON = ("RECEIPT", "OUTCOME")


class TestPleaseAckDecorator(TestCase):
    def test_init_serde(self):
        decorator = PleaseAckDecorator()
        assert type(decorator) == PleaseAckDecorator
        assert decorator.message_id is None
        assert decorator.on is None
        dumped = decorator.serialize()
        assert dumped == {}
        loaded = PleaseAckDecorator.deserialize(dumped)
        assert type(loaded) == PleaseAckDecorator
        assert loaded.message_id is None
        assert loaded.on is None

        decorator = PleaseAckDecorator(message_id=MESSAGE_ID)
        assert type(decorator) == PleaseAckDecorator
        assert decorator.message_id == MESSAGE_ID
        assert decorator.on is None
        dumped = decorator.serialize()
        assert dumped == {"message_id": MESSAGE_ID}
        loaded = PleaseAckDecorator.deserialize(dumped)
        assert type(loaded) == PleaseAckDecorator
        assert loaded.message_id == MESSAGE_ID
        assert loaded.on is None

        decorator = PleaseAckDecorator(on=ON)
        assert type(decorator) == PleaseAckDecorator
        assert decorator.message_id is None
        assert decorator.on == list(ON)
        dumped = decorator.serialize()
        assert dumped == {
            "on": list(ON),
        }
        loaded = PleaseAckDecorator.deserialize(dumped)
        assert type(loaded) == PleaseAckDecorator
        assert loaded.message_id is None
        assert loaded.on == list(ON)

        decorator = PleaseAckDecorator(message_id=MESSAGE_ID, on=ON)
        assert type(decorator) == PleaseAckDecorator
        assert decorator.message_id == MESSAGE_ID
        assert decorator.on == list(ON)
        dumped = decorator.serialize()
        assert dumped == {
            "message_id": MESSAGE_ID,
            "on": list(ON),
        }
        loaded = PleaseAckDecorator.deserialize(dumped)
        assert type(loaded) == PleaseAckDecorator
        assert loaded.message_id == MESSAGE_ID
        assert loaded.on == list(ON)
