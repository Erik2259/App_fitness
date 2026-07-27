from pydantic import BaseModel


class ResultadoIngesta(BaseModel):
    """Resumen de lo procesado tras un POST de Health Auto Export."""

    entrenamientos_creados: int
    entrenamientos_omitidos: int  # duplicados (mismo inicio) ya existentes
    metricas_creadas: int
    metricas_actualizadas: int
    fechas_metricas: list[str]
