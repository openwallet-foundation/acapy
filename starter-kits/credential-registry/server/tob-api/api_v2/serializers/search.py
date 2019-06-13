# TODO: migrate most of these serializers to a UI specific serializer module

import logging
from collections import OrderedDict

from django.db.models.manager import Manager
from drf_haystack.serializers import HaystackFacetSerializer, HaystackSerializerMixin
from rest_framework.serializers import ListSerializer, SerializerMethodField
from rest_framework.utils.serializer_helpers import ReturnDict

from api_v2.models.Address import Address
from api_v2.models.Attribute import Attribute
from api_v2.models.CredentialType import CredentialType
from api_v2.models.Issuer import Issuer
from api_v2.models.Name import Name
from api_v2.search_indexes import CredentialIndex
from api_v2.serializers.rest import (
    AddressSerializer,
    AttributeSerializer,
    CredentialAddressSerializer,
    CredentialAttributeSerializer,
    CredentialNamedTopicSerializer,
    CredentialNameSerializer,
    CredentialSerializer,
    CredentialSetSerializer,
    CredentialTopicExtSerializer,
    CredentialTypeSerializer,
    IssuerSerializer,
    NameSerializer,
    TopicRelationshipSerializer,
    TopicSerializer,
)

logger = logging.getLogger(__name__)


class SearchResultsListSerializer(ListSerializer):
    @staticmethod
    def __camelCase(s):
        return s[:1].lower() + s[1:] if s else ""

    def __get_keyName(self, instance):
        search_index = instance.searchindex
        model = search_index.get_model()
        return self.__camelCase(model.__name__) + "s"

    @property
    def data(self):
        ret = super(ListSerializer, self).data
        return ReturnDict(ret, serializer=self)

    def to_representation(self, data):
        results = OrderedDict()
        iterable = data.all() if isinstance(data, Manager) else data
        for item in iterable:
            search_index_name = self.__get_keyName(item)
            results.setdefault(search_index_name, []).append(
                self.child.to_representation(item)
            )

        return results


class CustomIssuerSerializer(IssuerSerializer):
    class Meta(IssuerSerializer.Meta):
        fields = ("id", "did", "name", "abbreviation", "email", "url", "has_logo")
        exclude = None


class CustomAddressSerializer(AddressSerializer):
    last_updated = SerializerMethodField()
    inactive = SerializerMethodField()

    class Meta(AddressSerializer.Meta):
        fields = tuple(AddressSerializer.Meta.fields) + (
            "credential_id",
            "last_updated",
            "inactive",
        )

    def get_last_updated(self, obj):
        return obj.credential.effective_date

    def get_inactive(self, obj):
        return obj.credential.inactive


class CustomAttributeSerializer(AttributeSerializer):
    credential_type_id = SerializerMethodField()
    last_updated = SerializerMethodField()
    inactive = SerializerMethodField()

    class Meta(AttributeSerializer.Meta):
        fields = (
            "id",
            "credential_id",
            "credential_type_id",
            "last_updated",
            "inactive",
            "type",
            "format",
            "value",
        )

    def get_credential_type_id(self, obj):
        return obj.credential.credential_type_id

    def get_last_updated(self, obj):
        return obj.credential.effective_date

    def get_inactive(self, obj):
        return obj.credential.inactive


class CustomNameSerializer(NameSerializer):
    last_updated = SerializerMethodField()
    inactive = SerializerMethodField()
    issuer = SerializerMethodField()

    class Meta(NameSerializer.Meta):
        fields = (
            "id",
            "credential_id",
            "last_updated",
            "inactive",
            "text",
            "language",
            "issuer",
            "type",
        )

    def get_last_updated(self, obj):
        return obj.credential.effective_date

    def get_inactive(self, obj):
        return obj.credential.inactive

    def get_issuer(self, obj):
        serializer = CustomIssuerSerializer(
            instance=obj.credential.credential_type.issuer
        )
        return serializer.data


class CustomTopicSerializer(TopicSerializer):
    names = SerializerMethodField()
    addresses = SerializerMethodField()
    attributes = SerializerMethodField()

    class Meta(TopicSerializer.Meta):
        depth = 1
        fields = (
            "id",
            "create_timestamp",
            "source_id",
            "type",
            "names",
            "addresses",
            "attributes",
        )

    def get_names(self, obj):
        names = Name.objects.filter(
            credential__topic=obj, credential__latest=True, credential__revoked=False
        ).order_by("credential__inactive")
        serializer = CustomNameSerializer(instance=names, many=True)
        return serializer.data

    def get_addresses(self, obj):
        addresses = Address.objects.filter(
            credential__topic=obj, credential__latest=True, credential__revoked=False
        ).order_by("credential__inactive")
        serializer = CustomAddressSerializer(instance=addresses, many=True)
        return serializer.data

    def get_attributes(self, obj):
        attributes = Attribute.objects.filter(
            credential__topic=obj,
            credential__credential_type__description="Registration",
            credential__latest=True,
            credential__revoked=False,
        ).order_by("credential__inactive")
        serializer = CustomAttributeSerializer(instance=attributes, many=True)
        return serializer.data


