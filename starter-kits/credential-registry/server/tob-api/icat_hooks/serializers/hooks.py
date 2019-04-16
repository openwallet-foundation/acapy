import random
from datetime import datetime, timedelta
from string import ascii_lowercase, digits

import pytz
import requests
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


# data specific to hook registration that is not part of the User model (but is 1:1)
class UserCredentialSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False, max_length=40)
    password = serializers.CharField(required=True, max_length=40, write_only=True)

    class Meta:
        model = get_user_model()
        fields = ("username", "password")


# registration maps to a user object (user registers and owns subscriptions)
class RegistrationSerializer(serializers.ModelSerializer):
    reg_id = serializers.ReadOnlyField(source="id")
    email = serializers.CharField(required=True, max_length=128)
    org_name = serializers.CharField(required=True, max_length=240)
    target_url = serializers.CharField(required=False, max_length=240)
    hook_token = serializers.CharField(required=False, max_length=240)
    registration_expiry = serializers.DateField(required=False, read_only=True)
    credentials = UserCredentialSerializer(required=False, source="user")

    class Meta:
        model = HookUser
        fields = (
            "reg_id",
            "email",
            "org_name",
            "target_url",
            "hook_token",
            "registration_expiry",
            "credentials",
        )

    def create(self, validated_data):
        """
        Create and return a new instance, given the validated data.
        """
        print("create() with ", validated_data)
        credentials_data = validated_data["user"]
        if "username" in credentials_data and 0 < len(credentials_data["username"]):
            prefix = credentials_data["username"][:16] + "-"
        else:
            prefix = "hook-"
        self.username = generate_random_username(length=32, prefix=prefix, split=None)
        credentials_data["username"] = generate_random_username(
            length=32, prefix=prefix, split=None
        )

        # TODO must populate unique DID due to database constraints
        credentials_data["DID"] = "not:a:did:" + credentials_data["username"]

        # TODO generate password (?) for now user must supply
        # tmp_password = get_random_password()
        # validated_data['password'] = tmp_password

        print(
            "Create user with",
            credentials_data["username"],
            credentials_data["password"],
        )
        credentials_data["email"] = validated_data["email"]

        # create api_v2 user
        user = get_user_model().objects.create_user(**credentials_data)
        user.groups.add(get_subscribers_group())
        user.save()

        # create icat_hooks user
        hookuser_data = validated_data
        hookuser_data["user"] = user
        hookuser_data["registration_expiry"] = get_password_expiry()
        hookuser = HookUser.objects.create(**hookuser_data)

        print("create() with response ", hookuser)

        return hookuser

    def update(self, instance, validated_data):
        """Update user and hook_user. Assumes there is a hook_user for every user."""
        credentials_data = validated_data.pop("credentials")
        validated_data["registration_expiry"] = get_password_expiry()
        super().update(instance, validated_data)

        user = instance.user
        user.email = validated_data["email"]

        # TODO potentially update password on each update?
        # instance['password'] = get_random_password()
        if "password" in credentials_data:
            user.set_password(validated_data.get("password"))
        user.save()

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

    def validate(self, data):
        # validate subscription parameters
        subscription_type = (
            data["subscription_type"] if "subscription_type" in data else None
        )
        topic_source_id = data["topic_source_id"] if "topic_source_id" in data else None
        credential_type = data["credential_type"] if "credential_type" in data else None
        if subscription_type == "New" and topic_source_id is None:
            raise serializers.ValidationError(
                "A topic id is required for subscription of type 'New'"
            )
        if subscription_type == "Stream" and (
            topic_source_id is None or credential_type is None
        ):
            raise serializers.ValidationError(
                "A topic id and a credential type are required for subscription of type 'Topic'"
            )

        # get current user from url
        uri = self.context.get("request").build_absolute_uri()
        context_user = uri.split("registration/")[1].split("/")[0]
        v2_user = User.objects.get(username=context_user)

        # validate hook url and token
        hook_url = data["target_url"] if "target_url" in data else None
        hook_token = data["hook_token"] if "hook_token" in data else None
        hook_user = HookUser.objects.get(user_id=v2_user.id)

        if hook_url is None:
            if hook_user.target_url is None:
                raise serializers.ValidationError(
                    "A target_url must be specified, no default value set in registration."
                )
            else:
                hook_url = hook_user.target_url

        if hook_token is None:
            if hook_user.hook_token is None:
                raise serializers.ValidationError(
                    "A hook-token must be specified, no default value set in registration."
                )
            else:
                hook_token = hook_user.hook_token

        # check hook url is valid
        self.check_live_url(hook_url, hook_token)

        return data

    def check_live_url(self, target_url, hook_token):
        if target_url is not None and hook_token is not None:
            head = {"Authorization": "Bearer " + hook_token}
            data = {"subscription": "test"}
            response = requests.post(target_url, json=data, headers=head)

            if response.status_code != requests.codes.ok:
                raise serializers.ValidationError(
                    "The url {} does not appear to be valid.".format(target_url)
                )

        return "SUCCESS"

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
