"""Fase 4 — Construcción del prompt dinámico para el coach LLM.

El prompt se arma exclusivamente con datos ya procesados por el backend: el estado de
recuperación (clúster de la Fase 3), la carga agregada (Fase 2) y la biomecánica de la
última sesión de running. El LLM interpreta y aconseja; no calcula ni inventa métricas.
"""

from __future__ import annotations

from app.models.biometric import ClusterRecuperacionEnum
from app.models.user import Usuario
from app.models.workout import Entrenamiento

SYSTEM_PROMPT = (
    "Eres un coach de alto rendimiento para atletas híbridos (running + fuerza/calistenia). "
    "Recibes métricas ya calculadas por el sistema (TRIMP, tonelaje, estado de recuperación) "
    "y tu trabajo es interpretarlas y dar una recomendación de entrenamiento accionable para hoy. "
    "Nunca calcules ni inventes cifras: usa solo las que se te entregan. "
    "Sé concreto, prioriza la prevención de lesiones y la progresión sostenible, y responde en español "
    "en un máximo de 6 frases."
)

_EXPLICACION_CLUSTER = {
    ClusterRecuperacionEnum.OPTIMO: "recuperación óptima, el atleta puede asumir carga alta",
    ClusterRecuperacionEnum.ALERTA_FATIGA: "señales de fatiga, conviene moderar la intensidad",
    ClusterRecuperacionEnum.SOBREENTRENAMIENTO: "riesgo de sobreentrenamiento, priorizar descanso/recuperación activa",
    ClusterRecuperacionEnum.SIN_CLASIFICAR: "sin datos suficientes para clasificar la recuperación",
}


def _linea_biomecanica(ultima_sesion: Entrenamiento | None) -> str:
    if ultima_sesion is None:
        return "- Biomecánica running: sin sesiones recientes de carrera."
    partes = []
    if ultima_sesion.cadencia_spm is not None:
        partes.append(f"cadencia {ultima_sesion.cadencia_spm:.0f} spm")
    if ultima_sesion.oscilacion_vertical_cm is not None:
        partes.append(f"oscilación vertical {ultima_sesion.oscilacion_vertical_cm:.1f} cm")
    if ultima_sesion.tiempo_contacto_suelo_ms is not None:
        partes.append(f"tiempo de contacto {ultima_sesion.tiempo_contacto_suelo_ms:.0f} ms")
    if ultima_sesion.potencia_watts_promedio is not None:
        partes.append(f"potencia media {ultima_sesion.potencia_watts_promedio:.0f} W")
    if not partes:
        return "- Biomecánica running: sin métricas de técnica en la última sesión."
    return "- Biomecánica última carrera: " + ", ".join(partes) + "."


def construir_prompt(
    *,
    usuario: Usuario,
    cluster: ClusterRecuperacionEnum,
    resumen_carga: dict,
    ultima_sesion_running: Entrenamiento | None,
) -> str:
    """Devuelve el mensaje de usuario (contexto) que se enviará al LLM."""
    edad = None
    if usuario.fecha_nacimiento is not None:
        from datetime import date

        hoy = date.today()
        edad = hoy.year - usuario.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (usuario.fecha_nacimiento.month, usuario.fecha_nacimiento.day)
        )

    perfil = [f"Atleta: {usuario.nombre}"]
    if edad is not None:
        perfil.append(f"{edad} años")
    if usuario.sexo is not None:
        perfil.append(usuario.sexo.value)
    if usuario.fc_maxima:
        perfil.append(f"FCmax {usuario.fc_maxima}")
    if usuario.fc_reposo:
        perfil.append(f"FCreposo {usuario.fc_reposo}")

    lineas = [
        "Contexto del atleta para la recomendación de hoy:",
        "- Perfil: " + ", ".join(perfil) + ".",
        f"- Estado de recuperación (K-Means): {cluster.value} "
        f"({_EXPLICACION_CLUSTER[cluster]}).",
        f"- Carga últimos {resumen_carga['ventana_dias']} días: "
        f"TRIMP total {resumen_carga['trimp_total']}, "
        f"TRIMP medio/día {resumen_carga['trimp_medio_diario']}, "
        f"tonelaje total {resumen_carga['tonelaje_total_kg']} kg, "
        f"{resumen_carga['sesiones']} sesiones.",
        _linea_biomecanica(ultima_sesion_running),
        "",
        "Con base en lo anterior, indica: (1) tipo e intensidad de entrenamiento recomendado para hoy, "
        "(2) una alerta si hay riesgo, y (3) un consejo de técnica si aplica.",
    ]
    return "\n".join(lineas)
