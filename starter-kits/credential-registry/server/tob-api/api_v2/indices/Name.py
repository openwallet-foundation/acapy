from django.utils import timezone
from haystack import indexes

from api_v2.models.Name import Name as NameModel


class NameIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr="text")

    autocomplete = indexes.EdgeNgramField()

    @staticmethod
    def prepare_autocomplete(obj):
        return " ".join((obj.name))

    def get_model(self):
        return NameModel

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(create_timestamp__lte=timezone.now())
