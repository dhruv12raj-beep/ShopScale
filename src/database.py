from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings

engine = create_async_engine(
    settings.sqlalchemy_url,
    connect_args={"ssl": True},  # Neon requires an encrypted connection
    pool_pre_ping=True,  # helps avoid "server closed the connection unexpectedly" errors
    pool_recycle=300,  # helps avoid "server closed the connection unexpectedly" errors
)   

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Gives each request its own database session, and cleans it up after."""
    async with AsyncSessionLocal() as session:
        yield session