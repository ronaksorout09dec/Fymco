import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["ADVANCE_JOB_ENABLED"] = "false"

from app.db.base import Base
import app.models.entities  # noqa: E402,F401


@pytest_asyncio.fixture
async def session_factory(tmp_path) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as current_session:
        yield current_session
