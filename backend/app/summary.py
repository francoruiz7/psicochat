"""
Generates and updates the evolving profile (summary accumulated across
sessions).

Runs once per session, when it's closed (see the POST /session/close
endpoint in chat.py) — not on every message. Uses the auxiliary (cheaper)
model because it doesn't need the same conversational depth as the main
chat, just consolidation of information.
"""

from openai import OpenAI

from .config import OPENAI_API_KEY, OPENAI_AUXILIARY_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

# NOTE: this prompt is functional — it must produce a Spanish-language
# summary so it integrates naturally into a Spanish-speaking
# conversation, so it's kept in Spanish rather than translated.
SUMMARY_INSTRUCTIONS = """\
Vas a leer el resumen acumulado de sesiones anteriores (puede estar vacío,
si es la primera sesión) y la transcripción completa de la sesión de hoy,
de una conversación de apoyo terapéutico conversacional.

Tu tarea es producir un resumen actualizado, en español, que:

- Integre lo nuevo de la sesión de hoy con lo que ya existía, sin repetir
  literalmente el resumen anterior — reformulalo de manera consolidada.
- Capture: temas y preocupaciones recurrentes, patrones psicológicos ya
  identificados (y si se reafirmaron, matizaron o cambiaron hoy),
  formulaciones o descubrimientos que la persona hizo por sí misma,
  hitos o eventos relevantes mencionados, y el estado emocional general
  de la sesión de hoy.
- Sea neutral y descriptivo, sin diagnósticos ni juicios de valor.
- Tenga una extensión acotada (aproximadamente 200-400 palabras) — es un
  contexto de fondo para futuras sesiones, no una transcripción.
- Esté escrito en tercera persona, como notas de continuidad, no como si
  le hablaras a la persona.

Devolvé únicamente el resumen actualizado, sin encabezados ni comentarios
adicionales.
"""


def _format_transcript(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        speaker = "Persona" if m["role"] == "user" else "Asistente"
        lines.append(f"{speaker}: {m['content']}")
    return "\n".join(lines)


def generate_summary(previous_summary: str, session_messages: list[dict]) -> str:
    """
    Generates the updated summary from the previous summary (can be an
    empty string) and the messages of the session being closed.
    """
    transcript = _format_transcript(session_messages)

    user_content = (
        f"RESUMEN ACUMULADO PREVIO:\n{previous_summary or '(vacío — primera sesión)'}\n\n"
        f"TRANSCRIPCIÓN DE LA SESIÓN DE HOY:\n{transcript}"
    )

    completion = client.chat.completions.create(
        model=OPENAI_AUXILIARY_MODEL,
        messages=[
            {"role": "system", "content": SUMMARY_INSTRUCTIONS},
            {"role": "user", "content": user_content},
        ],
    )
    return completion.choices[0].message.content.strip()