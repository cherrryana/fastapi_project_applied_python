import os

# подменяем переменные окружения ДО импорта приложения,
# чтобы config.py подхватил тестовые значения
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base, get_db
from app.main import app

# тестовая БД SQLite в файле (файл проще для дебага)
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

async def override_get_db():
    async with test_session_factory() as session:
        yield session

# говорим FastAPI использовать нашу тестовую БД
app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_header(client: AsyncClient) -> dict:
    """
    Регистрирует тестового юзера, логинится и возвращает заголовок авторизации
    """
    # регистрация
    await client.post(
        "/auth/register",
        json={"username": "testuser", "password": "testpass123"},
    )
    # логин
    resp = await client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass123"},
    )
    token = resp.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}
