
import json

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from api_v2.models.Credential import Credential


def health(request):
    """
    Health check for OpenShift
    """
    return HttpResponse(Credential.objects.count())
