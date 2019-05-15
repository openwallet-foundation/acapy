import logging

from django.http import Http404
from rest_framework import permissions
from rest_framework.decorators import list_route
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_haystack.filters import (
    HaystackOrderingFilter,
)
from drf_haystack.mixins import FacetMixin
from drf_haystack.viewsets import HaystackViewSet
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from haystack.query import RelatedSearchQuerySet

from api_v2.models.Credential import Credential
from api_v2.search.filters import (
    AutocompleteFilter,
    CategoryFilter,
    CredNameFilter,
    CustomFacetFilter,
    ExactFilter,
    StatusFilter,
)
from api_v2.serializers.search import (
    CredentialAutocompleteSerializer,
    CredentialSearchSerializer,
    CredentialFacetSerializer,
    CredentialTopicSearchSerializer,
)
from tob_api.pagination import ResultLimitPagination
from django.conf import settings

LOGGER = logging.getLogger(__name__)


class NameAutocompleteView(HaystackViewSet):
    """
    Return autocomplete results for a query string
    """
    permission_classes = (permissions.AllowAny,)
    pagination_class = ResultLimitPagination

    _swagger_params = [
        openapi.Parameter(
            "q",
            openapi.IN_QUERY,
            description="Query string",
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            "inactive",
            openapi.IN_QUERY,
            description="Show inactive credentials",
            type=openapi.TYPE_STRING,
            enum=["any", "false", "true"],
            default="any",
        ),
        openapi.Parameter(
            "latest",
            openapi.IN_QUERY,
            description="Show only latest credentials",
            type=openapi.TYPE_STRING,
            enum=["any", "false", "true"],
            default="true",
        ),
        openapi.Parameter(
            "revoked",
            openapi.IN_QUERY,
            description="Show revoked credentials",
            type=openapi.TYPE_STRING,
            enum=["any", "false", "true"],
            default="false",
        ),
        openapi.Parameter(
            "category",
            openapi.IN_QUERY,
            description="Filter by credential category. The category name and value should be joined by '::'",
            type=openapi.TYPE_STRING,
        ),
        #openapi.Parameter(
        #    "hl", openapi.IN_QUERY, description="Highlight search term", type=openapi.TYPE_BOOLEAN
        #),
    ]
    @swagger_auto_schema(manual_parameters=_swagger_params)
    def list(self, *args, **kwargs):
        print(' >>> calling autocomplete')
        ret = super(NameAutocompleteView, self).list(*args, **kwargs)
        print(' >>> autocomplete returns', ret)
        return ret
    retrieve = None

    index_models = [Credential]
    load_all = True
    serializer_class = CredentialAutocompleteSerializer
    # enable normal filtering
    filter_backends = [
        AutocompleteFilter,
        CategoryFilter,
        StatusFilter,
        HaystackOrderingFilter,
    ]
    ordering_fields = ('effective_date', 'revoked_date', 'score')
    ordering = ('-score')


