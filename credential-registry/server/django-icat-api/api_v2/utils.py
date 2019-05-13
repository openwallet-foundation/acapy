
"""
A collection of utility classes for TOB
"""

from datetime import datetime, timedelta
import logging
import os

from django.conf import settings
from django.db import connection

from haystack.query import SearchQuerySet
from pysolr import SolrError

LOGGER = logging.getLogger(__name__)


def fetch_custom_settings(*args):
    _values = {}

    if not hasattr(settings, "CUSTOMIZATIONS"):
        return _values

    _dict = settings.CUSTOMIZATIONS
    for arg in args:
        if not _dict[arg]:
            return _values
        _dict = _dict[arg]

    return _dict


def apply_custom_methods(cls, *args):
    functions = list(fetch_custom_settings(*args))
    for function in functions:
        setattr(cls, function.__name__, classmethod(function))


def model_counts(model_cls, cursor=None, optimize=None):
    if optimize is None:
        optimize = getattr(settings, "OPTIMIZE_TABLE_ROW_COUNTS", True)
    if not optimize:
        return model_cls.objects.count()
    close = False
    try:
        if not cursor:
            cursor = connection.cursor()
            close = True
        cursor.execute(
            "SELECT reltuples::BIGINT AS estimate FROM pg_class WHERE relname=%s",
            [model_cls._meta.db_table])
        row = cursor.fetchone()
    finally:
        if close:
            cursor.close()
    return row[0]


def solr_counts():
    latest_q = SearchQuerySet().filter(latest=True)
    registrations_q = latest_q.filter(category="entity_status::ACT")
    last_week = datetime.now() - timedelta(days=7)
    last_month = datetime.now() - timedelta(days=30)
    last_week_q = SearchQuerySet().filter(create_timestamp__gte=last_week)
    last_month_q = SearchQuerySet().filter(create_timestamp__gte=last_month)
    try:
        return {
            "active": latest_q.count(),
            "registrations": registrations_q.count(),
            "last_month": last_month_q.count(),
            "last_week": last_week_q.count(),
        }
    except SolrError:
        LOGGER.exception("Error when retrieving quickload counts from Solr")
        return False
