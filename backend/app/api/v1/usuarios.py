from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.crud import user as crud_user
from app.schemas.user import UsuarioOut, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("/me", response_model=UsuarioOut)
async def get_me(current_user: CurrentUser) -> UsuarioOut:
    """Perfil del atleta autenticado."""
    return current_user


@router.patch("/me", response_model=UsuarioOut)
async def update_me(data: UsuarioUpdate, current_user: CurrentUser, db: DbSession) -> UsuarioOut:
    """Actualiza (parcialmente) el perfil y los datos fisiológicos del atleta."""
    return await crud_user.update(db, current_user, data)
