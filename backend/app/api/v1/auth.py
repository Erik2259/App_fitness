from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, verify_password
from app.crud import user as crud_user
from app.schemas.auth import Token
from app.schemas.user import UsuarioCreate, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def register(data: UsuarioCreate, db: DbSession) -> UsuarioOut:
    """Registra un nuevo atleta. El email debe ser único."""
    if await crud_user.get_by_email(db, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email.",
        )
    return await crud_user.create(db, data)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    """Autentica con email (campo `username`) y contraseña; devuelve un JWT."""
    usuario = await crud_user.get_by_email(db, form_data.username)
    if usuario is None or not verify_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=str(usuario.id))
    return Token(access_token=token)


@router.get("/me", response_model=UsuarioOut)
async def me(current_user: CurrentUser) -> UsuarioOut:
    """Devuelve el perfil del usuario autenticado."""
    return current_user
