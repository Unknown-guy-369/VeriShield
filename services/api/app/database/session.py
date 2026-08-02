from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def normalize_database_url(url: str) -> str:
    normalized = url.strip()
    if normalized.startswith("postgresql://"):
        normalized = normalized.replace("postgresql://", "postgresql+psycopg://", 1)
    elif normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql+psycopg://", 1)

    parsed = make_url(normalized)
    if "pgbouncer" in parsed.query:
        # This flag is emitted by some Node/Prisma connection snippets. psycopg
        # rejects it, while Supabase selects the pooler mode from host and port.
        compatible_query = {
            key: value for key, value in parsed.query.items() if key != "pgbouncer"
        }
        parsed = parsed.set(query=compatible_query)
    return parsed.render_as_string(hide_password=False)


def is_supabase_transaction_pooler(url: str) -> bool:
    parsed: URL = make_url(normalize_database_url(url))
    return bool(
        parsed.host
        and parsed.host.endswith(".pooler.supabase.com")
        and parsed.port == 6543
    )


class Database:
    def __init__(self, url: str) -> None:
        normalized_url = normalize_database_url(url)
        connect_args: dict[str, object] = {}
        if is_supabase_transaction_pooler(normalized_url):
            # Supabase transaction pooling does not support prepared statements.
            connect_args["prepare_threshold"] = None
        self.engine: AsyncEngine = create_async_engine(
            normalized_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        await self.engine.dispose()
