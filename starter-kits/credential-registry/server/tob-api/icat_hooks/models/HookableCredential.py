from django.contrib.postgres import fields as contrib
from django.db import models

from .Subscription import Subscription
from api_v2.models.Auditable import Auditable


class HookableCredential(Auditable):
    """
    For example - in a python shell:

    from django.contrib.auth import get_user_model
    from rest_hooks.models import Hook
    from api_v2.models import HookableCredential, User
    import datetime

    jrrtolkien = get_user_model().objects.create(username='jrrtolkien')

    hook = Hook(user=jrrtolkien, event='hookable_cred.added', target='http://tob-api:8080/api/v2/feedback')
    hook.save()

    cred = HookableCredential(corp_num='BC1234568', credential_type='122', credential_json='{}')
    cred.save()

    ... should fire off a hook to the feedback api
    """
    # corp_num = models.ForeignKey("Topic", related_name="+", to_field="source_id", on_delete=models.DO_NOTHING)
    # credential_type = models.ForeignKey("CredentialType", related_name="+", on_delete=models.DO_NOTHING)
    # 'New' or 'Stream' depending if it's the first credential for the Topic (corp_num)
    topic_status = models.TextField()
    corp_num = models.TextField(null=True)
    credential_type = models.TextField(null=True)
    credential_json = contrib.JSONField(blank=True, null=True)

    def serialize_hook(self, hook):
        # optional, there are serialization defaults
        # we recommend always sending the Hook
        # metadata along for the ride as well
        subscriptions = Subscription.objects.filter(hook=hook)
        if 0 < len(subscriptions):
            hook_dict = subscriptions[0].dict()
        else:
            hook_dict = hook.dict()
        dict = {
            'subscription': hook_dict,
            'data': {
                'id': self.id,
                'corp_num': self.corp_num,
                'credential_type': self.credential_type,
                'credential_json': self.credential_json,
                # ... other fields here ...
            }
        }
        print("Sending hook", dict)
        return dict

    class Meta:
        db_table = "hookable_cred"
        #unique_together = (("corp_num", "credential_type"),)
        ordering = ("corp_num", "credential_type")
