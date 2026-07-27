"""Dependencias reutilizables de FastAPI: sesión de BD y usuario autenticado."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.crud import user as crud_user
from app.db.session import get_db
from app.models.user import Usuario

settings = get_settings()

# tokenUrl apunta al endpoint de login; Swagger lo usa para el botón "Authorize".
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> Usuario:
    """Resuelve el usuario autenticado a partir del JWT del header Authorization."""
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    subject = decode_access_token(token)
    if subject is None:
        raise credenciales_invalidas

    try:
        usuario_id = uuid.UUID(subject)
    except ValueError:
        raise credenciales_invalidas

    usuario = await crud_user.get(db, usuario_id)
    if usuario is None or not usuario.activo:
        raise credenciales_invalidas
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]
