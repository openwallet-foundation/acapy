from rest_framework import serializers

from api_v2.models.User import User
from api_v2.models.Subscription import Subscription


class NewRegistrationSerializer(serializers.Serializer):
    org_name = serializers.CharField(required=True, max_length=240)
    email = serializers.CharField(required=True, max_length=128)
    target_url = serializers.CharField(required=False, max_length=240)
    hook_token = serializers.CharField(required=False, max_length=240)

    def create(self, validated_data):
        """
        Create and return a new instance, given the validated data.
        """
        username = generate_random_username(
                length=12, prefix="hook-", split=None
            )
        return Snippet.objects.create(**validated_data)


class RegistrationSerializer(NewRegistrationSerializer):
    userid = serializers.CharField(required=False, max_length=40)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Snippet` instance, given the validated data.
        """
        instance.title = validated_data.get('title', instance.title)
        instance.code = validated_data.get('code', instance.code)
        instance.linenos = validated_data.get('linenos', instance.linenos)
        instance.language = validated_data.get('language', instance.language)
        instance.style = validated_data.get('style', instance.style)
        instance.save()
        return instance


class SubscriptionSerializer(serializers.Serializer):
    userid = serializers.CharField(required=True, max_length=40)
    subscription_type = serializers.CharField(required=True, max_length=20)
    topic_source_id = serializers.CharField(required=False, max_length=240)
    credential_type = serializers.CharField(required=False, max_length=240)
    target_url = serializers.CharField(required=False, max_length=240)
    hook_token = serializers.CharField(required=False, max_length=240)


class SubscriptionResponseSerializer(SubscriptionSerializer):
    owner = RegistrationSerializer()


class RegistrationResponseSerializer(RegistrationSerializer):
    subscriptions = SubscriptionSerializer(many=True)

