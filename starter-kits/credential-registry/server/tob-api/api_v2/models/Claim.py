from django.db import models

from .Auditable import Auditable
from .Credential import Credential


class Claim(Auditable):
    credential = models.ForeignKey(
        Credential, related_name="claims", on_delete=models.CASCADE
    )
    name = models.TextField(blank=True, null=True)
    value = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "claim"
        ordering = ("id",)
