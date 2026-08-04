import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import get_settings
from app.database.session import normalize_database_url

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    settings = get_settings()
    engine = create_async_engine(normalize_database_url(str(settings.alembic_database_url)))
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE alembic_version SET version_num='20260802_0001'"))
    await engine.dispose()

asyncio.run(main())
