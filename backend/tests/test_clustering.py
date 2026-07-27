"""Tests de la Fase 3: clustering K-Means del estado de recuperación."""

import uuid
from types import SimpleNamespace

from app.models.biometric import ClusterRecuperacionEnum
from app.services.clustering import clasificar_recuperacion


def _metrica(deuda, carga, hrv, rhr):
    return SimpleNamespace(
        id=uuid.uuid4(),
        deuda_sueno_min=deuda,
        carga_metabolica=carga,
        hrv_ms=hrv,
        rhr_bpm=rhr,
    )


def test_no_entrena_con_pocas_muestras():
    resultado = clasificar_recuperacion([_metrica(0, 100, 90, 48), _metrica(30, 200, 70, 55)])
    assert resultado.entrenado is False
    assert resultado.etiquetas == {}


def test_no_entrena_si_faltan_features():
    metricas = [
        _metrica(0, 100, 90, 48),
        _metrica(30, 200, None, 55),
        _metrica(120, 400, 40, 65),
    ]
    resultado = clasificar_recuperacion(metricas)
    assert resultado.entrenado is False


def test_asigna_tres_clusters_interpretables():
    # Tres grupos bien separados: descansado, fatiga moderada y sobreentrenado.
    optimos = [_metrica(-10, 80, 95, 46), _metrica(0, 90, 92, 47), _metrica(5, 100, 90, 48)]
    fatiga = [_metrica(60, 250, 70, 55), _metrica(70, 260, 68, 56), _metrica(65, 255, 69, 57)]
    sobre = [_metrica(180, 500, 40, 66), _metrica(190, 520, 38, 68), _metrica(200, 510, 39, 67)]
    metricas = optimos + fatiga + sobre

    resultado = clasificar_recuperacion(metricas)
    assert resultado.entrenado is True
    assert resultado.n_muestras == 9

    # El grupo descansado debe caer en OPTIMO y el exhausto en SOBREENTRENAMIENTO.
    for m in optimos:
        assert resultado.etiquetas[str(m.id)] == ClusterRecuperacionEnum.OPTIMO
    for m in sobre:
        assert resultado.etiquetas[str(m.id)] == ClusterRecuperacionEnum.SOBREENTRENAMIENTO

    # Las tres etiquetas del negocio deben aparecer exactamente una vez por grupo.
    valores = set(resultado.etiquetas.values())
    assert valores == {
        ClusterRecuperacionEnum.OPTIMO,
        ClusterRecuperacionEnum.ALERTA_FATIGA,
        ClusterRecuperacionEnum.SOBREENTRENAMIENTO,
    }
