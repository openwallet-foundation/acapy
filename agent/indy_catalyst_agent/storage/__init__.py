"""
Classes for storing data in the Indy wallet
"""

from .base import BaseStorage, BaseStorageRecordSearch
from .error import StorageError, StorageNotFoundError, StorageSearchError
from .record import StorageRecord
