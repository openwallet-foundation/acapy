from typing import Sequence
from pyld import jsonld

from .document_loader import DocumentLoader


def diff_dict_keys(full: dict, with_missing: dict, prefix: str = None) -> Sequence[str]:
    """Get the difference in dict keys between full and with_missing.

    Checks recursively

    Args:
        full (dict): The full dict with all keys present
        with_missing (dict): The dict with possibly keys missing
        prefix (str, optional): The prefix. Mostly used for internal recursion.

    Returns:
        Sequence[str]: List of missing property names in with_missing

    """

    missing = []
    # Loop trough all key/value pairs of the full document
    for key, value in full.items():
        _prefix = f"{prefix}.{key}" if prefix else key
        #
        # If the key is not present in the with_missing dict, add it to the list
        if key not in with_missing:
            missing.append(_prefix)

        # If the key is present, but is a dict itself, recursively check nested keys
        elif isinstance(value, dict):
            missing.extend(diff_dict_keys(value, with_missing.get(key), prefix=_prefix))

        # If the key is present, but is a list, recursively check nested keys for entries
        elif isinstance(value, list):
            for i in range(len(value)):
                nested_value = value[i]

                # Only check for nested list or dicts. We're not checking for string values
                if isinstance(nested_value, (dict, list)):
                    __prefix = f"{_prefix}[{i}]"
                    missing.extend(
                        diff_dict_keys(
                            nested_value, with_missing.get(key)[i], prefix=__prefix
                        )
                    )

    return missing


def get_properties_without_context(
    document: dict, document_loader: DocumentLoader
) -> Sequence[str]:
    """Get the properties from document that don't have an context definition."""
    [expanded] = jsonld.expand(document, {"documentLoader": document_loader})

    framed = jsonld.compact(
        expanded,
        document["@context"],
        {"skipExpansion": True, "documentLoader": document_loader},
    )

    missing = diff_dict_keys(document, framed)

    return missing
