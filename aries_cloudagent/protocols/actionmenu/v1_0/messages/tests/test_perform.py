from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import PERFORM, PROTOCOL_PACKAGE

from ..perform import Perform, PerformSchema


class TestPerform(TestCase):
    test_name = "option_name"
    test_params = {"a": "aaa"}

    def setUp(self):
        self.perform = Perform(name=self.test_name, params=self.test_params)

    def test_init(self):
        """Test initialization."""
        assert self.perform.name == self.test_name
        assert self.perform.params == self.test_params

    def test_type(self):
        """Test type."""
        assert self.perform._type == DIDCommPrefix.qualify_current(PERFORM)

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.perform.PerformSchema.load")
    def test_deserialize(self, mock_perform_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        request = Perform.deserialize(obj)
        mock_perform_schema_load.assert_called_once_with(obj)

        assert request is mock_perform_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.perform.PerformSchema.dump")
    def test_serialize(self, mock_perform_schema_dump):
        """
        Test serialization.
        """
        request_dict = self.perform.serialize()
        mock_perform_schema_dump.assert_called_once_with(self.perform)
        assert request_dict is mock_perform_schema_dump.return_value

    def test_make_model(self):
        data = self.perform.serialize()
        model_instance = Perform.deserialize(data)
        assert type(model_instance) is type(self.perform)
