from django.db import models
from django.utils import timezone

from .Auditable import Auditable


class Schema(Auditable):
    name = models.TextField()
    version = models.TextField()
    origin_did = models.TextField()

    class Meta:
        db_table = "schema"
        unique_together = (("name", "version", "origin_did"),)
        ordering = ('id',)
