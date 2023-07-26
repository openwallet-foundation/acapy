import json
import re
from typing import Any

import orjson


class JsonUtil:
    @staticmethod
    def format_json(json_str):
        """
        Post-processes a json string to conform to json.dumps default formatting.

        The `orjson` library does not introduce whitespace between keys and values, nor after commas.
        The default behavior of `json.dumps`, however, does include this whitespace. For compatibility
        purposes, this method reintroduces such whitespace. Although this introduces some overhead, the
        overall process remains faster than using standard `json.dumps`.

        A capture group in a regular expression is used to cater to the cases where the value following a
        colon (:) in a JSON string is either a string (starting with "), a digit, a JSON object (starting
        with {), or a boolean value or null (starting with "t", "f", or "n" respectively).

        This regular expression only operates under the assumption that all keys in the JSON string are
        strings enclosed in quotes (") which is the default behavior for `json.dumps` and `orjson.dumps`.

        Args:
            json_str: The compact json string to be formatted.

        Returns:
            Formatted json string with a space added after each colon and comma where appropriate.
        """
        json_str = re.sub(r',(["\d\{tfn])', r", \1", json_str)  # add space after comma
        json_str = re.sub(r'":(["\d\{tfn])', r'": \1', json_str)  # space after colon
        return json_str

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
        return JsonUtil.format_json(orjson.dumps(obj, *args, **kwargs).decode())

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
