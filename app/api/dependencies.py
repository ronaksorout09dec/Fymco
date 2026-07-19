from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.db.session import get_session

DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


async def require_internal_key(
    x_internal_api_key: Annotated[str | None, Header()] = None,
) -> None:
    if x_internal_api_key != get_settings().internal_api_key:
        raise UnauthorizedError("Valid X-Internal-API-Key header required")


InternalAccess = Annotated[None, Depends(require_internal_key)]
