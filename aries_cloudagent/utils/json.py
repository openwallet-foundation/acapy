"""A module providing a utility class for handling JSON-related operations."""

import json
import re
from typing import Any

import orjson


class JsonUtil:
    """A utility class for handling JSON-related operations.

    This class provides static methods for formatting JSON strings, and
    for converting between Python objects and JSON strings/files. It uses
    the `orjson` library where possible for its speed advantages, but reverts
    to the standard `json` library where `orjson` does not support the required
    functionality.
    """

    @staticmethod
    def format_json(json_str):
        """Post-processes a json string to conform to json.dumps default formatting.

        The `orjson` library does not introduce whitespace between keys and values,
        nor after commas. The default behavior of `json.dumps`, however, does include
        this whitespace. For compatibility purposes, this method reintroduces such
        whitespace. Although this introduces some overhead, the overall process
        remains faster than using standard `json.dumps`.

        A capture group in a regular expression is used to cater to the cases where
        the value following a colon (:) in a JSON string is either a string
        (starting  with "), a digit, a JSON or a List object (starting with { or [),
        or a boolean value or null (starting with "t", "f", or "n" respectively).

        This regular expression only operates under the assumption that all keys in
        the JSON string are strings enclosed in quotes (") which is the default
        behavior for `json.dumps` and `orjson.dumps`.

        Args:
            json_str: The compact json string to be formatted.

        Returns:
            Formatted json string with a space added where appropriate.

        """

        json_str = re.sub(r',([tfn"\d\{\[])', r", \1", json_str)  # space after comma
        json_str = re.sub(r'":([tfn"\d\{\[])', r'": \1', json_str)  # space after colon
        return json_str

    @staticmethod
    def dumps(obj, *args, **kwargs) -> str:
        """Convert a Python object into a json string.

        Args:
            obj: The data to be converted
            *args: Extra arguments to pass to the orjson.dumps() function
            **kwargs: Extra keyword arguments to pass to the orjson.dumps() function

        Returns:
            The json string representation of obj

        """

        if "indent" in kwargs:  # not supported in orjson, and only used in demo logs
            return json.dumps(obj, *args, **kwargs)
        else:
            return JsonUtil.format_json(orjson.dumps(obj, *args, **kwargs).decode())

    @staticmethod
    def loads(s: str, *args, **kwargs) -> Any:
        """Parse a JSON string into a Python object.

        Args:
            s: The JSON string to be parsed
            *args: Extra arguments to pass to the orjson.loads() function
            **kwargs: Extra keyword arguments to pass to the orjson.loads() function

        Returns:
            The Python representation of s

        """

        return orjson.loads(s, *args, **kwargs)
