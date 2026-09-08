import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# ---------------------------------------------------------------------------
# Resolve DATABASE_URL to an absolute path for SQLite databases.
#
# The default config uses a *relative* path (sqlite+aiosqlite:///./platform.db)
# which resolves relative to the process CWD at startup time.  When the server
# is started from different directories (project root vs. backend/) it would
# silently create/read different files, causing newly-registered accounts to
# vanish after a restart.  We fix this by replacing any relative SQLite path
# with an absolute path anchored to the `backend/` directory (two levels up
# from this file: backend/app/db/session.py → backend/).
# ---------------------------------------------------------------------------

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # .../backend/

db_url = settings.DATABASE_URL

if "sqlite" in db_url:
    # Normalise legacy bare `sqlite:///` → async scheme first
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite+aiosqlite:"):
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

    # Extract the file path portion after the scheme prefix
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if db_url.startswith(prefix):
            raw_path = db_url[len(prefix):]
            break
    else:
        raw_path = None

    if raw_path is not None and not os.path.isabs(raw_path):
        # Convert relative path to absolute, anchored at the backend directory
        abs_path = str((_BACKEND_DIR / raw_path).resolve())
        db_url = f"sqlite+aiosqlite:///{abs_path}"
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
