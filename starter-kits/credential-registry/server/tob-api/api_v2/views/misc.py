import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import FormParser

from api_v2.feedback import email_feedback
from api_v2.models.Claim import Claim
from api_v2.models.Credential import Credential as CredentialModel
from api_v2.models.CredentialType import CredentialType
from api_v2.models.Issuer import Issuer
from api_v2.models.Topic import Topic
from api_v2.utils import model_counts, record_count, solr_counts

LOGGER = logging.getLogger(__name__)


@swagger_auto_schema(
    method="get", operation_id="api_v2_quickload", operation_description="quick load"
)
@api_view(["GET"])
@authentication_classes(())
@permission_classes((permissions.AllowAny,))
def quickload(request, *args, **kwargs):
    count_models = {
        "claim": Claim,
        "credential": CredentialModel,
        "credentialtype": CredentialType,
        "issuer": Issuer,
        "topic": Topic,
    }
    with connection.cursor() as cursor:
        counts = {
            mname: model_counts(model, cursor)
            for (mname, model) in count_models.items()
        }
        actual_credential_count = record_count(CredentialModel, cursor)

    counts["actual_credential_count"] = actual_credential_count
    cred_counts = solr_counts()
    indexes_synced = (actual_credential_count - cred_counts["total"]) == 0
    return JsonResponse(
        {
            "counts": counts,
            "credential_counts": cred_counts,
            "demo": settings.DEMO_SITE,
            "indexes_synced": indexes_synced,
        }
    )


@swagger_auto_schema(
    method="post",
    manual_parameters=[
        openapi.Parameter(
            "from_name",
            openapi.IN_FORM,
            description="Sender name",
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            "from_email",
            openapi.IN_FORM,
            description="Sender email address",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_EMAIL,
        ),
        openapi.Parameter(
            "comments",
            openapi.IN_FORM,
            description="Comments",
            type=openapi.TYPE_STRING,
        ),
    ],
)
@api_view(["POST"])
@authentication_classes(())
@permission_classes((permissions.AllowAny,))
@parser_classes((FormParser,))
def send_feedback(request, *args, **kwargs):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip_addr = x_forwarded_for.split(",")[0]
    else:
        ip_addr = request.META.get("REMOTE_ADDR")
    from_name = request.POST.get("from_name")
    from_email = request.POST.get("from_email")
    reason = request.POST.get("reason")
    comments = request.POST.get("comments")
    email_feedback(ip_addr, from_name, from_email, reason, comments)
    return JsonResponse({"status": "ok"})


@swagger_auto_schema(
    method="get",
    operation_id="api_v2_verify_credential",
    operation_description="verify credential",
)
@api_view(["GET"])
@authentication_classes(())
@permission_classes((permissions.AllowAny,))
def verify_credential(request, *args, **kwargs):
    # TODO: implement functionality
    return JsonResponse({"status": "501", "message": "Not Implemented"})
