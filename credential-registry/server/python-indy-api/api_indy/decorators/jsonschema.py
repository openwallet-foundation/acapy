import logging
from functools import wraps
import jsonschema

from django.http import JsonResponse

logger = logging.getLogger(__name__)


def validate(schema):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                jsonschema.validate(request.data, schema)
            except jsonschema.ValidationError as e:
                logger.exception(e)
                response = {
                    "success": False,
                    "result": "Schema validation error: {}".format(e),
                }
                return JsonResponse(response, status=400)

            return func(request, *args, **kwargs)

        return wrapper

    return decorator
