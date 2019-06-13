from django.db import models


class Auditable(models.Model):
    create_timestamp = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    update_timestamp = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        abstract = True
