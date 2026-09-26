"""
Generación y actualización del perfil evolutivo (resumen acumulado entre
sesiones).

Se ejecuta una sola vez por sesión, al cerrarla (ver endpoint
POST /session/close en chat.py) — no en cada mensaje. Usa el modelo
auxiliar (más barato) porque no necesita la misma profundidad
conversacional que el chat principal, solo consolidar información.
"""

from openai import OpenAI

from .config import OPENAI_API_KEY, OPENAI_AUXILIARY_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

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
    Genera el resumen actualizado a partir del resumen previo (puede ser
    string vacío) y los mensajes de la sesión que se está cerrando.
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
