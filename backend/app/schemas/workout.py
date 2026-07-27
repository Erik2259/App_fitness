import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.workout import TipoEntrenamientoEnum


class EntrenamientoBase(BaseModel):
    """Payload que envía Flutter con una sesión de HealthKit.

    `trimp` no se acepta desde el cliente: lo calcula el backend en la Fase 2. Cualquier
    valor enviado se ignora (por eso no está en este esquema de entrada).
    """

    tipo: TipoEntrenamientoEnum
    fuente: str = Field(default="healthkit", max_length=50)

    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    duracion_segundos: int | None = Field(default=None, ge=0)

    # Esfuerzo cardiovascular
    fc_promedio: int | None = Field(default=None, gt=0, lt=250)
    fc_maxima_sesion: int | None = Field(default=None, gt=0, lt=250)
    calorias_activas: float | None = Field(default=None, ge=0)

    # Biomecánica de running
    distancia_m: float | None = Field(default=None, ge=0)
    ritmo_promedio_seg_km: float | None = Field(default=None, gt=0)
    potencia_watts_promedio: float | None = Field(default=None, ge=0)
    potencia_watts_pico: float | None = Field(default=None, ge=0)
    cadencia_spm: float | None = Field(default=None, ge=0)
    oscilacion_vertical_cm: float | None = Field(default=None, ge=0)
    tiempo_contacto_suelo_ms: float | None = Field(default=None, ge=0)

    # Fuerza / calistenia
    tonelaje_kg: float | None = Field(default=None, ge=0)
    series_totales: int | None = Field(default=None, ge=0)
    repeticiones_totales: int | None = Field(default=None, ge=0)
    peso_extra_kg: float | None = Field(default=None, ge=0)

    datos_crudos: dict[str, Any] | None = None


class EntrenamientoCreate(EntrenamientoBase):
    pass


class EntrenamientoOut(EntrenamientoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID
    trimp: float | None = None  # calculado por el backend (Fase 2)
    created_at: datetime
