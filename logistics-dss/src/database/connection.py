"""
Database Connection Manager
Handles SQLite database connections with proper session management.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from src.database.models import Base
from src.logger import LoggerMixin, get_logger

logger = get_logger(__name__)


class DatabaseManager(LoggerMixin):
    """Manages database connections and session lifecycle."""

    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        """Singleton pattern for database manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database connection."""
        if DatabaseManager._engine is None:
            self._initialize_engine()

    def _initialize_engine(self):
        """Create SQLAlchemy engine and session factory."""
        db_path = settings.DATABASE_PATH
        self.logger.info(f"Initializing database at: {db_path}")

        # Create engine with SQLite settings
        DatabaseManager._engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={
                "check_same_thread": False,
                "timeout": settings.SQLITE_TIMEOUT
            },
            echo=False
        )

        # Enable foreign keys for SQLite
        @event.listens_for(DatabaseManager._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create session factory
        DatabaseManager._session_factory = sessionmaker(
            bind=DatabaseManager._engine,
            autocommit=False,
            autoflush=False
        )

        self.logger.info("Database engine initialized")

    def create_tables(self):
        """Create all database tables."""
        self.logger.info("Creating database tables")
        Base.metadata.create_all(DatabaseManager._engine)
        self.logger.info("Database tables created successfully")

    def drop_tables(self):
        """Drop all database tables (use with caution)."""
        self.logger.warning("Dropping all database tables")
        Base.metadata.drop_all(DatabaseManager._engine)
        self.logger.info("Database tables dropped")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.

        Usage:
            with db_manager.get_session() as session:
                session.add(record)

        Yields:
            SQLAlchemy Session instance
        """
        session = DatabaseManager._session_factory()
        try:
            yield session
            session.commit()
            self.logger.debug("Session committed successfully")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Session rolled back due to error: {e}")
            raise
        finally:
            session.close()

    def get_engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        return DatabaseManager._engine

    def reset(self):
        """Reset the database manager (useful for testing)."""
        if DatabaseManager._engine:
            DatabaseManager._engine.dispose()
        DatabaseManager._engine = None
        DatabaseManager._session_factory = None
        DatabaseManager._instance = None


def get_db_manager() -> DatabaseManager:
    """Get the database manager instance."""
    return DatabaseManager()
