"""
Classes for storing data in the Indy wallet
"""

from .base import BaseStorage, BaseStorageRecordSearch
from .error import StorageException, StorageNotFoundException, StorageSearchException
from .record import StorageRecord
