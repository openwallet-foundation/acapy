from django.db import models

from .Auditable import Auditable


class Address(Auditable):
    reindex_related = ["credential"]

    credential = models.ForeignKey(
        "Credential", related_name="addresses", on_delete=models.CASCADE
    )
    addressee = models.TextField(null=True)
    civic_address = models.TextField(null=True)
    city = models.TextField(null=True)
    province = models.TextField(null=True)
    postal_code = models.TextField(null=True)
    country = models.TextField(null=True)

    class Meta:
        db_table = "address"
        ordering = ("id",)
