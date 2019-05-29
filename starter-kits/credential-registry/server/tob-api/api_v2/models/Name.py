from django.db import models

from .Auditable import Auditable

from .Credential import Credential


class Name(Auditable):
    reindex_related = ['credential']

    credential = models.ForeignKey(Credential, related_name="names", on_delete=models.CASCADE)
    text = models.TextField(null=True)
    language = models.TextField(null=True)
    type = models.TextField(null=True)

    class Meta:
        db_table = "name"
        ordering = ('id',)
