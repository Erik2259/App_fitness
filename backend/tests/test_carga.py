"""Tests de la Fase 2: cálculo de TRIMP y agregación de carga."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.models.user import SexoEnum
from app.services.carga import agregar_carga, compute_trimp


def test_trimp_none_si_faltan_datos():
    assert compute_trimp(
        fc_promedio=None,
        duracion_segundos=3600,
        fc_maxima_usuario=190,
        fc_reposo_usuario=50,
    ) is None


def test_trimp_none_si_duracion_invalida():
    assert compute_trimp(
        fc_promedio=150,
        duracion_segundos=0,
        fc_maxima_usuario=190,
        fc_reposo_usuario=50,
    ) is None


def test_trimp_valor_positivo_y_razonable():
    # 60 min a FC media 150, FCmax 190, FCreposo 50 -> HRr ~ 0.714
    trimp = compute_trimp(
        fc_promedio=150,
        duracion_segundos=3600,
        fc_maxima_usuario=190,
        fc_reposo_usuario=50,
        sexo=SexoEnum.MASCULINO,
    )
    assert trimp is not None
    assert 100 < trimp < 200  # rango típico para una sesión de 1 h a intensidad media-alta


def test_trimp_crece_con_intensidad():
    base = dict(duracion_segundos=3600, fc_maxima_usuario=190, fc_reposo_usuario=50)
    suave = compute_trimp(fc_promedio=120, **base)
    intenso = compute_trimp(fc_promedio=175, **base)
    assert intenso > suave


def test_trimp_coeficiente_por_sexo():
    base = dict(fc_promedio=160, duracion_segundos=3600, fc_maxima_usuario=190, fc_reposo_usuario=50)
    masc = compute_trimp(sexo=SexoEnum.MASCULINO, **base)
    fem = compute_trimp(sexo=SexoEnum.FEMENINO, **base)
    # El coeficiente masculino (1.92) es mayor que el femenino (1.67) -> más TRIMP.
    assert masc > fem


def test_agregar_carga_vacio():
    resumen = agregar_carga([], ventana_dias=7)
    assert resumen["sesiones"] == 0
    assert resumen["trimp_total"] == 0.0
    assert resumen["tonelaje_total_kg"] == 0.0


def test_agregar_carga_suma_y_promedia():
    ahora = datetime.now(timezone.utc)
    sesiones = [
        SimpleNamespace(fecha_inicio=ahora, trimp=100.0, tonelaje_kg=2000.0),
        SimpleNamespace(fecha_inicio=ahora - timedelta(days=1), trimp=50.0, tonelaje_kg=None),
        SimpleNamespace(fecha_inicio=ahora - timedelta(days=2), trimp=None, tonelaje_kg=1000.0),
    ]
    resumen = agregar_carga(sesiones, ventana_dias=7)
    assert resumen["sesiones"] == 3
    assert resumen["trimp_total"] == 150.0
    assert resumen["tonelaje_total_kg"] == 3000.0
    assert resumen["trimp_medio_diario"] == round(150.0 / 7, 2)
