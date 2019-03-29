import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import FormParser
from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet

from api_v2.models.User import User
from api_v2.models.Subscription import Subscription
from api_v2.serializers.hooks import *


class RegistrationViewSet(ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.
    """
    queryset = User.objects.all()
    serializer_class = RegistrationSerializer
    #permission_classes = (permissions.IsAuthenticatedOrReadOnly,
    #                      IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class SubscriptionViewSet(ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.
    """
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    #permission_classes = (permissions.IsAuthenticatedOrReadOnly,
    #                      IsOwnerOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

"""
@swagger_auto_schema(method='post', query_serializer=NewRegistrationSerializer, operation_id='v2_hook_registration_create')
@api_view(['POST'])
@authentication_classes(())
@permission_classes((permissions.AllowAny,))
def registration_create(request):
    if request.method == 'POST':
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(methods=('get','put','delete'), query_serializer=RegistrationSerializer, operation_id='v2_hook_registration')
@api_view(['GET', 'PUT', 'DELETE'])
def registration(request, userid):
    if request.method == 'GET':
        pass
    elif request.method == 'PUT':
        pass
    elif request.method == 'DELETE':
        pass


@swagger_auto_schema(methods=('get','post'), query_serializer=NewRegistrationSerializer, operation_id='v2_hook_subscription_create')
@api_view(['GET', 'POST'])
@authentication_classes(())
@permission_classes((permissions.AllowAny,))
def subscription_create(request, userid):
    if request.method == 'GET':
        pass
    elif request.method == 'POST':
        pass
"""

@swagger_auto_schema(methods=('get','put','delete'), query_serializer=NewRegistrationSerializer, operation_id='v2_hook_subscription')
@api_view(['GET', 'PUT', 'DELETE'])
def subscription(request, userid, pk):
    if request.method == 'GET':
        pass
    elif request.method == 'PUT':
        pass
    elif request.method == 'DELETE':
        pass

