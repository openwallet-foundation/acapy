import logging
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import exceptions
from rest_framework import serializers

from api_v2.auth import generate_random_username
from api_v2.models.Credential import Credential
from api_v2.models.CredentialType import CredentialType
from api_v2.models.User import User


logger = logging.getLogger(__name__)


# generic message from indy agent callback
class IndyAgentCallbackSerializer(serializers.Serializer):
    reg_id = serializers.ReadOnlyField(source="id")
    email = serializers.CharField(required=True, max_length=128)
    org_name = serializers.CharField(required=True, max_length=240)
    target_url = serializers.CharField(required=False, max_length=240)
    hook_token = serializers.CharField(required=False, max_length=240)
    registration_expiry = serializers.DateField(required=False, read_only=True)

