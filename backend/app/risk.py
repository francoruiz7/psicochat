"""
Risk detection (self-harm/suicide/violence/immediate danger).

Runs as an ADDITIONAL layer to what the system prompt itself already
asks for (see the "CUANDO ESTÉ MUY ANGUSTIADO" section in
prompts/system_prompt.txt) — it doesn't replace it. The idea is to not
rely solely on the main conversational model "remembering" to handle a
risk signal well in its free-text response: here the person's message is
classified explicitly and separately, so the help-resources banner can
be triggered deterministically in the UI.

Uses the auxiliary (cheap) model since this is a simple classification
task, it doesn't need the depth of the main conversational model.
"""

import json

from openai import OpenAI

from .config import OPENAI_API_KEY, OPENAI_AUXILIARY_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

# NOTE: this prompt is functional (it classifies the person's Spanish
# message), so it's kept in Spanish rather than translated.
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
        # Fail-safe: if the classifier fails for technical reasons
        # (timeout, network error, invalid JSON), don't block the
        # conversation or break the chat. The main system prompt's own
        # instruction for these cases still acts as a fallback.
        return False