import json
from typing import Any

import orjson


class JsonUtil:
    @staticmethod
    def dumps(obj, *args, **kwargs) -> str:
        """
        Convert a Python object into a json string.

        Args:
            obj: The data to be converted
            *args: Extra arguments to pass to the orjson.dumps() function
            **kwargs: Extra keyword arguments to pass to the orjson.dumps() function

        Returns:
            The json string representation of obj
        """
        return orjson.dumps(obj, *args, **kwargs).decode()

    @staticmethod
    def loads(s: str, *args, **kwargs) -> Any:
        """
        Parse a JSON string into a Python object.

        Args:
            s: The JSON string to be parsed
            *args: Extra arguments to pass to the orjson.loads() function
            **kwargs: Extra keyword arguments to pass to the orjson.loads() function

        Returns:
            The Python representation of s
        """
        return orjson.loads(s, *args, **kwargs)

    @staticmethod
    def load(fp, *args, **kwargs) -> Any:
        """
        Parse a JSON file into a Python object.

        Args:
            fp: a .read()-supporting file-like object containing a JSON document
            *args: Extra arguments to pass to the json.load() function
            **kwargs: Extra keyword arguments to pass to the json.load() function

        Returns:
            The Python representation of fp
        """
        return json.load(fp, *args, **kwargs)
