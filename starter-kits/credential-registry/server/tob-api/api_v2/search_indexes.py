# TODO: Figure out how to configure haystack to register indices in
#       ./indices/<IndexName> instead of this default file...

from itertools import chain
import logging

from haystack import indexes
from django.db.models import Prefetch
from django.utils import timezone

from api_v2.models.Credential import Credential as CredentialModel
from api_v2.models.Name import Name as NameModel
from api_v2.search.index import TxnAwareSearchIndex

LOGGER = logging.getLogger(__name__)


class CredentialIndex(TxnAwareSearchIndex, indexes.Indexable):
    document = indexes.CharField(document=True, use_template=True)

    name = indexes.MultiValueField()
    location = indexes.MultiValueField()
    category = indexes.MultiValueField()
    topic_id = indexes.IntegerField(model_attr="topic_id")
    topic_type = indexes.CharField(model_attr="topic__type")
    source_id = indexes.CharField(model_attr="topic__source_id")
    inactive = indexes.BooleanField(model_attr="inactive")
    revoked = indexes.BooleanField(model_attr="revoked")
    latest = indexes.BooleanField(model_attr="latest")
    create_timestamp = indexes.DateTimeField(model_attr="create_timestamp")
    effective_date = indexes.DateTimeField(model_attr="effective_date")
    revoked_date = indexes.DateTimeField(model_attr="revoked_date", null=True)
    credential_set_id = indexes.IntegerField(model_attr="credential_set_id", null=True)
    credential_type_id = indexes.IntegerField(model_attr="credential_type_id")
    issuer_id = indexes.IntegerField(model_attr="credential_type__issuer_id")
    schema_name = indexes.CharField(model_attr="credential_type__schema__name")
    schema_version = indexes.CharField(model_attr="credential_type__schema__version")
    wallet_id = indexes.CharField(model_attr="wallet_id")

    @staticmethod
    def prepare_name(obj):
        return [name.text for name in obj.all_names]

    @staticmethod
    def prepare_category(obj):
        return [
          "{}::{}".format(cat.type, cat.value) for cat in obj.all_categories
        ]

    @staticmethod
    def prepare_location(obj):
        locations = []
        for address in obj.addresses.all():
            loc = " ".join(filter(None, (
              address.addressee,
              address.civic_address,
              address.city,
              address.province,
              address.postal_code,
              address.country,
            )))
            if loc:
              locations.append(loc)
        return locations

    def get_model(self):
        return CredentialModel

    def index_queryset(self, using=None):
        prefetch = (
            "addresses",
            "attributes",
            "names",
        )
        select = (
          "credential_set",
          "credential_type",
          "credential_type__schema",
          "topic",
        )
        queryset = super(CredentialIndex, self).index_queryset(using)\
            .prefetch_related(*prefetch)\
            .select_related(*select)
        return queryset

    def read_queryset(self, using=None):
        select = (
            "credential_type__issuer",
        )
        queryset = self.index_queryset(using) \
            .select_related(*select)
        return queryset

    def get_updated_field(self):
      return "update_timestamp"
