from ..credential_offer import CredentialOffer, CredentialOfferSchema
from ...message_types import MessageTypes

from unittest import mock, TestCase


class TestCredentialOffer(TestCase):
    offer_json = "offer_json"

    def test_init(self):
        credential_offer = CredentialOffer(self.offer_json)
        assert credential_offer.offer_json == self.offer_json

    def test_type(self):
        credential_offer = CredentialOffer(self.offer_json)

        assert credential_offer._type == MessageTypes.CREDENTIAL_OFFER.value

    @mock.patch(
        "indy_catalyst_agent.messages.credentials.credential_offer.CredentialOfferSchema.load"
    )
    def test_deserialize(self, mock_credential_offer_schema_load):
        obj = {"obj": "obj"}

        credential_offer = CredentialOffer.deserialize(obj)
        mock_credential_offer_schema_load.assert_called_once_with(obj)

        assert credential_offer is mock_credential_offer_schema_load.return_value

    @mock.patch(
        "indy_catalyst_agent.messages.credentials.credential_offer.CredentialOfferSchema.dump"
    )
    def test_serialize(self, mock_credential_offer_schema_dump):
        credential_offer = CredentialOffer(self.offer_json)

        credential_offer_dict = credential_offer.serialize()
        mock_credential_offer_schema_dump.assert_called_once_with(credential_offer)

        assert credential_offer_dict is mock_credential_offer_schema_dump.return_value


class TestCredentialOfferSchema(TestCase):
    credential_offer = CredentialOffer("offer_json")

    def test_make_model(self):
        schema = CredentialOfferSchema()

        data = self.credential_offer.serialize()
        data["_type"] = data["@type"]
        del data["@type"]

        model_instance = schema.make_model(data)
        assert type(model_instance) is type(self.credential_offer)

