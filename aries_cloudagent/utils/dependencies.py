"""Dependency related util methods."""

import sys


def is_indy_sdk_module_installed():
    """Check whether indy (indy-sdk) module is installed.

    Returns:
        bool: Whether indy (indy-sdk) is installed.

    """
    try:
        # Check if already imported
        if "indy" in sys.modules:
            return True

        # Try to import
        import indy  # noqa: F401

        return True
    except ModuleNotFoundError:
        # Not installed if import went wrong
        return False


def is_ursa_bbs_signatures_module_installed():
    """Check whether ursa_bbs_signatures module is installed.

    Returns:
        bool: Whether ursa_bbs_signatures is installed.

    """
    try:
        # Check if already imported
        if "ursa_bbs_signatures" in sys.modules:
            return True

        # Try to import
        import ursa_bbs_signatures  # noqa: F401

        return True
    except ModuleNotFoundError:
        # Not installed if import went wrong
        return False


def assert_ursa_bbs_signatures_installed():
    """Assert ursa_bbs_signatures module is installed."""
    if not is_ursa_bbs_signatures_module_installed():
        raise Exception("ursa_bbs_signatures module not installed")
