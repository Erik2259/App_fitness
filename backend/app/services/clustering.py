"""Fase 3 — Clasificación del estado de recuperación con K-Means.

Toma el historial de `MetricaBiometrica` de un atleta y agrupa cada día en uno de
tres clústers de recuperación. K-Means no sabe qué significan sus clústers, así que
tras entrenarlo ordenamos los centroides por un "índice de fatiga" interpretable y
les asignamos las etiquetas del negocio (óptimo / alerta_fatiga / sobreentrenamiento).

Features usadas (las cuatro señales fisiológicas del snapshot diario):
    deuda_sueno_min, carga_metabolica, hrv_ms, rhr_bpm

Un HRV alto es bueno (recuperado); deuda de sueño, carga y RHR altos son malos.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from app.models.biometric import ClusterRecuperacionEnum, MetricaBiometrica

_FEATURES = ["deuda_sueno_min", "carga_metabolica", "hrv_ms", "rhr_bpm"]
_N_CLUSTERS = 3

# Etiquetas ordenadas de menor a mayor fatiga; se asignan a los centroides ya ordenados.
_ETIQUETAS_POR_FATIGA = [
    ClusterRecuperacionEnum.OPTIMO,
    ClusterRecuperacionEnum.ALERTA_FATIGA,
    ClusterRecuperacionEnum.SOBREENTRENAMIENTO,
]


@dataclass
class ResultadoClustering:
    """Mapa id_de_métrica -> etiqueta asignada, más metadatos del ajuste."""

    etiquetas: dict[str, ClusterRecuperacionEnum]
    n_muestras: int
    entrenado: bool
    motivo: str = ""


def _to_dataframe(metricas: list[MetricaBiometrica]) -> pd.DataFrame:
    filas = [
        {
            "id": str(m.id),
            "deuda_sueno_min": m.deuda_sueno_min,
            "carga_metabolica": m.carga_metabolica,
            "hrv_ms": m.hrv_ms,
            "rhr_bpm": m.rhr_bpm,
        }
        for m in metricas
    ]
    return pd.DataFrame(filas)


def _indice_fatiga(centroides_originales: np.ndarray, columnas: list[str]) -> np.ndarray:
    """Puntúa cada centroide (en unidades reales) por fatiga.

    Mayor deuda de sueño, carga y RHR suman fatiga; mayor HRV la resta.
    """
    idx = {col: i for i, col in enumerate(columnas)}
    score = (
        centroides_originales[:, idx["deuda_sueno_min"]]
        + centroides_originales[:, idx["carga_metabolica"]]
        + centroides_originales[:, idx["rhr_bpm"]]
        - centroides_originales[:, idx["hrv_ms"]]
    )
    return score


def clasificar_recuperacion(metricas: list[MetricaBiometrica]) -> ResultadoClustering:
    """Ajusta K-Means sobre las métricas dadas y devuelve la etiqueta de cada una.

    Requiere al menos `_N_CLUSTERS` filas con las cuatro features completas. Si hay
    menos, devuelve un resultado no entrenado (las métricas se quedan SIN_CLASIFICAR).
    """
    if len(metricas) < _N_CLUSTERS:
        return ResultadoClustering(
            etiquetas={},
            n_muestras=len(metricas),
            entrenado=False,
            motivo=f"Se requieren ≥{_N_CLUSTERS} métricas; hay {len(metricas)}.",
        )

    df = _to_dataframe(metricas).dropna(subset=_FEATURES)
    if len(df) < _N_CLUSTERS:
        return ResultadoClustering(
            etiquetas={},
            n_muestras=len(df),
            entrenado=False,
            motivo=f"Solo {len(df)} métricas con las 4 señales completas (se requieren ≥{_N_CLUSTERS}).",
        )

    X = df[_FEATURES].to_numpy(dtype=float)
    X_scaled = StandardScaler().fit_transform(X)

    kmeans = KMeans(n_clusters=_N_CLUSTERS, random_state=42, n_init=10)
    cluster_ids = kmeans.fit_predict(X_scaled)

    # Los centroides están en el espacio escalado; los llevamos a unidades reales
    # para puntuar la fatiga de forma interpretable.
    centroides_reales = _centroides_a_unidades_reales(X, X_scaled, kmeans.cluster_centers_)
    fatiga = _indice_fatiga(centroides_reales, _FEATURES)
    orden = np.argsort(fatiga)  # cluster_id menos fatigado primero
    cluster_a_etiqueta = {
        int(cluster_id): _ETIQUETAS_POR_FATIGA[rango] for rango, cluster_id in enumerate(orden)
    }

    etiquetas = {
        row_id: cluster_a_etiqueta[int(cid)]
        for row_id, cid in zip(df["id"].tolist(), cluster_ids)
    }
    return ResultadoClustering(etiquetas=etiquetas, n_muestras=len(df), entrenado=True)


def _centroides_a_unidades_reales(
    X: np.ndarray, X_scaled: np.ndarray, centroides_scaled: np.ndarray
) -> np.ndarray:
    """Reconstruye media/desviación desde los datos para invertir el escalado."""
    media = X.mean(axis=0)
    desv = X.std(axis=0)
    desv[desv == 0] = 1.0  # evita división por cero en features constantes
    return centroides_scaled * desv + media
