import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


# generic message from indy agent callback
class IndyAgentCallbackSerializer(serializers.Serializer):
    reg_id = serializers.ReadOnlyField(source="id")
    email = serializers.CharField(required=True, max_length=128)
    org_name = serializers.CharField(required=True, max_length=240)
    target_url = serializers.CharField(required=False, max_length=240)
    hook_token = serializers.CharField(required=False, max_length=240)
    registration_expiry = serializers.DateField(required=False, read_only=True)