class CustomTopicRelationshipSerializer(TopicRelationshipSerializer):
    attributes = CredentialAttributeSerializer(
        source="credential_attributes", many=True
    )
    topic = CustomTopicSerializer()
    related_topic = CustomTopicSerializer()
    relation_id = SerializerMethodField()
    topic_id = SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super(CustomTopicRelationshipSerializer, self).__init__(*args)
        self.relationship_type = kwargs.get("relationship_type", "to")

    class Meta(TopicRelationshipSerializer.Meta):
        depth = 1
        fields = (
            "topic_id",
            "relation_id",
            "credential",
            "topic",
            "related_topic",
            "attributes",
        )

    def get_relation_id(self, obj):
        return obj.id

    def get_topic_id(self, obj):
        if self.relationship_type == "to":
            return obj.topic.id
        else:
            return obj.related_topic.id


class CredentialSearchSerializer(HaystackSerializerMixin, CredentialSerializer):
    addresses = CredentialAddressSerializer(many=True)
    attributes = CredentialAttributeSerializer(many=True)
    credential_set = CredentialSetSerializer()
    credential_type = CredentialTypeSerializer()
    names = CredentialNameSerializer(many=True)
    topic = CredentialNamedTopicSerializer()
    related_topics = CredentialNamedTopicSerializer(many=True)

    class Meta(CredentialSerializer.Meta):
        fields = (
            "id",
            "create_timestamp",
            "update_timestamp",
            "effective_date",
            "inactive",
            "latest",
            "revoked",
            "revoked_date",
            "wallet_id",
            "credential_set",
            "credential_type",
            "addresses",
            "attributes",
            "names",
            "topic",
            "related_topics",
        )
        # used by ExactFilter
        exact_fields = (
            "credential_set_id",
            "credential_type_id",
            "issuer_id",
            "schema_name",
            "schema_version",
            "topic_id",
            "topic_type",
            "wallet_id",
        )
        # used by HaystackFilter
        search_fields = ("location", "effective_date", "revoked_date", "score")
        # used by StatusFilter
        status_fields = {"inactive": "false", "latest": "true", "revoked": "false"}


class CredentialAutocompleteSerializer(HaystackSerializerMixin, CredentialSerializer):
    names = CredentialNameSerializer(many=True)

    class Meta(CredentialSerializer.Meta):
        fields = ("id", "names", "inactive")
        status_fields = {"inactive": None, "latest": "true", "revoked": "false"}


class CredentialTopicSearchSerializer(CredentialSearchSerializer):
    """
    Return credentials with addresses and attributes removed, but
    added for the related topic instead
    """

    topic = CredentialTopicExtSerializer()

    class Meta(CredentialSearchSerializer.Meta):
        fields = (
            "id",
            "create_timestamp",
            "update_timestamp",
            "effective_date",
            "inactive",
            "latest",
            "revoked",
            "revoked_date",
            "wallet_id",
            "credential_set",
            "credential_type",
            "attributes",
            "names",
            "topic",
            "related_topics",
        )


class CredentialFacetSerializer(HaystackFacetSerializer):
    serialize_objects = True

    class Meta:
        index_classes = [CredentialIndex]
        fields = [
            "category",
            "credential_type_id",
            "issuer_id",
            # "inactive",
            # "topic_type",
        ]
        field_options = {
            "category": {},
            "credential_type_id": {},
            "issuer_id": {},
            # "inactive": {},
            # "topic_type": {},
            # date faceting isn't working, needs to use Solr range faceting
            # https://github.com/django-haystack/django-haystack/issues/1572
            #             "effective_date": {
            #                 "start_date": datetime.now() - timedelta(days=50000),
            #                 "end_date": datetime.now(),
            #                 "gap_by": "month",
            #                 "gap_amount": 3
            #             },
        }

    def get_fields(self):
        field_mapping = OrderedDict()
        field_mapping["facets"] = SerializerMethodField()
        if self.serialize_objects is True:
            field_mapping["objects"] = SerializerMethodField()
        return field_mapping

    def get_facets(self, instance):
        result = OrderedDict()
        for facet_type, facet_data in instance.items():
            serial_data = {}
            for field, facets in facet_data.items():
                serial_data[field] = self.format_facets(field, facets)
            result[facet_type] = serial_data
        return result

    def format_facets(self, field_name, facets):
        result = []
        for facet in facets:
            row = {"value": facet[0], "count": facet[1]}
            # naive method - can be optimized
            if field_name == "issuer_id":
                row["text"] = Issuer.objects.get(pk=row["value"]).name
            elif field_name == "credential_type_id":
                row["text"] = CredentialType.objects.get(pk=row["value"]).description
            result.append(row)
        return result

    def get_objects(self, instance):
        """
        Overriding default behaviour to use more standard pagination info
        """
        view = self.context["view"]
        queryset = self.context["objects"]

        page = view.paginate_queryset(queryset)
        if page is not None:
            serializer = view.get_facet_objects_serializer(page, many=True)
            response = view.paginator.get_paginated_response(serializer.data)
            return response.data  # unwrap value

        return super(CredentialFacetSerializer, self).get_objects()
