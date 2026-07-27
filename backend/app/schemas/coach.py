from datetime import date

from pydantic import BaseModel, Field


class ResumenCarga(BaseModel):
    """Agregados de carga que se le muestran al LLM (ya calculados en Python)."""

    ventana_dias: int
    trimp_total: float
    trimp_medio_diario: float
    tonelaje_total_kg: float
    sesiones: int


class RecomendacionRequest(BaseModel):
    ventana_dias: int = Field(default=7, ge=1, le=60)


class RecomendacionResponse(BaseModel):
    fecha: date
    cluster_recuperacion: str
    resumen_carga: ResumenCarga
    prompt: str  # el prompt exacto que se construyó (trazabilidad)
    recomendacion: str  # respuesta del LLM, o nota de dry-run si no hay API key
    modelo: str
    dry_run: bool
