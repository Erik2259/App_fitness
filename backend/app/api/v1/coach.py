from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.crud import biometric as crud_biometric
from app.crud import workout as crud_workout
from app.models.biometric import ClusterRecuperacionEnum
from app.models.workout import TipoEntrenamientoEnum
from app.schemas.coach import RecomendacionRequest, RecomendacionResponse, ResumenCarga
from app.services.carga import agregar_carga
from app.services.llm import generar_recomendacion
from app.services.prompt_builder import SYSTEM_PROMPT, construir_prompt

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/recomendacion", response_model=RecomendacionResponse)
async def recomendacion(
    data: RecomendacionRequest, current_user: CurrentUser, db: DbSession
) -> RecomendacionResponse:
    """Fase 4: arma el contexto del atleta y pide al LLM la recomendación de hoy.

    Combina el estado de recuperación (Fase 3), la carga agregada (Fase 2) y la
    biomecánica de la última carrera, construye el prompt y lo envía al modelo.
    """
    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(days=data.ventana_dias)

    entrenamientos = await crud_workout.list_for_user(
        db, current_user.id, desde=desde, limit=500
    )
    resumen = agregar_carga(entrenamientos, ventana_dias=data.ventana_dias)

    # Estado de recuperación: el snapshot más reciente clasificado.
    metricas = await crud_biometric.list_for_user(db, current_user.id, limit=1)
    cluster = (
        metricas[0].cluster_recuperacion
        if metricas
        else ClusterRecuperacionEnum.SIN_CLASIFICAR
    )

    ultima_carrera = next(
        (
            e
            for e in entrenamientos
            if e.tipo in (TipoEntrenamientoEnum.RUNNING, TipoEntrenamientoEnum.INTERVALOS)
        ),
        None,
    )

    user_prompt = construir_prompt(
        usuario=current_user,
        cluster=cluster,
        resumen_carga=resumen,
        ultima_sesion_running=ultima_carrera,
    )
    respuesta = generar_recomendacion(SYSTEM_PROMPT, user_prompt)

    return RecomendacionResponse(
        fecha=date.today(),
        cluster_recuperacion=cluster.value,
        resumen_carga=ResumenCarga(**resumen),
        prompt=user_prompt,
        recomendacion=respuesta.texto,
        modelo=respuesta.modelo,
        dry_run=respuesta.dry_run,
    )
