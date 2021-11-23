from unittest import mock, TestCase

from marshmallow.exceptions import ValidationError

from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import DISCLOSURES, PROTOCOL_PACKAGE

from ..disclosures import Disclosures


class TestDisclosures(TestCase):
    test_disclosure_a = [
        {
            "id": DIDCommPrefix.qualify_current("basicmessage/1.0/message"),
            "feature-type": "protocol",
            "roles": [],
        }
    ]
    test_disclosure_b = [
        {
            "id": DIDCommPrefix.qualify_current("basicmessage/1.0/message"),
            "feature-type": "protocol",
            "roles": [],
        },
        {"feature-type": "goal-code", "id": "aries.sell.goods.consumer"},
    ]

    def test_init(self):
        disclosures = Disclosures(disclosures=self.test_disclosure_a)
        assert disclosures.disclosures == self.test_disclosure_a

        disclosures = Disclosures(disclosures=self.test_disclosure_b)
        assert disclosures.disclosures == self.test_disclosure_b

    def test_type(self):
        disclosures = Disclosures(disclosures=self.test_disclosure_a)
        assert disclosures._type == DIDCommPrefix.qualify_current(DISCLOSURES)

        disclosures = Disclosures(disclosures=self.test_disclosure_b)
        assert disclosures._type == DIDCommPrefix.qualify_current(DISCLOSURES)

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.disclosures.DisclosuresSchema.load")
    def test_deserialize(self, mock_disclosures_schema_load):
        obj = {"obj": "obj"}

        disclosures = Disclosures.deserialize(obj)
        mock_disclosures_schema_load.assert_called_once_with(obj)

        assert disclosures is mock_disclosures_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.disclosures.DisclosuresSchema.dump")
    def test_serialize(self, mock_disclosures_schema_dump):
        disclosures = Disclosures(disclosures=self.test_disclosure_b)

        disclosures_dict = disclosures.serialize()
        mock_disclosures_schema_dump.assert_called_once_with(disclosures)

        assert disclosures_dict is mock_disclosures_schema_dump.return_value


class TestDiscloseSchema(TestCase):
    test_disclosures = [
        {
            "id": DIDCommPrefix.qualify_current("basicmessage/1.0/message"),
            "feature-type": "protocol",
            "roles": [],
        },
        {"feature-type": "goal-code", "id": "aries.sell.goods.consumer"},
    ]
    disclosures = Disclosures(disclosures=test_disclosures)
    test_invalid_disclosures = [
        {
            "id": DIDCommPrefix.qualify_current("basicmessage/1.0/message"),
            "feature-type": "protocol",
            "roles": [],
        },
        {"test": "test"},
    ]
    invalid_disclosures = Disclosures(disclosures=test_invalid_disclosures)

    def test_make_model(self):
        data = self.disclosures.serialize()
        model_instance = Disclosures.deserialize(data)
        assert isinstance(model_instance, Disclosures)

        with self.assertRaises(BaseModelError):
            data = self.invalid_disclosures.serialize()
            model_instance = Disclosures.deserialize(data)
