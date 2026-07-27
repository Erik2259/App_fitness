"""Fase 2 — Cálculo de carga de entrenamiento.

Todo el cómputo cuantitativo vive aquí, en Python/Pandas: el LLM (Fase 4) recibe
estos números ya calculados y solo los interpreta, nunca los estima.

- **TRIMP** (Training Impulse, método de Banister ponderado por FC de reserva): una
  medida de la carga cardiovascular de una sesión que pondera el tiempo por la
  intensidad de forma exponencial, con un coeficiente distinto por sexo.
- **Tonelaje**: volumen de fuerza (kg movidos), que ya llega calculado desde el
  cliente pero se agrega aquí por ventanas de tiempo.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

import pandas as pd

from app.models.user import SexoEnum
from app.models.workout import Entrenamiento

# Coeficiente exponencial del método de Banister, dependiente del sexo.
_TRIMP_K = {
    SexoEnum.MASCULINO: 1.92,
    SexoEnum.FEMENINO: 1.67,
}
_TRIMP_K_DEFAULT = 1.92  # si no se conoce el sexo, se usa el coeficiente masculino


def compute_trimp(
    *,
    fc_promedio: int | None,
    duracion_segundos: int | None,
    fc_maxima_usuario: int | None,
    fc_reposo_usuario: int | None,
    sexo: SexoEnum | None = None,
) -> float | None:
    """Devuelve el TRIMP de una sesión, o None si faltan datos para calcularlo.

    TRIMP = duracion_min · HRr · 0.64 · e^(k · HRr)
    donde HRr = (FCprom − FCreposo) / (FCmax − FCreposo) es la fracción de FC de reserva.
    """
    if None in (fc_promedio, duracion_segundos, fc_maxima_usuario, fc_reposo_usuario):
        return None
    if duracion_segundos <= 0 or fc_maxima_usuario <= fc_reposo_usuario:
        return None

    hr_reserve = (fc_promedio - fc_reposo_usuario) / (fc_maxima_usuario - fc_reposo_usuario)
    # Acotar a [0, 1]: FC por debajo del reposo o por encima de la máxima son ruido.
    hr_reserve = max(0.0, min(1.0, hr_reserve))

    k = _TRIMP_K.get(sexo, _TRIMP_K_DEFAULT)
    duracion_min = duracion_segundos / 60.0
    trimp = duracion_min * hr_reserve * 0.64 * math.exp(k * hr_reserve)
    return round(trimp, 2)


def agregar_carga(entrenamientos: Iterable[Entrenamiento], ventana_dias: int) -> dict:
    """Agrega la carga de una lista de entrenamientos usando Pandas.

    Devuelve un dict con TRIMP total y medio diario, tonelaje total y nº de sesiones,
    listo para poblar `schemas.coach.ResumenCarga`.
    """
    filas = [
        {
            "fecha": e.fecha_inicio,
            "trimp": e.trimp or 0.0,
            "tonelaje_kg": e.tonelaje_kg or 0.0,
        }
        for e in entrenamientos
    ]

    if not filas:
        return {
            "ventana_dias": ventana_dias,
            "trimp_total": 0.0,
            "trimp_medio_diario": 0.0,
            "tonelaje_total_kg": 0.0,
            "sesiones": 0,
        }

    df = pd.DataFrame(filas)
    trimp_total = float(df["trimp"].sum())
    tonelaje_total = float(df["tonelaje_kg"].sum())

    return {
        "ventana_dias": ventana_dias,
        "trimp_total": round(trimp_total, 2),
        "trimp_medio_diario": round(trimp_total / ventana_dias, 2),
        "tonelaje_total_kg": round(tonelaje_total, 2),
        "sesiones": int(len(df)),
    }
