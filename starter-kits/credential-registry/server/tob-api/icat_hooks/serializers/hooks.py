import random
from datetime import datetime, timedelta
from string import ascii_lowercase, digits

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import exceptions
from rest_framework import serializers
from rest_hooks.models import Hook

from api_v2.auth import generate_random_username
from api_v2.models.CredentialType import CredentialType
from api_v2.models.User import User
from icat_hooks.models.HookUser import HookUser

from ..models.Subscription import Subscription

SUBSCRIBERS_GROUP_NAME = "subscriber"

SUBSCRIPTION_TYPES = {
    "New": "All New Credentials",
    "Stream": "All Credentials for a specific stream (Topic and Type)",
    "Topic": "All Credentials for a Topic",
}


def get_subscribers_group():
    group, created = Group.objects.get_or_create(name=SUBSCRIBERS_GROUP_NAME)
    return group


def get_random_password():
    return "".join([random.choice(ascii_lowercase + digits) for i in range(32)])


def get_password_expiry():
    now = datetime.now()
    return (now + timedelta(days=90)).date()


class HookUserSerializer(serializers.Serializer):
    org_name = serializers.CharField(required=True, max_length=240)
    target_url = serializers.CharField(required=False, max_length=240)
    hook_token = serializers.CharField(required=False, max_length=240)
    registration_expiry = serializers.DateField(required=False, read_only=True)

class RegistrationSerializer(serializers.Serializer):
    reg_id = serializers.ReadOnlyField(source="id")
    org_name = serializers.PrimaryKeyRelatedField(required=True, queryset=HookUser.objects.all(), source="hook_user.org_name", many=True)
    email = serializers.CharField(required=True, max_length=128)
    target_url = serializers.PrimaryKeyRelatedField(required=False, queryset=HookUser.objects.all(), source="hook_user.target_url", many=True)
    hook_token = serializers.PrimaryKeyRelatedField(required=False, queryset=HookUser.objects.all(), source="hook_user.hook_token", many=True)
    username = serializers.CharField(required=False, max_length=40)
    password = serializers.CharField(required=True, max_length=40, write_only=True)
    registration_expiry = serializers.PrimaryKeyRelatedField(required=False, source="hook_user.registration_expiry", read_only=True, many=True)

    def create(self, validated_data):
        """
        Create and return a new instance, given the validated data.
        """
        if "username" in validated_data and 0 < len(validated_data["username"]):
            prefix = validated_data["username"][:16] + "-"
        else:
            prefix = "hook-"
        self.username = generate_random_username(length=32, prefix=prefix, split=None)
        validated_data["username"] = self.username

        # TODO must populate unique DID due to database constraints
        validated_data["DID"] = "not:a:did:" + self.username

        # TODO generate password (?) for now user must supply
        # tmp_password = get_random_password()
        # validated_data['password'] = tmp_password

        print(
            "Create user with", validated_data["username"], validated_data["password"]
        )

        # create api_v2 user
        user_data_keys = ["email", "username", "password", "DID"]
        user_data = {x: validated_data[x] for x in user_data_keys}
        user = get_user_model().objects.create_user(**user_data)
        user.groups.add(get_subscribers_group())
        user.save()

        # create icat_hooks user
        hookuser_data_keys = ["org_name", "target_url", "hook_token"]
        hookuser_data = {x: validated_data[x] for x in hookuser_data_keys}
        hookuser_data["user"] = user
        hookuser_data["registration_expiry"] = get_password_expiry()
        hookuser = HookUser.objects.create(**hookuser_data)

        # prepare serializable response
        response = {}
        response["id"] = user.id
        response["email"] = user.email
        response["username"] = user.username
        response["org_name"] = hookuser.org_name
        response["target_url"] = hookuser.target_url
        response["hook_token"] = hookuser.hook_token
        response["registration_expiry"] = hookuser.registration_expiry

        return response

    def update(self, instance, validated_data):
        """
        Update and return an existing instance, given the validated data.
        """
        instance.email = validated_data.get("email", instance.email)
        hook_user = instance.hook_user
        instance.org_name = validated_data.get("org_name", hook_user.org_name)
        instance.target_url = validated_data.get("target_url", hook_user.target_url)
        instance.hook_token = validated_data.get("hook_token", hook_user.hook_token)

        # TODO potentially update password on each update?
        # instance['password'] = get_random_password()
        if "password" in validated_data:
            instance.set_password(validated_data.get("password"))
            validated_data["registration_expiry"] = get_password_expiry()

        instance.save()
        return instance


class SubscriptionSerializer(serializers.Serializer):
    sub_id = serializers.ReadOnlyField(source="id")
    owner = serializers.ReadOnlyField(source="owner.username")
    subscription_type = serializers.CharField(required=True, max_length=20)
    topic_source_id = serializers.CharField(required=False, max_length=240)
    credential_type = serializers.CharField(
        source="credential_type.schema.name", required=False, max_length=240
    )
    target_url = serializers.CharField(required=False, max_length=240)
    hook_token = serializers.CharField(required=False, max_length=240)

    def validate_subscription_type(self, value):
        if value in SUBSCRIPTION_TYPES:
            return value
        raise serializers.ValidationError("Error not a valid subscription type")

    def validate_credential_type(self, value):
        credential_types = CredentialType.objects.filter(schema__name=value).all()
        if 0 < len(credential_types):
            return value
        raise serializers.ValidationError("Error not a valid credential type")

    def create(self, validated_data):
        """
        Create and return a new instance, given the validated data.
        """
        # note owner is assigned in the view
        credential_type = CredentialType.objects.filter(
            schema__name=validated_data["credential_type"]
        ).first()
        validated_data["credential_type"] = credential_type
        return Subscription.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing instance, given the validated data.
        """
        # TODO
        pass


class SubscriptionResponseSerializer(SubscriptionSerializer):
    owner = RegistrationSerializer()


class RegistrationResponseSerializer(RegistrationSerializer):
    subscriptions = SubscriptionSerializer(many=True)


class HookSerializer(serializers.ModelSerializer):
    def validate_event(self, event):
        if event not in settings.HOOK_EVENTS:
            err_msg = "Unexpected event {}".format(event)
            raise exceptions.ValidationError(detail=err_msg, code=400)
        return event

    class Meta:
        model = Hook
        fields = "__all__"
        read_only_fields = ("user",)
