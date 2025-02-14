import logging
import contextlib
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from src.config.app import DATABASE_URL, DATABASE_URL_ASYNC

logger = logging.getLogger(__name__)


def make_sa_session() -> AsyncSession:
    """
    Create a new SQLAlchemy session for connection to SQLite database.
    """
    logger.debug("Creating new async SQLAlchemy session")
    try:
        engine = create_async_engine(DATABASE_URL_ASYNC)
        logger.debug("Successfully created async engine")
        return AsyncSession(engine)
    except Exception as e:
        logger.error("Failed to create async session: %s", str(e))
        raise


@contextlib.asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Simple context manager that creates a new session for SQLAlchemy."""
    session = make_sa_session()
    try:
        yield session
    finally:
        await session.close()
        logger.debug("Session closed")


def create_tables() -> None:
    """Simple helper function to create all tables (no using alembic yet)"""
    logger.debug("Creating all tables for DB %s", DATABASE_URL)
    engine = create_engine(DATABASE_URL)
    SQLModel.metadata.create_all(engine)
    logger.info("Successfully created all tables for DB %s", DATABASE_URL)
