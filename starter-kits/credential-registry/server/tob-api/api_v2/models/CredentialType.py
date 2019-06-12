from django.contrib.postgres import fields as contrib
from django.db import models

from .Auditable import Auditable
from .Issuer import Issuer
from .Schema import Schema


class CredentialType(Auditable):
    schema = models.ForeignKey(
        Schema, related_name="credential_types", on_delete=models.CASCADE
    )
    issuer = models.ForeignKey(
        Issuer, related_name="credential_types", on_delete=models.CASCADE
    )
    description = models.TextField(blank=True, null=True)
    processor_config = contrib.JSONField(blank=True, null=True)
    credential_def_id = models.TextField(db_index=True, null=True)
    logo_b64 = models.TextField(null=True)
    visible_fields = models.TextField(null=True)
    last_issue_date = models.DateTimeField(null=True)
    url = models.TextField(blank=True, null=True)
    claim_descriptions = contrib.JSONField(blank=True, null=True)
    claim_labels = contrib.JSONField(blank=True, null=True)
    category_labels = contrib.JSONField(blank=True, null=True)

    class Meta:
        db_table = "credential_type"
        unique_together = (("schema", "issuer"),)
        ordering = ("id",)

    def get_has_logo(self):
        return bool(self.logo_b64 or (self.issuer and self.issuer.logo_b64))
