import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from sqlalchemy import delete

from app.cache import init_redis, close_redis
from app.config import UNUSED_DAYS_LIMIT, CLEANUP_INTERVAL_SECONDS
from app.database import engine, async_session, Base
from app.models import Link
from app.routers import auth, links


async def cleanup_unused_links() -> None:
    """
    Удаляет ссылки, не использованные более UNUSED_DAYS_LIMIT дней
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=UNUSED_DAYS_LIMIT)
    async with async_session() as db:
        await db.execute(
            delete(Link).where(
                # удаляем если last_used_at < cutoff ИЛИ
                # если ссылку ни разу не использовали и она создана давно
                (Link.last_used_at != None) & (Link.last_used_at < cutoff)
                | (Link.last_used_at == None) & (Link.created_at < cutoff)
            )
        )
        await db.commit()


async def periodic_cleanup() -> None:
    """
    Периодическая очистка неиспользуемых ссылок
    """
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        await cleanup_unused_links()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await init_redis()
    await cleanup_unused_links()
    task = asyncio.create_task(periodic_cleanup())
    print("Link shortener is up and running!")

    yield

    task.cancel()
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="Link shortener",
    description="HSE applied python homework: URL shortener service",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(links.router)


@app.get("/")
async def root():
    return {
        "service": "Link shortener",
        "docs": "/docs",
        "tip": "try POST /links/shorten to create your first short link!",
    }
