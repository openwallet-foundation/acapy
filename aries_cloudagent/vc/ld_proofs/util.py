from pyld import jsonld
from typing import Union


def frame_without_compact_to_relative(
    input: Union[dict, str], frame: dict, options: dict = None
):
    """Frame document without compacting to relative.

    We need to expand first as otherwise the base (e.g. did: from did:key) is removed.
    in jsonld.js this can be solved by setting `compactToRelative` to false
    however this is not supported in pyld.
    https://github.com/digitalbazaar/jsonld.js/blob/93a9d3f9abaffb7666f0fe0cb1adf59e0f816b5a/lib/jsonld.js#L111

    Args:
        input (Union[dict, str]): the JSON-LD input to frame.
        frame (dict): the JSON-LD frame to use.
        options (dict, optional): the options to use. Defaults to None.

    Returns:
        the framed JSON-LD output.
    """
    expanded = jsonld.expand(input, options=options)

    framed = jsonld.frame(
        expanded,
        frame,
        options=options,
    )

    return framed
