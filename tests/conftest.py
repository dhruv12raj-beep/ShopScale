import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import app


@pytest.fixture
async def db_session():
    """A brand-new in-memory database for each test — every test starts from zero."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",  # in-memory: lives in RAM, vanishes after the test
        poolclass=StaticPool,  # keep ONE connection, or our tables would vanish
        connect_args={"check_same_thread": False},
    )

    # Create tables straight from the models (no Alembic needed for tests)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db_session):
    """An HTTP client that calls our app directly — no server, no port, no Neon."""

    async def override_get_db():
        try:
            yield db_session
        finally:
            await db_session.rollback()  # swap the real database for the test database

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()