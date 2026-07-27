import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.biometric import ClusterRecuperacionEnum


class MetricaBiometricaBase(BaseModel):
    """Snapshot diario de recuperación enviado por Flutter (uno por fecha y usuario)."""

    fecha: date

    # Sueño
    sueno_total_min: int | None = Field(default=None, ge=0)
    sueno_rem_min: int | None = Field(default=None, ge=0)
    sueno_profundo_min: int | None = Field(default=None, ge=0)
    sueno_ligero_min: int | None = Field(default=None, ge=0)
    deuda_sueno_min: int | None = None  # puede ser negativa (durmió de más)

    # Recuperación
    hrv_ms: float | None = Field(default=None, ge=0)
    rhr_bpm: int | None = Field(default=None, gt=0, lt=200)

    # Carga agregada del día
    carga_metabolica: float | None = Field(default=None, ge=0)


class MetricaBiometricaCreate(MetricaBiometricaBase):
    pass


class MetricaBiometricaUpdate(BaseModel):
    """Actualización parcial de una métrica existente (upsert desde el cliente)."""

    sueno_total_min: int | None = Field(default=None, ge=0)
    sueno_rem_min: int | None = Field(default=None, ge=0)
    sueno_profundo_min: int | None = Field(default=None, ge=0)
    sueno_ligero_min: int | None = Field(default=None, ge=0)
    deuda_sueno_min: int | None = None
    hrv_ms: float | None = Field(default=None, ge=0)
    rhr_bpm: int | None = Field(default=None, gt=0, lt=200)
    carga_metabolica: float | None = Field(default=None, ge=0)


class MetricaBiometricaOut(MetricaBiometricaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID
    cluster_recuperacion: ClusterRecuperacionEnum
    created_at: datetime
