import logging
import random
from string import ascii_lowercase, digits

from django.contrib.auth.models import Group
from rest_framework import permissions

from api_v2.models.User import User

ISSUERS_GROUP_NAME = "issuers"


def create_issuer_user(
    email,
    issuer_did,
    username=None,
    password=None,
    display_name="",
    first_name="",
    last_name="",
    verkey=None,
):
    logger = logging.getLogger(__name__)
    try:
        user = User.objects.get(DID=issuer_did)
    except User.DoesNotExist:
        logger.debug("Creating user for DID '{0}' ...".format(issuer_did))
        if not username:
            username = generate_random_username(length=12, prefix="issuer-", split=None)
        user = User.objects.create_user(
            username,
            email=email,
            password=password,
            DID=issuer_did,
            verkey=verkey,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
        )
        user.groups.add(get_issuers_group())
    else:
        user.DID = issuer_did
        user.verkey = verkey
        user.email = email
        user.display_name = display_name
        if first_name != None:
            user.first_name = first_name
        if last_name != None:
            user.last_name = last_name
        user.save()
    return user


def get_issuers_group():
    group, created = Group.objects.get_or_create(name=ISSUERS_GROUP_NAME)
    return group


def generate_random_username(
    length=16, chars=ascii_lowercase + digits, split=4, delimiter="-", prefix=""
):
    username = "".join([random.choice(chars) for i in range(length)])

    if split:
        username = delimiter.join(
            [
                username[start : start + split]
                for start in range(0, len(username), split)
            ]
        )
    username = prefix + username

    try:
        User.objects.get(username=username)
        return generate_random_username(
            length=length, chars=chars, split=split, delimiter=delimiter
        )
    except User.DoesNotExist:
        return username


class IsRegisteredIssuer(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.groups.filter(name=ISSUERS_GROUP_NAME).exists()
        )
