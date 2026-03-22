import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "service" in resp.json()

@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={"username": "katya", "password": "password123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "katya"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient):
    await client.post("/auth/register", json={"username": "masha", "password": "masha2026"})
    resp = await client.post("/auth/register", json={"username": "masha", "password": "masha2026"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post("/auth/register", json={"username": "dima", "password": "dimapass1"})
    resp = await client.post("/auth/login", data={"username": "dima", "password": "dimapass1"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/register", json={"username": "sasha", "password": "realpass"})
    resp = await client.post("/auth/login", data={"username": "sasha", "password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/auth/login", data={"username": "nikto", "password": "net"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_request_with_invalid_token(client: AsyncClient):
    resp = await client.post(
        "/links/shorten",
        json={"url": "https://example.com"},
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    # ссылка создастся анонимно, токен просто проигнорируется
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_link_anonymous(client: AsyncClient):
    resp = await client.post(
        "/links/shorten",
        json={"url": "https://example.com"},
    )
    assert resp.status_code == 201
    assert "short_code" in resp.json()


@pytest.mark.asyncio
async def test_create_link_authenticated(client: AsyncClient, auth_header: dict):
    resp = await client.post(
        "/links/shorten",
        json={"url": "https://example.com"},
        headers=auth_header,
    )
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_create_link_custom_alias(client: AsyncClient):
    resp = await client.post(
        "/links/shorten",
        json={"url": "https://example.com", "custom_alias": "myalias"},
    )
    assert resp.status_code == 201
    assert resp.json()["short_code"] == "myalias"


@pytest.mark.asyncio
async def test_create_link_duplicate_alias(client: AsyncClient):
    await client.post("/links/shorten", json={"url": "https://github.com", "custom_alias": "taken"})
    resp = await client.post("/links/shorten", json={"url": "https://ya.ru", "custom_alias": "taken"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_link_invalid_url(client: AsyncClient):
    resp = await client.post("/links/shorten", json={"url": "not-a-url"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_link_with_expiration(client: AsyncClient):
    future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    resp = await client.post(
        "/links/shorten",
        json={"url": "https://example.com", "expires_at": future},
    )
    assert resp.status_code == 201
    assert resp.json()["expires_at"] is not None


@pytest.mark.asyncio
async def test_redirect(client: AsyncClient):
    """
    Переход по короткой ссылке -> 307
    """
    await client.post("/links/shorten", json={"url": "https://example.com", "custom_alias": "go"})
    resp = await client.get("/links/go")
    assert resp.status_code == 307
    assert "example.com" in resp.headers["location"]

@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    resp = await client.get("/links/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_redirect_expired(client: AsyncClient):
    """
    Истекшая ссылка -> 410
    """
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    await client.post(
        "/links/shorten",
        json={"url": "https://example.com", "custom_alias": "old", "expires_at": past},
    )
    resp = await client.get("/links/old")
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_redirect_increments_counter(client: AsyncClient):
    await client.post("/links/shorten", json={"url": "https://example.com", "custom_alias": "cnt"})

    # делаем 3 перехода по ссылке
    await client.get("/links/cnt")
    await client.get("/links/cnt")
    await client.get("/links/cnt")

    stats = await client.get("/links/cnt/stats")
    assert stats.json()["redirect_count"] == 3


@pytest.mark.asyncio
async def test_stats(client: AsyncClient):
    await client.post("/links/shorten", json={"url": "https://example.com", "custom_alias": "st"})
    resp = await client.get("/links/st/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["redirect_count"] == 0
    assert data["original_url"] == "https://example.com/"

@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    resp = await client.get("/links/nope/stats")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search(client: AsyncClient):
    await client.post("/links/shorten", json={"url": "https://hse.ru/about"})
    resp = await client.get("/links/search", params={"original_url": "https://hse.ru/about"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_search_not_found(client: AsyncClient):
    resp = await client.get("/links/search", params={"original_url": "https://notexist.xyz/"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_expired_links(client: AsyncClient):
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    await client.post(
        "/links/shorten",
        json={"url": "https://vk.com/music", "custom_alias": "exp", "expires_at": past},
    )
    resp = await client.get("/links/expired")
    assert resp.status_code == 200
    codes = [link["short_code"] for link in resp.json()]
    assert "exp" in codes


@pytest.mark.asyncio
async def test_expired_links_empty(client: AsyncClient):
    """
    Если нет истекших, то список пустой
    """
    resp = await client.get("/links/expired")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_update_link(client: AsyncClient, auth_header: dict):
    await client.post(
        "/links/shorten",
        json={"url": "https://youtube.com/watch?v=123", "custom_alias": "upd"},
        headers=auth_header,
    )
    resp = await client.put(
        "/links/upd",
        json={"url": "https://habr.com/ru/articles"},
        headers=auth_header,
    )
    assert resp.status_code == 200
    assert "habr.com" in resp.json()["original_url"]

@pytest.mark.asyncio
async def test_update_link_no_auth(client: AsyncClient):
    """
    Без авторизации -> 401
    """
    await client.post("/links/shorten", json={"url": "https://stackoverflow.com", "custom_alias": "noauth"})
    resp = await client.put("/links/noauth", json={"url": "https://reddit.com"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_link_wrong_user(client: AsyncClient, auth_header: dict):
    """
    Чужая ссылка -> 403
    """
    # создаем ссылку анонимно (user_id = None)
    await client.post("/links/shorten", json={"url": "https://t.me/durov", "custom_alias": "foreign"})
    resp = await client.put(
        "/links/foreign",
        json={"url": "https://vk.com"},
        headers=auth_header,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_link_not_found(client: AsyncClient, auth_header: dict):
    resp = await client.put(
        "/links/ghost",
        json={"url": "https://b.com"},
        headers=auth_header,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_link(client: AsyncClient, auth_header: dict):
    await client.post(
        "/links/shorten",
        json={"url": "https://pikabu.ru", "custom_alias": "bye"},
        headers=auth_header,
    )
    resp = await client.delete("/links/bye", headers=auth_header)
    assert resp.status_code == 204

    resp = await client.get("/links/bye/stats")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_no_auth(client: AsyncClient):
    await client.post("/links/shorten", json={"url": "https://twitch.tv", "custom_alias": "nodelete"})
    resp = await client.delete("/links/nodelete")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_wrong_user(client: AsyncClient, auth_header: dict):
    """
    Удаление чужой ссылки -> 403
    """
    await client.post("/links/shorten", json={"url": "https://spotify.com", "custom_alias": "notmine"})
    resp = await client.delete("/links/notmine", headers=auth_header)
    assert resp.status_code == 403
