from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transactional(session: AsyncSession) -> AsyncGenerator[None, None]:
    """Use the caller's explicit transaction or atomically own a new one."""
    if session.in_transaction():
        yield
        return
    async with session.begin():
        yield
