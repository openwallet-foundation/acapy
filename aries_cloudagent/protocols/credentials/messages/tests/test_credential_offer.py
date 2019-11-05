# from ..credential_offer import CredentialOffer
# from ....message_types import MessageTypes
#
# from unittest import mock, TestCase
#
#
# class TestCredentialOffer(TestCase):
#     """Credential offer tests"""
#
#     offer_json = "offer_json"
#
#     def test_init(self):
#         """Test initializer"""
#         credential_offer = CredentialOffer(offer_json=self.offer_json)
#         assert credential_offer.offer_json == self.offer_json
#
#     def test_type(self):
#         """Test type"""
#         credential_offer = CredentialOffer(offer_json=self.offer_json)
#
#         assert credential_offer._type == MessageTypes.CREDENTIAL_OFFER.value
#
#     @mock.patch(
#         "aries_cloudagent.messaging.credentials.messages."
#         + "credential_offer.CredentialOfferSchema.load"
#     )
#     def test_deserialize(self, mock_credential_offer_schema_load):
#         """
#         Test deserialize
#         """
#         obj = {"obj": "obj"}
#
#         credential_offer = CredentialOffer.deserialize(obj)
#         mock_credential_offer_schema_load.assert_called_once_with(obj)
#
#         assert credential_offer is mock_credential_offer_schema_load.return_value
#
#     @mock.patch(
#         "aries_cloudagent.messaging.credentials.messages."
#         + "credential_offer.CredentialOfferSchema.dump"
#     )
#     def test_serialize(self, mock_credential_offer_schema_dump):
#         """
#         Test serialization.
#         """
#         credential_offer = CredentialOffer(offer_json=self.offer_json)
#
#         credential_offer_dict = credential_offer.serialize()
#         mock_credential_offer_schema_dump.assert_called_once_with(credential_offer)
#
#         assert credential_offer_dict is mock_credential_offer_schema_dump.return_value
#
#
# class TestCredentialOfferSchema(TestCase):
#     """Test credential cred offer schema"""
#
#     credential_offer = CredentialOffer(offer_json="offer_json")
#
#     def test_make_model(self):
#         """Test making model."""
#         data = self.credential_offer.serialize()
#         model_instance = CredentialOffer.deserialize(data)
#         assert isinstance(model_instance, CredentialOffer)
