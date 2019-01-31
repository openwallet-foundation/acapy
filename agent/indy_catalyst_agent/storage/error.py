"""
Storage-related exceptions
"""

class StorageException(Exception):
    """
    Base class for Storage errors
    """

class StorageNotFoundException(StorageException):
    """
    Record not found in storage
    """

class StorageSearchException(StorageException):
    """
    General exception during record search
    """
