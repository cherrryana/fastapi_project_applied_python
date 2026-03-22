import string
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_current_user_required
from app.cache import (
    cache_get, cache_set, cache_delete,
    link_cache_key, stats_cache_key,
)
from app.database import get_db
from app.models import Link, User
from app.schemas import LinkCreate, LinkUpdate, LinkResponse, LinkStats

router = APIRouter(prefix="/links", tags=["links"])

SHORT_CODE_LENGTH = 6
CHARS = string.ascii_letters + string.digits  # "abcABC...0123456789"


def generate_short_code() -> str:
    """
    Генерирует случайный короткий код из 6 символов
    """
    return "".join(secrets.choice(CHARS) for _ in range(SHORT_CODE_LENGTH))


async def _get_link(
    short_code: str, db: AsyncSession
) -> Link:
    result = await db.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return link


@router.post("/shorten", response_model=LinkResponse, status_code=201)
async def create_link(
    data: LinkCreate,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    if data.custom_alias:
        result = await db.execute(
            select(Link).where(Link.short_code == data.custom_alias)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="This alias is already taken")
        short_code = data.custom_alias
    else:
        for _ in range(10):
            short_code = generate_short_code()
            result = await db.execute(
                select(Link).where(Link.short_code == short_code)
            )
            if not result.scalar_one_or_none():
                break
        else:
            raise HTTPException(status_code=500, detail="Failed to generate code")

    link = Link(
        short_code=short_code,
        original_url=str(data.url),
        user_id=user.id if user else None,
        expires_at=data.expires_at,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    print(f"New link created: {short_code} -> {data.url}")

    return link


@router.get("/search", response_model=list[LinkResponse])
async def search_links(
    original_url: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Link).where(Link.original_url == original_url)
    )
    links = result.scalars().all()
    if not links:
        raise HTTPException(status_code=404, detail="Links not found")
    return links


@router.get("/expired", response_model=list[LinkStats])
async def get_expired_links(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Link).where(
            Link.expires_at != None, 
            Link.expires_at < datetime.now(timezone.utc)
        )
    )
    return result.scalars().all()


@router.get("/{short_code}/stats", response_model=LinkStats)
async def get_link_stats(
    short_code: str,
    db: AsyncSession = Depends(get_db),
):
    cached = await cache_get(stats_cache_key(short_code))
    if cached:
        return LinkStats.model_validate_json(cached)

    link = await _get_link(short_code, db)

    stats = LinkStats.model_validate(link)
    await cache_set(stats_cache_key(short_code), stats.model_dump_json(), ttl=300)
    return stats


@router.get("/{short_code}")
async def redirect_link(
    short_code: str,
    db: AsyncSession = Depends(get_db),
):
    # сначала пробуем достать url из кэша
    cached_url = await cache_get(link_cache_key(short_code))

    # в любом случае нужен объект из бд для обновления счетчика
    link = await _get_link(short_code, db)

    if link.expires_at:
        expires = link.expires_at.replace(tzinfo=None)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if expires < now:
            raise HTTPException(status_code=410, detail="Link expired")

    link.redirect_count += 1
    link.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    # кэшируем если еще не было в кэше
    if not cached_url:
        await cache_set(link_cache_key(short_code), link.original_url, ttl=3600)
    # статистика изменилась, сбрасываем ее кэш
    await cache_delete(stats_cache_key(short_code))

    return RedirectResponse(url=link.original_url, status_code=307)


@router.delete("/{short_code}", status_code=204)
async def delete_link(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    link = await _get_link(short_code, db)
    if link.user_id != user.id:
        raise HTTPException(status_code=403, detail="No rights to delete this link")

    await db.delete(link)
    await db.commit()

    await cache_delete(link_cache_key(short_code))
    await cache_delete(stats_cache_key(short_code))


@router.put("/{short_code}", response_model=LinkResponse)
async def update_link(
    short_code: str,
    data: LinkUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    link = await _get_link(short_code, db)
    if link.user_id != user.id:
        raise HTTPException(status_code=403, detail="No rights to update this link")

    link.original_url = str(data.url)
    await db.commit()
    await db.refresh(link)

    await cache_delete(link_cache_key(short_code))
    await cache_delete(stats_cache_key(short_code))

    return link
