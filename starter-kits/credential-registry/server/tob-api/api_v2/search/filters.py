import functools
import logging
import operator

from django.conf import settings
from drf_haystack.query import (
    BaseQueryBuilder,
    FacetQueryBuilder,
    FilterQueryBuilder,
)
from drf_haystack.filters import (
    HaystackFilter,
    HaystackFacetFilter,
)
from haystack.inputs import Clean, Exact, Raw

LOGGER = logging.getLogger(__name__)


class CustomFilter(HaystackFilter):
    pass


class Proximate(Clean):
    """
    Prepare a filter clause matching one or more words, adjusting score according to word proximity
    """
    input_type_name = 'contains'
    post_process = False # don't put AND between terms

    def query_words(self, *parts):
        skip = settings.SEARCH_SKIP_WORDS or ()
        word_len = self.kwargs.get('wordlen', 4)
        for part in parts:
            clean = part.strip()
            if len(clean.strip('_-,.;\'"')) >= word_len and clean.lower() not in skip:
                yield clean

    def prepare(self, query_obj):
        # clean input
        query_string = super(Proximate, self).prepare(query_obj)
        if query_string is not '':
            # match phrase with minimal word movements
            proximity = self.kwargs.get('proximity', 5)
            parts = query_string.split(' ')
            if len(parts) > 1:
                output = '"{}"~{}'.format(query_string, proximity)
            else:
                output = parts[0]
            if 'boost' in self.kwargs:
                output = '{}^{}'.format(output, self.kwargs['boost'])

            # increase score for any individual term
            if self.kwargs.get('any') and len(parts) > 1:
                words = list(self.query_words(*parts))
                if words:
                    output = ' OR '.join([output, *words])
        else:
            output = query_string
        return output


class AutocompleteFilterBuilder(BaseQueryBuilder):
    query_param = 'q'

    def build_name_query(self, term):
        SQ = self.view.query_object
        match_any = not settings.SEARCH_TERMS_EXCLUSIVE
        return SQ(name_suggest=Proximate(term)) \
               | SQ(name_precise=Proximate(term, boost=10, any=match_any))

    def build_query(self, **filters):
        inclusions = []
        exclusions = None
        SQ = self.view.query_object
        if self.query_param in filters:
            for qval in filters[self.query_param]:
                if len(qval):
                    inclusions.append(self.build_name_query(qval))
        inclusions = functools.reduce(operator.and_, inclusions) if inclusions else None
        return inclusions, exclusions


class AutocompleteFilter(CustomFilter):
    """
    Apply name autocomplete filter to credential search
    """
    query_builder_class = AutocompleteFilterBuilder


class CategoryFilterBuilder(BaseQueryBuilder):
    query_param = 'category'

    def build_query(self, **filters):
        inclusions = {}
        exclusions = {}
        SQ = self.view.query_object
        for qname, qvals in filters.items():
            category = None
            by_value = False
            negate = False
            if ':' in qname:
                parts = qname.split(':', 1)
                if parts[0] == self.query_param:
                    category = parts[1]
                    if '__' in category:
                        category, oper = category.split('__', 1)
                        if oper == 'not':
                            negate = True
                        elif oper != 'exact':
                            continue
            else:
                if '__' in qname:
                    qname, oper = qname.split('__', 1)
                    if oper == 'not':
                        negate = True
                    elif oper != 'exact':
                        continue
                if qname == self.query_param:
                    by_value = True
            if not category and not by_value:
                continue
            target = exclusions if negate else inclusions
            for qv in qvals:
                if not qv:
                    continue
                if by_value:
                    if '::' not in qv:
                        continue
                    category, qv = qv.split('::', 1)
                filt = Exact('{}::{}'.format(category, qv))
                sq_filt = SQ(**{self.query_param: filt})
                if category in target:
                    target[category] = target[category] | sq_filt
                else:
                    target[category] = sq_filt
        inclusions = functools.reduce(operator.and_, inclusions.values()) if inclusions else None
        exclusions = functools.reduce(operator.and_, exclusions.values()) if exclusions else None
        return inclusions, exclusions


class CategoryFilter(CustomFilter):
    """
    Apply category filters to credential search
    """
    query_builder_class = CategoryFilterBuilder


class CredNameFilterBuilder(AutocompleteFilterBuilder):
    """
    Augment autocomplete filter with matching on the related topic source ID
    """
    query_param = 'name'

    def build_name_query(self, term):
        SQ = self.view.query_object
        filter = super(CredNameFilterBuilder, self).build_name_query(term)
        if term and ' ' not in term:
            filter = filter | (SQ(source_id=Exact(term)) & SQ(name=Raw('*')))
        return filter


class CredNameFilter(AutocompleteFilter):
    """
    Apply autocomplete filter
    """
    query_builder_class = CredNameFilterBuilder


class ExactFilterBuilder(BaseQueryBuilder):
    """
    Perform exact matching on specified fields
    """
    def build_query(self, **filters):
        inclusions = {}
        exclusions = None
        SQ = self.view.query_object
        exact_fields = getattr(self.view.serializer_class.Meta, 'exact_fields', [])
        for qname, qvals in filters.items():
            if qname not in exact_fields:
                continue
            for qval in qvals:
                if qval:
                    filt = SQ(**{qname: Exact(qval)})
                    inclusions[qname] = (filt | inclusions[qname]) if qname in inclusions else filt
        inclusions = functools.reduce(operator.and_, inclusions.values()) if inclusions else None
        return inclusions, exclusions


class ExactFilter(CustomFilter):
    """
    Apply exact-match filters
    """
    query_builder_class = ExactFilterBuilder


class CustomFacetQueryBuilder(FacetQueryBuilder):
    def parse_field_options(self, *options):
        # skip parsing of URL arguments as facets for now
        return {}


class CustomFacetFilter(HaystackFacetFilter):
    query_builder_class = CustomFacetQueryBuilder


class StatusFilterBuilder(BaseQueryBuilder):
    def build_query(self, **filters):
        inclusions = {}
        exclusions = None
        SQ = self.view.query_object
        status_fields = getattr(self.view.serializer_class.Meta, 'status_fields', {})
        for qname, qval in status_fields.items():
            if qval and qval != 'any':
                inclusions[qname] = SQ(**{qname: Exact(qval)})
        for qname, qvals in filters.items():
            if qname not in status_fields:
                continue
            for qval in qvals:
                if qval and qval != 'any':
                    inclusions[qname] = SQ(**{qname: Exact(qval)})
                elif qname in inclusions:
                    del inclusions[qname]
        inclusions = functools.reduce(operator.and_, inclusions.values()) if inclusions else None
        return inclusions, exclusions


class StatusFilter(CustomFilter):
    """
    Apply boolean filter flags
    """
    query_builder_class = StatusFilterBuilder
