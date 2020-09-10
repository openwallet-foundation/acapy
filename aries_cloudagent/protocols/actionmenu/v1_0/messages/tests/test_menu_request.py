from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import MENU_REQUEST, PROTOCOL_PACKAGE

from ..menu_request import MenuRequest, MenuRequestSchema


class TestMenuRequest(TestCase):
    def setUp(self):
        self.menu_request = MenuRequest()

    def test_init(self):
        """Test initialization."""
        pass

    def test_type(self):
        """Test type."""
        assert self.menu_request._type == DIDCommPrefix.qualify_current(MENU_REQUEST)

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.menu_request.MenuRequestSchema.load")
    def test_deserialize(self, mock_menu_request_schema_load):
        """
        Test deserialization.
        """
        obj = {"obj": "obj"}

        request = MenuRequest.deserialize(obj)
        mock_menu_request_schema_load.assert_called_once_with(obj)

        assert request is mock_menu_request_schema_load.return_value

    @mock.patch(f"{PROTOCOL_PACKAGE}.messages.menu_request.MenuRequestSchema.dump")
    def test_serialize(self, mock_menu_request_schema_dump):
        """
        Test serialization.
        """
        request_dict = self.menu_request.serialize()
        mock_menu_request_schema_dump.assert_called_once_with(self.menu_request)
        assert request_dict is mock_menu_request_schema_dump.return_value

    def test_make_model(self):
        data = self.menu_request.serialize()
        model_instance = MenuRequest.deserialize(data)
        assert type(model_instance) is type(self.menu_request)
