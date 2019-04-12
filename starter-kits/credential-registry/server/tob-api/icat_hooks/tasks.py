import json
import logging

import requests
from celery.task import Task

logger = logging.getLogger(__name__)


class DeliverHook(Task):
    max_retries = 5

    def run(self, target, payload, instance_id=None, hook_id=None, **kwargs):
        """
        target:     the url to receive the payload.
        payload:    a python primitive data structure
        instance_id:   a possibly None "trigger" instance ID
        hook_id:       the ID of defining Hook object
        """
        try:
            logger.info("Delivering hook to: {}".format(target))
            response = requests.post(
                url=target,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            if response.status_code >= 500:
                response.raise_for_response()
        except requests.ConnectionError:
            delay_in_seconds = 2 ** self.request.retries
            self.retry(countdown=delay_in_seconds)


def deliver_hook_wrapper(target, payload, instance, hook):
    # instance is None if using custom event, not built-in
    if instance is not None:
        instance_id = instance.id
    else:
        instance_id = None
    # pass ID's not objects because using pickle for objects is a bad thing
    kwargs = dict(
        target=target, payload=payload, instance_id=instance_id, hook_id=hook.id
    )
    DeliverHook.apply_async(kwargs=kwargs)
