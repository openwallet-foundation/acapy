from django.http import HttpResponse

from api_v2.models.Credential import Credential


def health(request):
    """
    Health check for OpenShift
    """
    return HttpResponse(Credential.objects.count())
