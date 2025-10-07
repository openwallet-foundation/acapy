"""Category registry for database managers."""

import logging
from typing import Tuple

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.WARNING)


RELEASE_ORDER = ["release_0", "release_0_1", "release_0_2"]


def load_schema(category: str, version: str) -> dict:
    """Load schema from the  versioned file."""
    try:
        module_path = f"acapy_agent.database_manager.schemas.{category}_v{version}"
        module = __import__(module_path, fromlist=[category])

        schemas = getattr(module, "SCHEMAS", {})
        columns = getattr(module, "COLUMNS", [])
        drop_schemas = getattr(module, "DROP_SCHEMAS", {})

        return {"schemas": schemas, "columns": columns, "drop_schemas": drop_schemas}
    except ImportError as e:
        LOGGER.error(
            "Failed to load schema for category=%s, version=%s: %s",
            category,
            version,
            str(e),
        )
        return {"schemas": {}, "columns": [], "drop_schemas": {}}
    except Exception as e:
        LOGGER.error(
            "Unexpected error loading schema for category=%s, version=%s: %s",
            category,
            version,
            str(e),
        )
        return {"schemas": {}, "columns": [], "drop_schemas": {}}


def load_release(release_number: str) -> dict:
    """Load the release configuration from its module."""
    try:
        module_path = f"acapy_agent.database_manager.releases.{release_number}"
        module = __import__(module_path, fromlist=[release_number])

        release = getattr(module, "RELEASE", {})
        return release
    except ImportError as e:
        LOGGER.error("Failed to load release module %s: %s", release_number, str(e))
        raise ValueError(f"Release module {release_number} not found")
    except Exception as e:
        LOGGER.error(
            "Unexpected error loading release module %s: %s", release_number, str(e)
        )
        raise ValueError(
            f"Unexpected error loading release module {release_number}: {str(e)}"
        )


def get_release(release_number: str, db_type: str = "sqlite") -> Tuple[dict, dict, dict]:
    """Retrieve handlers and schemas for a given release number and database type."""
    if release_number not in RELEASE_ORDER:
        LOGGER.error(
            "Invalid release number: %s, expected one of %s",
            release_number,
            RELEASE_ORDER,
        )
        raise ValueError(f"Release number {release_number} not found")

    release = load_release(release_number)

    handlers = {}
    schemas = {}
    drop_schemas = {}

    if release_number == "release_0":
        default_handler = release["default"]["handlers"].get(db_type)
        if not default_handler:
            LOGGER.error(
                "Database type %s not supported for default handler in release %s",
                db_type,
                release_number,
            )
            raise ValueError(
                f"Database type {db_type} not supported for default handler "
                f"in release {release_number}"
            )
        for category in release:
            handlers[category] = (
                default_handler() if callable(default_handler) else default_handler
            )
            schemas[category] = None
            drop_schemas[category] = None
    else:
        for category, info in release.items():
            if category == "default" and not info["schemas"]:
                handlers[category] = info["handlers"].get(db_type)
                schemas[category] = None
                drop_schemas[category] = None
            else:
                if db_type not in info["handlers"]:
                    LOGGER.error(
                        "Database type %s not supported for category %s in release %s",
                        db_type,
                        category,
                        release_number,
                    )
                    raise ValueError(
                        f"Database type {db_type} not supported for category "
                        f"{category} in release {release_number}"
                    )
                handlers[category] = info["handlers"][db_type]
                schema_list = info["schemas"].get(db_type) if info["schemas"] else None
                schemas[category] = {db_type: schema_list} if schema_list else None
                drop_list = (
                    info["drop_schemas"].get(db_type)
                    if info.get("drop_schemas")
                    else None
                )
                drop_schemas[category] = {db_type: drop_list} if drop_list else None
                if schemas[category] is None and info["schemas"]:
                    LOGGER.warning(
                        "No schema found for category=%s, db_type=%s, "
                        "despite schemas being defined: %s",
                        category,
                        db_type,
                        info["schemas"],
                    )

    return handlers, schemas, drop_schemas
