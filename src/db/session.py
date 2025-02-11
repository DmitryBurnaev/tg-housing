import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config.app import DATABASE_URL

logger = logging.getLogger(__name__)


def make_sa_session() -> AsyncSession:
    """
    Create a new SQLAlchemy session for connection to SQLite database.
    """
    logger.debug("Creating new async SQLAlchemy session")
    try:
        engine = create_async_engine(DATABASE_URL)
        logger.debug("Successfully created async engine")
        return AsyncSession(engine)
    except Exception as e:
        logger.error("Failed to create async session: %s", str(e))
        raise
