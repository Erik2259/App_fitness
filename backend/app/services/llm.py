"""Fase 4 — Cliente del LLM del coach (Anthropic Claude).

Se aísla la dependencia del proveedor detrás de una única función `generar_recomendacion`.
Si no hay `ANTHROPIC_API_KEY` configurada, funciona en modo *dry-run*: devuelve una nota
en lugar de llamar al modelo, para poder desarrollar y testear sin gastar tokens.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings

settings = get_settings()


@dataclass
class RespuestaLLM:
    texto: str
    modelo: str
    dry_run: bool


def generar_recomendacion(system_prompt: str, user_prompt: str) -> RespuestaLLM:
    """Llama a Claude con el prompt del coach y devuelve el texto de la recomendación.

    En dry-run (sin API key) no contacta al proveedor y devuelve una nota explicativa.
    """
    if not settings.anthropic_api_key:
        return RespuestaLLM(
            texto=(
                "[dry-run: sin ANTHROPIC_API_KEY configurada] "
                "El backend construyó el contexto correctamente; conecta una API key para "
                "recibir la recomendación generada por el modelo."
            ),
            modelo=settings.llm_model,
            dry_run=True,
        )

    # Import perezoso: el SDK solo se necesita cuando de verdad se llama al modelo.
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    texto = "".join(
        bloque.text for bloque in message.content if getattr(bloque, "type", None) == "text"
    )
    return RespuestaLLM(texto=texto.strip(), modelo=settings.llm_model, dry_run=False)
