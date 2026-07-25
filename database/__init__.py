"""
database/

Generic, multi-dialect database connection layer for the Agentic SQL
Assistant. Currently exposes the connection layer; the Schema Agent will
add a schema_inspector module here in a later step.
"""

from .connection import (
    DEFAULT_PORTS,
    DIALECT_DRIVERS,
    SUPPORTED_DB_TYPES,
    DatabaseConfig,
    DatabaseManager,
)

__all__ = [
    "DatabaseConfig",
    "DatabaseManager",
    "DIALECT_DRIVERS",
    "DEFAULT_PORTS",
    "SUPPORTED_DB_TYPES",
]
