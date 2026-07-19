from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError


class BaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_raise(self, model, entity_id: UUID):
        entity = await self.session.get(model, entity_id)
        if entity is None:
            raise NotFoundError(f"{model.__name__} {entity_id} was not found")
        return entity

    async def get_locked_or_raise(self, model, entity_id: UUID):
        entity = await self.session.scalar(
            select(model).where(model.id == entity_id).with_for_update()
        )
        if entity is None:
            raise NotFoundError(f"{model.__name__} {entity_id} was not found")
        return entity

