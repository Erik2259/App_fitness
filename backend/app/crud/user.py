import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import Usuario
from app.schemas.user import UsuarioCreate, UsuarioUpdate


async def get(db: AsyncSession, usuario_id: uuid.UUID) -> Usuario | None:
    return await db.get(Usuario, usuario_id)


async def get_by_email(db: AsyncSession, email: str) -> Usuario | None:
    result = await db.execute(select(Usuario).where(Usuario.email == email))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, data: UsuarioCreate) -> Usuario:
    usuario = Usuario(
        email=data.email,
        password_hash=hash_password(data.password),
        nombre=data.nombre,
        fecha_nacimiento=data.fecha_nacimiento,
        sexo=data.sexo,
        altura_cm=data.altura_cm,
        peso_kg=data.peso_kg,
        fc_maxima=data.fc_maxima,
        fc_reposo=data.fc_reposo,
        ftp_running_watts=data.ftp_running_watts,
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def update(db: AsyncSession, usuario: Usuario, data: UsuarioUpdate) -> Usuario:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(usuario, field, value)
    await db.commit()
    await db.refresh(usuario)
    return usuario
