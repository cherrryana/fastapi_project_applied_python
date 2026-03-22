import string
import pytest
from jose import jwt

from app.auth import hash_password, verify_password, create_access_token
from app.config import SECRET_KEY, ALGORITHM
from app.routers.links import generate_short_code, SHORT_CODE_LENGTH
from app.cache import link_cache_key, stats_cache_key, cache_get, cache_set, cache_delete

from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from tests.conftest import test_session_factory
from app.models import Link
from app.main import cleanup_unused_links

def test_short_code_length():
    """
    Код должен быть ровно 6 символов
    """
    code = generate_short_code()
    assert len(code) == SHORT_CODE_LENGTH

def test_short_code_characters():
    """
    Код состоит только из букв и цифр
    """
    code = generate_short_code()
    allowed = string.ascii_letters + string.digits
    for char in code:
        assert char in allowed


def test_short_code_unique():
    """
    Два вызова дают разные коды
    """
    codes = {generate_short_code() for _ in range(50)}
    assert len(codes) > 1


def test_hash_password_not_plain():
    """
    Хэш не должен совпадать с исходным паролем
    """
    password = "privet2026"
    hashed = hash_password(password)
    assert hashed != password


def test_verify_password_correct():
    password = "privet2026"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True

def test_verify_password_wrong():
    hashed = hash_password("correct_password")
    assert verify_password("wrong_password", hashed) is False


def test_create_access_token():
    token = create_access_token({"sub": "42"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "42"
    assert "exp" in payload

def test_link_cache_key():
    assert link_cache_key("abc123") == "link:abc123"


def test_stats_cache_key():
    assert stats_cache_key("abc123") == "stats:abc123"


@pytest.mark.asyncio
async def test_cache_get_without_redis():
    """
    cache_get возвращает None если Redis не подключен
    """
    result = await cache_get("anything")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_without_redis():
    """
    cache_set не падает без Redis
    """
    await cache_set("key", "value") # просто не должно быть ошибки

@pytest.mark.asyncio
async def test_cache_delete_without_redis():
    """
    cache_delete не падает без Redis
    """
    await cache_delete("key") # просто не должно быть ошибки


@pytest.mark.asyncio
async def test_cleanup_unused_links():
    # создаем ссылку с очень старой датой
    async with test_session_factory() as db:
        old_link = Link(
            short_code="oldlink",
            original_url="https://stepik.org/s",
            created_at=datetime.now(timezone.utc) - timedelta(days=365),
        )
        db.add(old_link)
        await db.commit()

    # запускаем очистку
    await cleanup_unused_links()

    # проверяем что ссылка удалена
    async with test_session_factory() as db:
        result = await db.execute(select(Link).where(Link.short_code == "oldlink"))
        assert result.scalar_one_or_none() is None
