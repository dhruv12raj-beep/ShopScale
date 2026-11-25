import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.models import User
from src.database import Base, get_db
from src.main import app

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpass123"


@pytest.fixture
async def db_session():
    """A brand-new in-memory database for each test — every test starts from zero."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
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
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_headers(client, db_session):
    """A logged-in admin. The first admin can't be created through the API
    (chicken-and-egg), so we promote directly in the database — exactly
    what make_admin.py does on the real server."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    user = await db_session.scalar(select(User).where(User.email == ADMIN_EMAIL))
    user.is_admin = True
    await db_session.commit()
    token = (
        await client.post(
            "/api/v1/auth/login",
            data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def create_product(client, admin_headers):
    """Create a product — as an admin, because now only admins can."""

    async def _create(stock=5, price="10.00", name="Mouse"):
        response = await client.post(
            "/api/v1/products",
            json={"name": name, "price": price, "stock": stock},
            headers=admin_headers,
        )
        return response.json()["id"]

    return _create