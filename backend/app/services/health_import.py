"""Traducción del JSON de la app "Health Auto Export" a nuestros modelos.

Esa app (App Store) lee HealthKit y hace POST de un JSON a una URL. Su formato
varía entre versiones y unidades (km/mi, kcal/kJ, horas/minutos), así que aquí se
parsea de forma **defensiva**: cada item se procesa en un try/except y lo que no se
entiende se ignora sin tumbar la petición. El payload crudo se guarda por si hay
que reprocesar.

Formato aproximado esperado::

    {
      "data": {
        "workouts": [ {"name","start","end","duration","distance",...} ],
        "metrics":  [ {"name","units","data":[{"date","qty",...}]} ]
      }
    }
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.workout import TipoEntrenamientoEnum

# --- Mapeo de nombres de workout de HealthKit a nuestro enum ---
_TIPO_KEYWORDS: list[tuple[tuple[str, ...], TipoEntrenamientoEnum]] = [
    (("interval", "hiit", "high intensity"), TipoEntrenamientoEnum.INTERVALOS),
    (("run", "carrera", "trail"), TipoEntrenamientoEnum.RUNNING),
    (("strength", "fuerza", "weight", "traditional", "functional"), TipoEntrenamientoEnum.FUERZA),
    (("core", "calisthen", "calisten", "yoga", "flexib", "pilates"), TipoEntrenamientoEnum.CALISTENIA),
]


def map_tipo(nombre: str | None) -> TipoEntrenamientoEnum:
    """Traduce el nombre del workout a un TipoEntrenamientoEnum (OTRO si no encaja)."""
    if not nombre:
        return TipoEntrenamientoEnum.OTRO
    n = nombre.lower()
    for claves, tipo in _TIPO_KEYWORDS:
        if any(c in n for c in claves):
            return tipo
    return TipoEntrenamientoEnum.OTRO


def _parse_dt(value: Any) -> datetime | None:
    """Parsea las fechas de Health Auto Export ('2024-06-01 06:00:00 +0000') o ISO."""
    if not value or not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _qty(value: Any) -> float | None:
    """Extrae un número de {'qty': n, 'units': ...} o de un número suelto."""
    if isinstance(value, dict):
        value = value.get("qty")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _units(value: Any) -> str:
    return value.get("units", "").lower() if isinstance(value, dict) else ""


def _a_metros(distancia: Any) -> float | None:
    """Convierte una distancia {qty, units} a metros (asume km si no hay unidad)."""
    q = _qty(distancia)
    if q is None:
        return None
    u = _units(distancia)
    if u.startswith("mi"):  # millas
        return round(q * 1609.34, 2)
    if u in ("m", "meter", "metre", "metros"):
        return round(q, 2)
    return round(q * 1000, 2)  # km por defecto (unidad más común en Health Auto Export)


def _horas_a_min(value: float | None) -> int | None:
    """El sueño puede venir en horas (floats < 24) o minutos; normaliza a minutos."""
    if value is None:
        return None
    return int(round(value * 60)) if value < 24 else int(round(value))


def parse_workouts(payload: dict) -> list[dict]:
    """Devuelve una lista de dicts compatibles con EntrenamientoCreate + datos_crudos."""
    workouts = (payload.get("data") or {}).get("workouts") or []
    resultado: list[dict] = []
    for w in workouts:
        try:
            inicio = _parse_dt(w.get("start"))
            if inicio is None:
                continue
            fin = _parse_dt(w.get("end"))
            duracion = w.get("duration")
            if not isinstance(duracion, (int, float)) and fin is not None:
                duracion = (fin - inicio).total_seconds()

            resultado.append(
                {
                    "tipo": map_tipo(w.get("name")),
                    "fuente": "health_auto_export",
                    "fecha_inicio": inicio,
                    "fecha_fin": fin,
                    "duracion_segundos": int(duracion) if isinstance(duracion, (int, float)) else None,
                    "fc_promedio": _int(_qty(w.get("avgHeartRate"))),
                    "fc_maxima_sesion": _int(_qty(w.get("maxHeartRate"))),
                    "calorias_activas": _qty(w.get("activeEnergyBurned") or w.get("activeEnergy")),
                    "distancia_m": _a_metros(w.get("distance")),
                    "cadencia_spm": _qty(w.get("stepCadence") or w.get("cadence")),
                    "datos_crudos": w,
                }
            )
        except Exception:
            # Un workout malformado no debe tumbar toda la importación.
            continue
    return resultado


# Nombres de métrica de HealthKit que nos interesan para el snapshot diario.
_SLEEP_NAMES = {"sleep_analysis", "sleep"}
_HRV_NAMES = {"heart_rate_variability", "hrv", "heart_rate_variability_sdnn"}
_RHR_NAMES = {"resting_heart_rate", "resting_heart_rate_bpm"}


def parse_daily_metrics(payload: dict) -> dict:
    """Agrupa las métricas diarias por fecha (date -> campos de MetricaBiometrica)."""
    metrics = (payload.get("data") or {}).get("metrics") or []
    por_fecha: dict = {}

    for metric in metrics:
        nombre = (metric.get("name") or "").lower()
        for punto in metric.get("data") or []:
            dt = _parse_dt(punto.get("date"))
            if dt is None:
                continue
            fecha = dt.date()
            registro = por_fecha.setdefault(fecha, {})
            try:
                if nombre in _HRV_NAMES:
                    registro["hrv_ms"] = _qty(punto.get("qty") if "qty" in punto else punto)
                elif nombre in _RHR_NAMES:
                    registro["rhr_bpm"] = _int(_qty(punto.get("qty") if "qty" in punto else punto))
                elif nombre in _SLEEP_NAMES:
                    _acumular_sueno(registro, punto)
            except Exception:
                continue

    return por_fecha


def _acumular_sueno(registro: dict, punto: dict) -> None:
    """Extrae fases de sueño de un punto (asleep/rem/deep/core/light) a minutos."""
    total = punto.get("asleep") if punto.get("asleep") is not None else punto.get("totalSleep")
    rem = punto.get("rem")
    deep = punto.get("deep")
    light = punto.get("core") if punto.get("core") is not None else punto.get("light")

    if total is not None:
        registro["sueno_total_min"] = _horas_a_min(_qty(total))
    if rem is not None:
        registro["sueno_rem_min"] = _horas_a_min(_qty(rem))
    if deep is not None:
        registro["sueno_profundo_min"] = _horas_a_min(_qty(deep))
    if light is not None:
        registro["sueno_ligero_min"] = _horas_a_min(_qty(light))


def _int(value: float | None) -> int | None:
    return int(round(value)) if isinstance(value, (int, float)) else None
