# encoders/factory.py
from .sqlite_encoder import SqliteTagEncoder
from .postgres_encoder import PostgresTagEncoder
from .mongo_encoder import MongoTagEncoder
from .mssql_encoder import MssqlTagEncoder

def get_encoder(db_type: str, enc_name, enc_value):
    """
    Returns an encoder object based on the database type.

    Args:
        db_type (str): The type of database (e.g., 'sqlite', 'postgresql', 'mongodb', 'mssql').
        enc_name (callable): Function to encode tag names.
        enc_value (callable): Function to encode tag values.

    Returns:
        TagQueryEncoder: An instance of the appropriate encoder class.

    Raises:
        ValueError: If the database type is not supported.
    """
    encoders = {
        'sqlite': SqliteTagEncoder,
        'postgresql': PostgresTagEncoder,
        'mongodb': MongoTagEncoder,
        'mssql': MssqlTagEncoder,
    }
    encoder_class = encoders.get(db_type.lower())
    if encoder_class is None:
        raise ValueError(f"Unsupported database type: {db_type}")
    return encoder_class(enc_name, enc_value)