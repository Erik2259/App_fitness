"""Tests de la ingesta del JSON de Health Auto Export."""

from datetime import date

from app.models.workout import TipoEntrenamientoEnum
from app.services.health_import import map_tipo, parse_daily_metrics, parse_workouts

PAYLOAD = {
    "data": {
        "workouts": [
            {
                "name": "Outdoor Run",
                "start": "2026-07-20 06:00:00 +0000",
                "end": "2026-07-20 06:45:00 +0000",
                "duration": 2700,
                "distance": {"qty": 8.2, "units": "km"},
                "activeEnergyBurned": {"qty": 620, "units": "kcal"},
                "avgHeartRate": {"qty": 152, "units": "bpm"},
                "maxHeartRate": {"qty": 178, "units": "bpm"},
            },
            {
                "name": "Traditional Strength Training",
                "start": "2026-07-21 18:00:00 +0000",
                "duration": 3000,
            },
            {"name": "Roto", "start": "no-es-fecha"},  # se debe ignorar sin romper
        ],
        "metrics": [
            {
                "name": "heart_rate_variability",
                "units": "ms",
                "data": [{"date": "2026-07-20 00:00:00 +0000", "qty": 65.3}],
            },
            {
                "name": "resting_heart_rate",
                "units": "bpm",
                "data": [{"date": "2026-07-20 00:00:00 +0000", "qty": 48}],
            },
            {
                "name": "sleep_analysis",
                "units": "hr",
                "data": [{"date": "2026-07-20 00:00:00 +0000", "asleep": 7.5, "rem": 1.5, "deep": 1.2, "core": 4.0}],
            },
        ],
    }
}


def test_map_tipo():
    assert map_tipo("Outdoor Run") == TipoEntrenamientoEnum.RUNNING
    assert map_tipo("Traditional Strength Training") == TipoEntrenamientoEnum.FUERZA
    assert map_tipo("High Intensity Interval Training") == TipoEntrenamientoEnum.INTERVALOS
    assert map_tipo("Core Training") == TipoEntrenamientoEnum.CALISTENIA
    assert map_tipo("Algo Raro") == TipoEntrenamientoEnum.OTRO
    assert map_tipo(None) == TipoEntrenamientoEnum.OTRO


def test_parse_workouts_mapea_y_descarta_malformados():
    workouts = parse_workouts(PAYLOAD)
    assert len(workouts) == 2  # el tercero (fecha inválida) se descarta

    run = workouts[0]
    assert run["tipo"] == TipoEntrenamientoEnum.RUNNING
    assert run["fuente"] == "health_auto_export"
    assert run["duracion_segundos"] == 2700
    assert run["distancia_m"] == 8200.0  # 8.2 km -> metros
    assert run["fc_promedio"] == 152
    assert run["fc_maxima_sesion"] == 178
    assert run["datos_crudos"]["name"] == "Outdoor Run"


def test_parse_workouts_duracion_desde_start_end():
    payload = {"data": {"workouts": [
        {"name": "Run", "start": "2026-07-20 06:00:00 +0000", "end": "2026-07-20 06:30:00 +0000"}
    ]}}
    w = parse_workouts(payload)[0]
    assert w["duracion_segundos"] == 1800  # 30 min calculados de start/end


def test_parse_daily_metrics_agrupa_por_fecha():
    metricas = parse_daily_metrics(PAYLOAD)
    dia = date(2026, 7, 20)
    assert dia in metricas
    campos = metricas[dia]
    assert campos["hrv_ms"] == 65.3
    assert campos["rhr_bpm"] == 48
    assert campos["sueno_total_min"] == 450  # 7.5 h -> 450 min
    assert campos["sueno_rem_min"] == 90
    assert campos["sueno_profundo_min"] == 72
    assert campos["sueno_ligero_min"] == 240
