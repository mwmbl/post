"""Database connection and session management."""

from contextlib import contextmanager
from typing import Generator

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings
from .models import Base


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self) -> None:
        """Initialize the database manager."""
        self.engine = create_engine(
            settings.database_url,
            echo=settings.log_level.upper() == "DEBUG",
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_tables(self) -> None:
        """Create all database tables."""
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")

    def drop_tables(self) -> None:
        """Drop all database tables."""
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped successfully")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()


# Global database manager instance
db_manager = DatabaseManager()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Convenience function to get a database session."""
    with db_manager.get_session() as session:
        yield session
