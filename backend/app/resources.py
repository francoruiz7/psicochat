"""
Help resources shown when risk detection triggers.

Initial version: a simple keyword mapping over the "city" field the
person entered at onboarding (free text, optional). This is
deliberately not real geolocation — we don't want to ask for exact
browser location. If the project grows, this can be replaced with a
more complete per-country table, or an external help-line directory
service.
"""

from typing import Optional

ARGENTINA_KEYWORDS = [
    "argentina", "buenos aires", "caba", "capital federal", "amba",
    "cordoba", "córdoba", "rosario", "mendoza", "la plata",
]

# NOTE: these strings are shown directly to the user in the risk
# banner, so they're kept in Spanish.
ARGENTINA_RESOURCES = [
    "Línea 135 (Ciudad de Buenos Aires): atención telefónica gratuita "
    "las 24 horas para crisis de salud mental.",
    "Línea nacional 0800-345-1435: Programa de Asistencia al Suicida, "
    "gratuita, las 24 horas, todo el país.",
    "Emergencia inmediata: 911.",
]

DEFAULT_RESOURCES = [
    "Comunicate con el número de emergencias de tu país (por ejemplo, "
    "911 o el equivalente local).",
    "Buscá 'línea de prevención del suicidio' junto con el nombre de tu "
    "país para encontrar un recurso gratuito cercano.",
    "Si podés, avisale a alguien de confianza para no estar solo/a en "
    "este momento.",
]


def get_help_resources(city: Optional[str]) -> list[str]:
    if not city:
        return DEFAULT_RESOURCES
    normalized = city.strip().lower()
    if any(keyword in normalized for keyword in ARGENTINA_KEYWORDS):
        return ARGENTINA_RESOURCES
    return DEFAULT_RESOURCES