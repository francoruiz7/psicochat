"""
Detección de riesgo (Fase 3).

Corre como una capa ADICIONAL a las instrucciones que ya tiene el propio
system prompt (sección "CUANDO ESTÉ MUY ANGUSTIADO" en
prompts/system_prompt.txt) — no la reemplaza. La idea es no depender
únicamente de que el modelo conversacional principal "se acuerde" de
manejar bien una señal de riesgo en el texto libre de su respuesta: acá
se clasifica el mensaje de la persona de forma explícita y separada, para
poder disparar el banner de recursos de ayuda en la interfaz de forma
determinística.

Usa el modelo auxiliar (barato) porque es una clasificación simple, no
requiere la profundidad del modelo conversacional principal.
"""

import json

from openai import OpenAI

from .config import OPENAI_API_KEY, OPENAI_AUXILIARY_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

RISK_CLASSIFIER_PROMPT = """\
Sos un clasificador de seguridad para una app de apoyo terapéutico \
conversacional.

Vas a leer el último mensaje que escribió la persona y tenés que \
determinar si expresa alguna de estas señales:
- Riesgo de autolesión o ideación suicida (propia).
- Riesgo de hacerle daño a otra persona.
- Una situación de peligro físico inmediato.

Frases metafóricas o coloquiales claramente no literales ("me muero de \
vergüenza", "esto me mata de risa", "quiero matar a mi hermano por lo \
que hizo" dicho en tono de frustración cotidiana sin intención real) NO \
cuentan como riesgo. Ante cualquier duda razonable de que sí podría ser \
literal, clasificá como riesgo.

Respondé ÚNICAMENTE con un JSON de esta forma, sin texto adicional:
{"risk": true} o {"risk": false}
"""


def assess_risk(message: str) -> bool:
    try:
        completion = client.chat.completions.create(
            model=OPENAI_AUXILIARY_MODEL,
            messages=[
                {"role": "system", "content": RISK_CLASSIFIER_PROMPT},
                {"role": "user", "content": message},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(completion.choices[0].message.content)
        return bool(data.get("risk", False))
    except Exception:
        # Fail-safe: si el clasificador falla técnicamente (timeout, error
        # de red, JSON inválido), no bloqueamos la conversación ni
        # rompemos el chat. Queda como respaldo la instrucción del propio
        # system prompt principal para estos casos.
        return False
