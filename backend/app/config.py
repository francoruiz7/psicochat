"""
Configuración central del backend.

Fase 2: se suma el perfil evolutivo (resumen acumulado entre sesiones).

NOTA PARA FASES FUTURAS:
- Falta incorporar la inyección de nombre/edad al prompt base (mencionada
  pero todavía no redactada). Cuando se agregue, sumarla en
  build_system_prompt DESPUÉS del bloque estático de SYSTEM_PROMPT, igual
  que el profile_summary — así no se rompe el prompt caching del bloque
  fijo (ver nota de costos: el caching de OpenAI requiere que el prefijo
  se mantenga idéntico entre llamadas).
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Modelo liviano para tareas auxiliares (Fase 3: detección de riesgo,
# Fase 2: generación de resúmenes). Separado del modelo conversacional
# principal para poder usar algo más barato/rápido en esas tareas.
OPENAI_AUXILIARY_MODEL = os.getenv("OPENAI_AUXILIARY_MODEL", "gpt-4o-mini")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# Fase 3: timeout de las llamadas a OpenAI, para no dejar al usuario
# esperando indefinidamente si la API no responde.
OPENAI_REQUEST_TIMEOUT_SECONDS = float(os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "30"))

MIN_AGE = 18

# Tope aproximado (en palabras) para el perfil evolutivo acumulado.
# Al regenerarlo en cada cierre de sesión, le pedimos al modelo auxiliar
# que condense en vez de solo agregar, para que esto no crezca sin límite
# turno a turno y siga siendo barato de inyectar en cada sesión nueva.
PROFILE_SUMMARY_MAX_WORDS = 400

SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.txt"

# Fase 4: storage pasó de JSON plano a SQLite. Un solo archivo de base de
# datos para sesiones, mensajes y perfiles.
DB_PATH = BASE_DIR / "promptpsyco.db"


def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


SYSTEM_PROMPT = load_system_prompt()

PROFILE_SECTION_HEADER = (
    "\n\n---\n\n"
    "CONTEXTO DE SESIONES ANTERIORES\n\n"
    "Lo siguiente es un resumen acumulado de sesiones anteriores con esta "
    "misma persona. Usalo para dar continuidad (patrones ya identificados, "
    "formulaciones que la persona descubrió, temas recurrentes), pero sin "
    "forzar referencias a esto si no viene al caso en lo que la persona "
    "traiga hoy.\n\n"
)


def build_system_prompt(profile_summary: Optional[str]) -> str:
    """
    Arma el system prompt de una sesión. El bloque SYSTEM_PROMPT va
    siempre primero e idéntico entre llamadas (para aprovechar el
    prompt caching); el resumen de perfil, si existe, se agrega después.
    """
    if not profile_summary:
        return SYSTEM_PROMPT
    return SYSTEM_PROMPT + PROFILE_SECTION_HEADER + profile_summary
