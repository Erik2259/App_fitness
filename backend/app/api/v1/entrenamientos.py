import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.crud import workout as crud_workout
from app.schemas.workout import EntrenamientoCreate, EntrenamientoOut
from app.services.carga import compute_trimp

router = APIRouter(prefix="/entrenamientos", tags=["entrenamientos"])


@router.post("", response_model=EntrenamientoOut, status_code=status.HTTP_201_CREATED)
async def crear_entrenamiento(
    data: EntrenamientoCreate, current_user: CurrentUser, db: DbSession
) -> EntrenamientoOut:
    """Registra una sesión de HealthKit y calcula su TRIMP (Fase 2) en el acto.

    El TRIMP se computa en el backend a partir de la FC de la sesión y los datos
    fisiológicos base del usuario; el cliente no lo envía.
    """
    entrenamiento = await crud_workout.create(db, current_user.id, data)

    trimp = compute_trimp(
        fc_promedio=entrenamiento.fc_promedio,
        duracion_segundos=entrenamiento.duracion_segundos,
        fc_maxima_usuario=current_user.fc_maxima,
        fc_reposo_usuario=current_user.fc_reposo,
        sexo=current_user.sexo,
    )
    if trimp is not None:
        entrenamiento.trimp = trimp
        await db.commit()
        await db.refresh(entrenamiento)

    return entrenamiento


@router.get("", response_model=list[EntrenamientoOut])
async def listar_entrenamientos(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[EntrenamientoOut]:
    """Lista las sesiones del atleta, de la más reciente a la más antigua."""
    return await crud_workout.list_for_user(db, current_user.id, limit=limit)


@router.get("/{entrenamiento_id}", response_model=EntrenamientoOut)
async def obtener_entrenamiento(
    entrenamiento_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> EntrenamientoOut:
    entrenamiento = await crud_workout.get(db, current_user.id, entrenamiento_id)
    if entrenamiento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entrenamiento no encontrado."
        )
    return entrenamiento
