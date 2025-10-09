"""Module docstring."""

from .postgres_encoder import PostgresTagEncoder
from .sqlite_encoder import SqliteTagEncoder


def get_encoder(
    db_type: str,
    enc_name,
    enc_value,
    normalized: bool = False,
    tags_table: str = "items_tags",
):
    """Returns an encoder object based on the database type.

    Args:
        db_type (str): The type of database (e.g., 'sqlite', 'postgresql',
            'mongodb', 'mssql').
        enc_name (callable): Function to encode tag names.
        enc_value (callable): Function to encode tag values.
        normalized (bool): Flag to indicate if the encoder should use normalized
            mode (default: False).
        tags_table (str): Name of the tags table for non-normalized mode
            (default: 'items_tags'). Ignored in normalized mode.

    Returns:
        TagQueryEncoder: An instance of the appropriate encoder class.

    Raises:
        ValueError: If the database type is not supported.

    """
    encoders = {
        "sqlite": SqliteTagEncoder,
        "postgresql": PostgresTagEncoder,
    }
    encoder_class = encoders.get(db_type.lower())
    if encoder_class is None:
        raise ValueError(f"Unsupported database type: {db_type}")
    return encoder_class(enc_name, enc_value, normalized, tags_table=tags_table)