class CredentialSearchView(HaystackViewSet, FacetMixin):
    """
    Provide credential search via Solr with both faceted (/facets) and unfaceted results
    """

    permission_classes = (permissions.AllowAny,)

    _swagger_params = [
        openapi.Parameter(
            "name",
            openapi.IN_QUERY,
            description="Filter credentials by related name or topic source ID",
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            "inactive",
            openapi.IN_QUERY,
            description="Show inactive credentials",
            type=openapi.TYPE_STRING,
            enum=["any", "false", "true"],
            default="false",
        ),
        openapi.Parameter(
            "latest",
            openapi.IN_QUERY,
            description="Show only latest credentials",
            type=openapi.TYPE_STRING,
            enum=["any", "false", "true"],
            default="true",
        ),
        openapi.Parameter(
            "revoked",
            openapi.IN_QUERY,
            description="Show revoked credentials",
            type=openapi.TYPE_STRING,
            enum=["any", "false", "true"],
            default="false",
        ),
        openapi.Parameter(
            "category",
            openapi.IN_QUERY,
            description="Filter by credential category. The category name and value should be joined by '::'",
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            "credential_type_id",
            openapi.IN_QUERY,
            description="Filter by Credential Type ID",
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            "issuer_id",
            openapi.IN_QUERY,
            description="Filter by Issuer ID",
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            "topic_id",
            openapi.IN_QUERY,
            description="Filter by Topic ID",
            type=openapi.TYPE_STRING,
        ),
    ]
    @swagger_auto_schema(manual_parameters=_swagger_params)
    def list(self, *args, **kwargs):
        print(" >>> calling credentialsearch")
        if self.object_class is TopicSearchQuerySet:
            query = self.request.GET.get('name')
            topic_id = self.request.GET.get('topic_id')
            if not self.valid_search_query(query, topic_id):
                raise Http404()
        ret = super(CredentialSearchView, self).list(*args, **kwargs)
        print(" >>> credentialsearch returns", ret)
        return ret

    @swagger_auto_schema(manual_parameters=_swagger_params)
    def retrieve(self, *args, **kwargs):
        print(" >>> calling credentialsearch retrieve")
        ret = super(CredentialSearchView, self).retrieve(*args, **kwargs)
        print(" >>> credentialsearch retrieve returns", ret)
        return ret

    def valid_search_query(self, query, topic_id):
        is_valid = False
        if isinstance(query, str) and len(query.strip()) >= 2:
            is_valid = True
        if isinstance(topic_id, str) and len(topic_id.strip()) > 0:
            is_valid = True
        return is_valid

    index_models = [Credential]
    load_all = True
    serializer_class = CredentialSearchSerializer
    # enable normal filtering
    filter_backends = [
        CredNameFilter,
        CategoryFilter,
        ExactFilter,
        StatusFilter,
        HaystackOrderingFilter,
    ]
    facet_filter_backends = [
        CredNameFilter,
        ExactFilter,
        StatusFilter,
        CustomFacetFilter,
    ]
    facet_serializer_class = CredentialFacetSerializer
    facet_objects_serializer_class = CredentialSearchSerializer
    ordering_fields = ('effective_date', 'revoked_date', 'score')
    ordering = ('-score')

    # FacetMixin provides /facets
    @list_route(methods=["get"], url_path="facets")
    def facets(self, request):
        """
        We want facet_counts from the less-restricted queryset
        """
        queryset = self.get_queryset()
        facet_queryset = self.filter_facet_queryset(queryset)
        result_queryset = self.filter_queryset(queryset)

        #for facet in request.query_params.getlist(self.facet_query_params_text):
            #if ":" not in facet:
            #    continue
            #field, value = facet.split(":", 1)
            #if value:
            #    queryset = queryset.narrow('%s:"%s"' % (field, queryset.query.clean(value)))
        for key in ('category', 'credential_type_id', 'issuer_id'):
            for value in request.query_params.getlist(key):
                if value:
                    facet_queryset = facet_queryset.narrow('{}:"{}"'.format(key, queryset.query.clean(value)))

        serializer = self.get_facet_serializer(facet_queryset.facet_counts(), objects=result_queryset, many=False)
        return Response(serializer.data)


LIMIT = getattr(settings, 'HAYSTACK_MAX_RESULTS', 200)

class TopicSearchQuerySet(RelatedSearchQuerySet):
    """
    Optimize queries when fetching topic-oriented credential search results
    """

    def __init__(self, *args, **kwargs):
        super(TopicSearchQuerySet, self).__init__(*args, **kwargs)
        self._load_all_querysets[Credential] = self.topic_queryset()

    def __len__(self):
        ret = super(TopicSearchQuerySet, self).__len__()
        if ret > LIMIT:
            print(" >>> Limiting the query LEN", ret, LIMIT)
            ret = LIMIT
        return ret

    def topic_queryset(self):
        return Credential.objects.select_related(
            "credential_type",
            "credential_type__issuer",
            "credential_type__schema",
            "topic",
        ).all()

    def _fill_cache(self, start, end, **kwargs):
        print(" >>> Limiting the cache results", start, end, LIMIT)
        if start is not None:
            if start > LIMIT:
                start = LIMIT
        if end is not None:
            if end > LIMIT:
                end = LIMIT
        super(TopicSearchQuerySet, self)._fill_cache(start, end, **kwargs)

    def count(self):
        ret = super(TopicSearchQuerySet, self).count()
        if ret > LIMIT:
            print(" >>> Limiting the query count", ret, LIMIT)
            ret = LIMIT
        return ret


class CredentialTopicSearchView(CredentialSearchView):

    object_class = TopicSearchQuerySet
    serializer_class = CredentialTopicSearchSerializer
    facet_objects_serializer_class = CredentialTopicSearchSerializer
