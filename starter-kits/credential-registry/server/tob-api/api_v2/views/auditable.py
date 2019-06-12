from rest_framework import status
from rest_framework.response import Response


class AuditableMixin(object):
    def serialize_object(self, request, data):
        http_sm_user = request.META.get("HTTP_SM_USER")
        data.update({"CREATE_USER": http_sm_user, "UPDATE_USER": http_sm_user})
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer, request)
        return serializer.data

    def create(self, request, *args, **kwargs):
        objs = []
        if type(request.data) is list:
            for data in request.data:
                objs.append(self.serialize_object(request, data))
        else:
            objs.append(self.serialize_object(request, request.data))

        response = objs[0] if len(objs) == 1 else objs
        headers = self.get_success_headers(response)
        return Response(response, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer, request):
        instance = serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        http_sm_user = request.META.get("HTTP_SM_USER")
        request.data.update({"UPDATE_USER": http_sm_user})
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()
