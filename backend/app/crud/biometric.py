import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.biometric import MetricaBiometrica
from app.schemas.biometric import MetricaBiometricaCreate, MetricaBiometricaUpdate


async def get_by_fecha(
    db: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> MetricaBiometrica | None:
    result = await db.execute(
        select(MetricaBiometrica).where(
            MetricaBiometrica.usuario_id == usuario_id,
            MetricaBiometrica.fecha == fecha,
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession, usuario_id: uuid.UUID, data: MetricaBiometricaCreate
) -> MetricaBiometrica:
    metrica = MetricaBiometrica(usuario_id=usuario_id, **data.model_dump())
    db.add(metrica)
    await db.commit()
    await db.refresh(metrica)
    return metrica


async def update(
    db: AsyncSession, metrica: MetricaBiometrica, data: MetricaBiometricaUpdate
) -> MetricaBiometrica:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(metrica, field, value)
    await db.commit()
    await db.refresh(metrica)
    return metrica


async def list_for_user(
    db: AsyncSession,
    usuario_id: uuid.UUID,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    limit: int = 365,
) -> list[MetricaBiometrica]:
    stmt = select(MetricaBiometrica).where(MetricaBiometrica.usuario_id == usuario_id)
    if desde is not None:
        stmt = stmt.where(MetricaBiometrica.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(MetricaBiometrica.fecha <= hasta)
    stmt = stmt.order_by(MetricaBiometrica.fecha.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
