"""Tests de la Fase 4: construcción del prompt y cliente LLM en dry-run."""

from types import SimpleNamespace

from app.models.biometric import ClusterRecuperacionEnum
from app.models.user import SexoEnum
from app.services.llm import generar_recomendacion
from app.services.prompt_builder import SYSTEM_PROMPT, construir_prompt


def _usuario():
    return SimpleNamespace(
        nombre="Erik",
        fecha_nacimiento=None,
        sexo=SexoEnum.MASCULINO,
        fc_maxima=190,
        fc_reposo=48,
    )


def _resumen():
    return {
        "ventana_dias": 7,
        "trimp_total": 420.0,
        "trimp_medio_diario": 60.0,
        "tonelaje_total_kg": 12000.0,
        "sesiones": 5,
    }


def test_prompt_incluye_estado_y_carga():
    prompt = construir_prompt(
        usuario=_usuario(),
        cluster=ClusterRecuperacionEnum.ALERTA_FATIGA,
        resumen_carga=_resumen(),
        ultima_sesion_running=None,
    )
    assert "Erik" in prompt
    assert "alerta_fatiga" in prompt
    assert "TRIMP total 420.0" in prompt
    assert "sin sesiones recientes" in prompt


def test_prompt_incluye_biomecanica():
    carrera = SimpleNamespace(
        cadencia_spm=178.0,
        oscilacion_vertical_cm=8.5,
        tiempo_contacto_suelo_ms=230.0,
        potencia_watts_promedio=290.0,
    )
    prompt = construir_prompt(
        usuario=_usuario(),
        cluster=ClusterRecuperacionEnum.OPTIMO,
        resumen_carga=_resumen(),
        ultima_sesion_running=carrera,
    )
    assert "cadencia 178 spm" in prompt
    assert "oscilación vertical 8.5 cm" in prompt


def test_llm_dry_run_sin_api_key():
    respuesta = generar_recomendacion(SYSTEM_PROMPT, "contexto de prueba")
    assert respuesta.dry_run is True
    assert "dry-run" in respuesta.texto
    assert respuesta.modelo  # el nombre del modelo configurado siempre viene informado
