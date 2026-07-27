import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import Usuario


class ClusterRecuperacionEnum(str, enum.Enum):
    OPTIMO = "optimo"
    ALERTA_FATIGA = "alerta_fatiga"
    SOBREENTRENAMIENTO = "sobreentrenamiento"
    SIN_CLASIFICAR = "sin_clasificar"  # aún no procesado por el modelo K-Means (Fase 3)


class MetricaBiometrica(Base):
    """Snapshot diario de recuperación y carga de un usuario.

    Es la unidad que alimenta al modelo K-Means (Fase 3): combina "deuda de sueño"
    y "carga metabólica" para clasificar el día del atleta en un clúster de estado
    físico. Un usuario tiene como máximo un registro por fecha.
    """

    __tablename__ = "metricas_biometricas"
    __table_args__ = (UniqueConstraint("usuario_id", "fecha", name="uq_usuario_fecha"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True
    )

    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # --- Sueño (fases extraídas de HealthKit) ---
    sueno_total_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sueno_rem_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sueno_profundo_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sueno_ligero_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deuda_sueno_min: Mapped[int | None] = mapped_column(Integer, nullable=True)  # vs. objetivo del usuario

    # --- Recuperación ---
    hrv_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    rhr_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Carga agregada del día (input directo del K-Means junto a deuda_sueno_min) ---
    carga_metabolica: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Resultado del modelo de clustering (se actualiza en Fase 3) ---
    cluster_recuperacion: Mapped[ClusterRecuperacionEnum] = mapped_column(
        Enum(ClusterRecuperacionEnum, name="cluster_recuperacion_enum"),
        default=ClusterRecuperacionEnum.SIN_CLASIFICAR,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="metricas_biometricas")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<MetricaBiometrica usuario_id={self.usuario_id} fecha={self.fecha} "
            f"cluster={self.cluster_recuperacion}>"
        )
