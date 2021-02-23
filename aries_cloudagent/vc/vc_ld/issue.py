from typing import Any

from .checker import check_credential


def issue(credential: dict, suite: Any, *, purpose: Any = None):
    # common credential checks
    check_credential(credential)

    # todo: document loader
    # see: https://github.com/animo/aries-cloudagent-python/issues/3

    if not suite.verification_method:
        raise Exception('"suite.verification_method" property is required')

    # todo: set purpose to CredentialIssuancePurpose if not present
    # see: https://github.com/animo/aries-cloudagent-python/issues/4

    # todo: sign credential, dependent on ld-proofs functionality
    return credential