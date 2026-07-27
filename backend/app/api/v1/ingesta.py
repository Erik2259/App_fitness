from typing import Any

from fastapi import APIRouter, Body

from app.api.deps import CurrentUser, DbSession
from app.crud import biometric as crud_biometric
from app.crud import workout as crud_workout
from app.schemas.biometric import MetricaBiometricaCreate, MetricaBiometricaUpdate
from app.schemas.ingesta import ResultadoIngesta
from app.schemas.workout import EntrenamientoCreate
from app.services.carga import compute_trimp
from app.services.health_import import parse_daily_metrics, parse_workouts

router = APIRouter(prefix="/ingesta", tags=["ingesta"])


@router.post("/health-auto-export", response_model=ResultadoIngesta)
async def ingesta_health_auto_export(
    current_user: CurrentUser,
    db: DbSession,
    payload: dict[str, Any] = Body(...),
) -> ResultadoIngesta:
    """Recibe el JSON de la app *Health Auto Export* y lo vuelca a la base de datos.

    Configura en la app un automation de tipo REST API apuntando a esta ruta, con el
    header `Authorization: Bearer <token>`. Los entrenamientos se crean (calculando su
    TRIMP) y las métricas diarias se hacen upsert por fecha. Reimportar el mismo export
    no duplica sesiones (se deduplican por instante de inicio).
    """
    creados = omitidos = 0

    for datos in parse_workouts(payload):
        if await crud_workout.exists_by_start(db, current_user.id, datos["fecha_inicio"]):
            omitidos += 1
            continue

        entrenamiento = await crud_workout.create(
            db, current_user.id, EntrenamientoCreate(**datos)
        )
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
        creados += 1

    metricas_creadas = metricas_actualizadas = 0
    fechas: list[str] = []
    for fecha, campos in sorted(parse_daily_metrics(payload).items()):
        # Ignora fechas sin ninguna señal útil.
        if not any(v is not None for v in campos.values()):
            continue
        fechas.append(fecha.isoformat())
        existente = await crud_biometric.get_by_fecha(db, current_user.id, fecha)
        if existente is not None:
            await crud_biometric.update(db, existente, MetricaBiometricaUpdate(**campos))
            metricas_actualizadas += 1
        else:
            await crud_biometric.create(
                db, current_user.id, MetricaBiometricaCreate(fecha=fecha, **campos)
            )
            metricas_creadas += 1

    return ResultadoIngesta(
        entrenamientos_creados=creados,
        entrenamientos_omitidos=omitidos,
        metricas_creadas=metricas_creadas,
        metricas_actualizadas=metricas_actualizadas,
        fechas_metricas=fechas,
    )
