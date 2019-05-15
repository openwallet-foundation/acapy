from django.db import models
from rest_hooks.models import AbstractHook


class CredentialHook(AbstractHook):
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return (
            str(self.id)
            + " "
            + self.user.username
            + " "
            + self.event
            + " "
            + self.target
        )
