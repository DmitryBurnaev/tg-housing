from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.config.app import DATABASE_URL


def make_sa_session() -> AsyncSession:
    """
    Create a new SQLAlchemy session. for connection to SQLite database.
    """
    engine = create_async_engine(DATABASE_URL)
    return AsyncSession(engine)
