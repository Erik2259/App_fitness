from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.crud import biometric as crud_biometric
from app.models.biometric import ClusterRecuperacionEnum
from app.schemas.biometric import MetricaBiometricaCreate, MetricaBiometricaOut
from app.services.clustering import clasificar_recuperacion

router = APIRouter(prefix="/metricas-biometricas", tags=["metricas-biometricas"])


@router.post("", response_model=MetricaBiometricaOut, status_code=status.HTTP_201_CREATED)
async def crear_o_actualizar_metrica(
    data: MetricaBiometricaCreate, current_user: CurrentUser, db: DbSession
) -> MetricaBiometricaOut:
    """Registra el snapshot diario de recuperación (upsert por fecha).

    Como hay un único registro por atleta y día, si ya existe uno para esa fecha se
    actualizan sus campos en lugar de crear un duplicado.
    """
    existente = await crud_biometric.get_by_fecha(db, current_user.id, data.fecha)
    if existente is not None:
        # Reutiliza el mismo esquema de campos para el update parcial.
        from app.schemas.biometric import MetricaBiometricaUpdate

        update = MetricaBiometricaUpdate(**data.model_dump(exclude={"fecha"}))
        return await crud_biometric.update(db, existente, update)

    return await crud_biometric.create(db, current_user.id, data)


@router.get("", response_model=list[MetricaBiometricaOut])
async def listar_metricas(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=90, ge=1, le=365),
) -> list[MetricaBiometricaOut]:
    """Historial de snapshots diarios, del más reciente al más antiguo."""
    return await crud_biometric.list_for_user(db, current_user.id, limit=limit)


@router.post("/clasificar", response_model=dict)
async def clasificar(current_user: CurrentUser, db: DbSession) -> dict:
    """Fase 3: ejecuta K-Means sobre el historial del atleta y persiste el clúster de cada día.

    Devuelve un resumen del ajuste (nº de muestras, si se entrenó y el conteo por clúster).
    """
    metricas = await crud_biometric.list_for_user(db, current_user.id, limit=365)
    resultado = clasificar_recuperacion(metricas)

    if not resultado.entrenado:
        return {
            "entrenado": False,
            "n_muestras": resultado.n_muestras,
            "motivo": resultado.motivo,
        }

    conteo: dict[str, int] = {}
    for metrica in metricas:
        etiqueta = resultado.etiquetas.get(str(metrica.id))
        if etiqueta is not None and metrica.cluster_recuperacion != etiqueta:
            metrica.cluster_recuperacion = etiqueta
        if etiqueta is not None:
            conteo[etiqueta.value] = conteo.get(etiqueta.value, 0) + 1
    await db.commit()

    return {
        "entrenado": True,
        "n_muestras": resultado.n_muestras,
        "conteo_por_cluster": conteo,
    }
