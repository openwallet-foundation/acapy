import json
import re
from typing import Any

import orjson


class JsonUtil:
    @staticmethod
    def format_json(json_str):
        """
        Post-process json string to match json.dumps default formatting.

        `orjson` does not add whitespace between keys and values, or after commas,
        which json does by default. This format method adds this whitespace again for compatability.
        Naturally this adds some overhead again, but still proves faster than standard `json.dumps`
        
        A capture group is used to handle cases where the value is either a digit or a string (starting with ").
        This is used to prevent incorrectly replacing all `:` with `: `. 
        So we refine by replacing `":"` with `": "`, `":\d` with `": \d`, and `":{` with `": {`
        This assumes all keys are strings, wrapped in " quotes, which is the case for or/json.dumps results

        Args:
            json_str: compact json string

        Returns:
            Formatted json string with space after colon and comma
        """
        json_str = re.sub(r'":(["\d\{])', r'": \1', json_str)  # add space after colon
        json_str = re.sub(r',(["\d\{])', r", \1", json_str)  # add space after comma
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
