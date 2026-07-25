"""
database/connection.py

Generic, dialect-agnostic database connection layer built on SQLAlchemy.

This replaces the PostgreSQL-only connection logic that used to live inline
in app.py (psycopg2 + a single hardcoded URI). Everything downstream
(Schema Agent, SQL Generator, Execution Agent) will depend on this module
instead of talking to a specific driver directly.

Adding a new database dialect later = adding one entry to DIALECT_DRIVERS.
No other code in the project should need to change.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


# Human-readable database type -> SQLAlchemy dialect+driver string.
DIALECT_DRIVERS = {
    "PostgreSQL": "postgresql+psycopg2",
    "MySQL": "mysql+mysqlconnector",
    "MariaDB": "mysql+pymysql",
    "SQL Server": "mssql+pyodbc",
    "SQLite": "sqlite",
}


DEFAULT_PORTS = {
    "PostgreSQL": 5432,
    "MySQL": 3306,
    "MariaDB": 3306,
    "SQL Server": 1433,
    "SQLite": None,
}

SUPPORTED_DB_TYPES = list(DIALECT_DRIVERS.keys())


@dataclass
class DatabaseConfig:
    """Connection parameters for a single database.

    For SQLite, `database` is treated as a file path and host/port/
    username/password are ignored.
    """

    db_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

    def build_uri(self) -> str:
        """Builds a SQLAlchemy connection URI for the configured dialect.

        Raises:
            ValueError: if the db_type is unsupported or required fields
                are missing.
        """
        if self.db_type not in DIALECT_DRIVERS:
            raise ValueError(
                f"Unsupported database type: '{self.db_type}'. "
                f"Supported types: {SUPPORTED_DB_TYPES}"
            )

        driver = DIALECT_DRIVERS[self.db_type]

        if self.db_type == "SQLite":
            if not self.database:
                raise ValueError("SQLite requires a file path in 'database'.")
            print(self.database)
            return f"{driver}:///{self.database}"

        missing = [
            name
            for name, value in (
                ("host", self.host),
                ("port", self.port),
                ("username", self.username),
                ("database", self.database),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"{self.db_type} connection is missing required field(s): "
                f"{', '.join(missing)}"
            )

        extra = ""
        if self.db_type == "SQL Server":
            extra = "?driver=ODBC+Driver+18+for+SQL+Server"

        username = quote_plus(self.username)
        password = quote_plus(self.password)

        print("Host:", self.host)
        print("Port:", self.port)
        print("Database:", self.database)
        print("Username:", self.username)

        return (
            f"{driver}://{username}:{password}"
            f"@{self.host}:{self.port}/{self.database}{extra}"
        )
    


class DatabaseManager:
    """Owns the SQLAlchemy engine and LangChain SQLDatabase wrapper for one
    active connection.

    One instance is created per connection (e.g. stored in
    st.session_state) and reused across the app until the user disconnects
    or reconnects.
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine: Optional[Engine] = None
        self._sql_database: Optional[SQLDatabase] = None

    def connect(self) -> SQLDatabase:
        """Creates the engine, verifies connectivity, and wraps it as a
        LangChain SQLDatabase.

        Returns:
            The connected SQLDatabase instance.

        Raises:
            ValueError: if the config is incomplete/invalid.
            SQLAlchemyError: if the database cannot be reached.
        """
        uri = self.config.build_uri()
        print(uri)
        logger.info(
            "Connecting to %s database '%s'", self.config.db_type, self.config.database
        )

        engine = create_engine(uri, pool_pre_ping=True)

        # Fail fast with a clear error instead of letting a broken
        # connection surface deep inside an agent later on.
        try:
            with engine.connect():
                pass
        except SQLAlchemyError as exc:
            logger.error("Connection to %s failed: %s", self.config.db_type, exc)
            engine.dispose()
            raise

        self._engine = engine
        self._sql_database = SQLDatabase(engine)
        logger.info("Connected successfully to %s.", self.config.db_type)
        return self._sql_database

    def disconnect(self) -> None:
        """Disposes of the engine and clears cached connection objects."""
        if self._engine is not None:
            self._engine.dispose()
            logger.info("Disconnected from %s database.", self.config.db_type)
        self._engine = None
        self._sql_database = None

    @property
    def is_connected(self) -> bool:
        return self._engine is not None

    @property
    def engine(self) -> Optional[Engine]:
        return self._engine

    @property
    def sql_database(self) -> Optional[SQLDatabase]:
        return self._sql_database

    def test_connection(self) -> Tuple[bool, str]:
        """Attempts a throwaway connection without mutating this manager's
        state. Useful for a 'Test Connection' button before committing.

        Returns:
            (success, message) tuple.
        """
        try:
            uri = self.config.build_uri()
            print(uri)
        except ValueError as exc:
            return False, str(exc)

        try:
            engine = create_engine(uri, pool_pre_ping=True)
            with engine.connect():
                pass
            engine.dispose()
            return True, f"Successfully connected to {self.config.db_type}."
        except SQLAlchemyError as exc:
            return False, str(exc)