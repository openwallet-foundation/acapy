"""Module docstring."""

# encoders/factory.py
from acapy_agent.database_manager.wql_normalized.encoders.postgres_encoder import (
    PostgresTagEncoder,
)

from .mongo_encoder import MongoTagEncoder
from .sqlite_encoder import SqliteTagEncoder


def get_encoder(db_type: str, enc_name, enc_value):
    """Returns an encoder object based on the database type.

    Args:
        db_type (str): The type of database (e.g., 'sqlite', 'postgresql', 'mongodb').
        enc_name (callable): Function to encode tag names.
        enc_value (callable): Function to encode tag values.

    Returns:
        TagQueryEncoder: An instance of the appropriate encoder class.

    Raises:
        ValueError: If the database type is not supported.

    """
    encoders = {
        "sqlite": SqliteTagEncoder,
        "postgresql": PostgresTagEncoder,
        "mongodb": MongoTagEncoder,
    }
    encoder_class = encoders.get(db_type.lower())
    if encoder_class is None:
        raise ValueError(f"Unsupported database type: {db_type}")
    return encoder_class(enc_name, enc_value)
