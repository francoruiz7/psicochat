"""
Central backend configuration.

NOTE FOR FUTURE PHASES:
- Name/age injection into the base prompt is still pending (mentioned
  but not yet written). When added, it should go in build_system_prompt,
  AFTER the static SYSTEM_PROMPT block — same as profile_summary — so it
  doesn't break OpenAI's prompt caching on the fixed prefix.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Cheaper/lighter model for auxiliary tasks (risk detection, session
# summary generation). Kept separate from the main conversational model
# so those tasks can use something cheaper without affecting quality of
# the main chat responses.
OPENAI_AUXILIARY_MODEL = os.getenv("OPENAI_AUXILIARY_MODEL", "gpt-4o-mini")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# Timeout for OpenAI API calls, so the user isn't left waiting
# indefinitely if the API doesn't respond.
OPENAI_REQUEST_TIMEOUT_SECONDS = float(os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "30"))

MIN_AGE = 18

SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.txt"

# Storage: SQLite, a single database file for sessions, messages and
# profiles.
DB_PATH = BASE_DIR / "promptpsyco.db"


def load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


SYSTEM_PROMPT = load_system_prompt()

# NOTE: this header text is injected into the model's own system prompt
# (it shapes model behavior, it's not UI text), so it's kept in Spanish
# to match the rest of the therapeutic prompt, which is written for a
# Spanish-speaking conversation.
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
    Builds a session's system prompt. The static SYSTEM_PROMPT block
    always goes first and identical across calls (to benefit from prompt
    caching); the profile summary, if any, is appended after it.
    """
    if not profile_summary:
        return SYSTEM_PROMPT
    return SYSTEM_PROMPT + PROFILE_SECTION_HEADER + profile_summary