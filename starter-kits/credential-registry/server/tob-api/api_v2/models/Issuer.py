from django.db import models

from .Auditable import Auditable


class Issuer(Auditable):
    did = models.TextField(unique=True)
    name = models.TextField()
    abbreviation = models.TextField()
    email = models.TextField()
    url = models.TextField()
    logo_b64 = models.TextField(null=True)
    endpoint = models.TextField(null=True)

    class Meta:
        db_table = "issuer"
        ordering = ('id',)

    def get_has_logo(self):
        return bool(self.logo_b64)
