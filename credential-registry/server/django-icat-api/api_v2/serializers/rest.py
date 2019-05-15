from rest_framework.serializers import BooleanField, ModelSerializer, SerializerMethodField
from api_v2.models.Issuer import Issuer
from api_v2.models.Schema import Schema
from api_v2.models.CredentialType import CredentialType
from api_v2.models.Topic import Topic
from api_v2.models.Credential import Credential
from api_v2.models.CredentialSet import CredentialSet
from api_v2.models.Address import Address
from api_v2.models.Claim import Claim
from api_v2.models.Name import Name
from api_v2.models.Attribute import Attribute
from api_v2 import utils


class IssuerSerializer(ModelSerializer):
    has_logo = BooleanField(source="get_has_logo", read_only=True)

    class Meta:
        model = Issuer
        exclude = (
            "logo_b64",
        )


class SchemaSerializer(ModelSerializer):
    class Meta:
        model = Schema
        fields = "__all__"


class CredentialSetSerializer(ModelSerializer):
    class Meta:
        model = CredentialSet
        fields = (
            "id", "create_timestamp", "update_timestamp",
            "latest_credential_id", "topic_id",
            "first_effective_date", "last_effective_date",
        )


class CredentialTypeSerializer(ModelSerializer):
    issuer = IssuerSerializer()
    has_logo = BooleanField(source="get_has_logo", read_only=True)

    class Meta:
        model = CredentialType
        depth = 1
        exclude = (
            "category_labels",
            "claim_descriptions",
            "claim_labels",
            "logo_b64",
            "processor_config",
            "visible_fields",
        )


class TopicSerializer(ModelSerializer):
    class Meta:
        model = Topic
        fields = list(utils.fetch_custom_settings('serializers', 'Topic', 'includeFields'))


class AddressSerializer(ModelSerializer):
    class Meta:
        model = Address
        fields = list(utils.fetch_custom_settings('serializers', 'Address', 'includeFields'))


class ClaimSerializer(ModelSerializer):
    class Meta:
        model = Claim
        fields = "__all__"


class NameSerializer(ModelSerializer):
    class Meta:
        model = Name
        fields = "__all__"


class AttributeSerializer(ModelSerializer):
    class Meta:
        model = Attribute
        fields = "__all__"


class CredentialSerializer(ModelSerializer):
    class Meta:
        model = Credential
        fields = "__all__"

class CredentialAddressSerializer(AddressSerializer):
    class Meta(AddressSerializer.Meta):
        fields = tuple(
            {*AddressSerializer.Meta.fields, "credential_id"} - {"credential"}
        )

class CredentialAttributeSerializer(AttributeSerializer):
    class Meta(AttributeSerializer.Meta):
        fields = ("id", "type", "format", "value", "credential_id")

class CredentialNameSerializer(NameSerializer):
    class Meta(NameSerializer.Meta):
        fields = ("id", "text", "language", "credential_id")

class CredentialTopicSerializer(TopicSerializer):
    class Meta(TopicSerializer.Meta):
        fields = (
            "id", "create_timestamp", "update_timestamp",
            "source_id", "type",
        )

class CredentialNamedTopicSerializer(CredentialTopicSerializer):
    names = CredentialNameSerializer(source='get_active_names', many=True)

    class Meta(CredentialTopicSerializer.Meta):
        fields = CredentialTopicSerializer.Meta.fields + ("names",)

class TopicAttributeSerializer(AttributeSerializer):
    credential_type_id = SerializerMethodField()
    class Meta(CredentialAttributeSerializer.Meta):
        fields = ("id", "type", "format", "value", "credential_id", "credential_type_id")

    def get_credential_type_id(self, obj):
        return obj.credential.credential_type_id

class CredentialTopicExtSerializer(CredentialNamedTopicSerializer):
    addresses = CredentialAddressSerializer(source='get_active_addresses', many=True)
    attributes = TopicAttributeSerializer(source='get_active_attributes', many=True)

    class Meta(CredentialNamedTopicSerializer.Meta):
        fields = CredentialNamedTopicSerializer.Meta.fields + ("addresses", "attributes")


class CredentialExtSerializer(CredentialSerializer):
    addresses = CredentialAddressSerializer(many=True)
    attributes = CredentialAttributeSerializer(many=True)
    credential_type = CredentialTypeSerializer()
    names = CredentialNameSerializer(many=True)
    topic = CredentialTopicExtSerializer()
    related_topics = CredentialNamedTopicSerializer(many=True)

    class Meta(CredentialSerializer.Meta):
        depth = 1
        fields = (
            "id",
            "create_timestamp",
            "effective_date",
            "inactive",
            "latest",
            "revoked",
            "revoked_date",
            "wallet_id",
            "credential_type",
            "addresses",
            "attributes",
            "names",
            "topic",
            "related_topics",
        )


class ExpandedCredentialSetSerializer(CredentialSetSerializer):
    credentials = CredentialExtSerializer(many=True)

    class Meta(CredentialSetSerializer.Meta):
        fields = CredentialSetSerializer.Meta.fields + ("credentials",)


class ExpandedCredentialSerializer(CredentialExtSerializer):
    credential_set = ExpandedCredentialSetSerializer()

    class Meta(CredentialExtSerializer.Meta):
        fields = CredentialExtSerializer.Meta.fields + ("credential_set",)
