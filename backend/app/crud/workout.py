import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workout import Entrenamiento
from app.schemas.workout import EntrenamientoCreate


async def create(
    db: AsyncSession, usuario_id: uuid.UUID, data: EntrenamientoCreate
) -> Entrenamiento:
    entrenamiento = Entrenamiento(usuario_id=usuario_id, **data.model_dump())
    db.add(entrenamiento)
    await db.commit()
    await db.refresh(entrenamiento)
    return entrenamiento


async def get(
    db: AsyncSession, usuario_id: uuid.UUID, entrenamiento_id: uuid.UUID
) -> Entrenamiento | None:
    result = await db.execute(
        select(Entrenamiento).where(
            Entrenamiento.id == entrenamiento_id,
            Entrenamiento.usuario_id == usuario_id,
        )
    )
    return result.scalar_one_or_none()


async def exists_by_start(
    db: AsyncSession, usuario_id: uuid.UUID, fecha_inicio: datetime
) -> bool:
    """True si ya hay un entrenamiento del usuario con ese instante de inicio.

    Se usa para que reimportar el mismo export no duplique sesiones.
    """
    result = await db.execute(
        select(Entrenamiento.id).where(
            Entrenamiento.usuario_id == usuario_id,
            Entrenamiento.fecha_inicio == fecha_inicio,
        )
    )
    return result.first() is not None


async def list_for_user(
    db: AsyncSession,
    usuario_id: uuid.UUID,
    *,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limit: int = 100,
) -> list[Entrenamiento]:
    stmt = select(Entrenamiento).where(Entrenamiento.usuario_id == usuario_id)
    if desde is not None:
        stmt = stmt.where(Entrenamiento.fecha_inicio >= desde)
    if hasta is not None:
        stmt = stmt.where(Entrenamiento.fecha_inicio <= hasta)
    stmt = stmt.order_by(Entrenamiento.fecha_inicio.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
