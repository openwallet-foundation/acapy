"""
Enclose property names in double quotes in order to JSON serialize the contents in the API
"""
import logging

from rest_framework.decorators import detail_route

LOGGER = logging.getLogger(__name__)


@detail_route(url_path="related_to")
def list_related_to(self, request, pk=None):
    # We load most at runtime because ORM isn't loaded at setup time
    from django.shortcuts import get_object_or_404
    from api_v2.views.rest import CustomTopicSerializer
    from api_v2.models.Topic import Topic
    from api_v2.models.TopicRelationship import TopicRelationship
    from rest_framework.response import Response

    parent_queryset = Topic.objects.all()
    item = get_object_or_404(parent_queryset, pk=pk)
    queryset = item.get_active_related_to()
    serializer = CustomTopicSerializer(queryset, many=True)
    return Response(serializer.data)


@detail_route(url_path="related_from")
def list_related_from(self, request, pk=None):
    # Secondary imports do not incur a cost
    from django.shortcuts import get_object_or_404
    from api_v2.views.rest import CustomTopicSerializer
    from api_v2.models.Topic import Topic
    from api_v2.models.TopicRelationship import TopicRelationship
    from rest_framework.response import Response

    parent_queryset = Topic.objects.all()
    item = get_object_or_404(parent_queryset, pk=pk)
    queryset = item.get_active_related_from()
    serializer = CustomTopicSerializer(queryset, many=True)
    return Response(serializer.data)


@detail_route(url_path="related_to_relations")
def list_related_to_relations(self, request, pk=None):
    # We load most at runtime because ORM isn't loaded at setup time
    from api_v2.views.rest import CustomTopicRelationshipSerializer
    from api_v2.models.TopicRelationship import TopicRelationship
    from rest_framework.response import Response

    parent_queryset = TopicRelationship.objects.filter(topic=pk).all()
    serializer = CustomTopicRelationshipSerializer(
        parent_queryset, many=True, relationship_type="to"
    )
    return Response(serializer.data)


@detail_route(url_path="related_from_relations")
def list_related_from_relations(self, request, pk=None):
    # We load most at runtime because ORM isn't loaded at setup time
    from api_v2.views.rest import CustomTopicRelationshipSerializer
    from api_v2.models.TopicRelationship import TopicRelationship
    from rest_framework.response import Response

    parent_queryset = TopicRelationship.objects.filter(related_topic=pk).all()
    serializer = CustomTopicRelationshipSerializer(
        parent_queryset, many=True, relationship_type="from"
    )
    return Response(serializer.data)


TIME_ZONE = "America/Vancouver"

CUSTOMIZATIONS = {
    "serializers": {
        "Address": {
            "includeFields": [
                "id",
                "create_timestamp",
                "update_timestamp",
                "addressee",
                "civic_address",
                "city",
                "province",
                "postal_code",
                "country",
                "credential",
            ]
        },
        "Topic": {
            "includeFields": [
                "id",
                "create_timestamp",
                "update_timestamp",
                "source_id",
                "type",
                "related_to",
                "related_from",
            ]
        },
        "TopicRelationship": {
            "includeFields": ["id", "credential", "topic", "related_topic"]
        },
    },
    "views": {
        "TopicViewSet": {"includeMethods": [list_related_to, list_related_from]},
        "TopicRelationshipViewSet": {
            "includeMethods": [list_related_to_relations, list_related_from_relations]
        },
    },
}
