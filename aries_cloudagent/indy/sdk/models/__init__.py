"""Indy-SDK code and data."""

from os import environ

UNENCRYPTED_TAGS = environ.get("EXCH_UNENCRYPTED_TAGS", "False").upper() == "TRUE"
