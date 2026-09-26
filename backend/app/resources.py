"""
Recursos de ayuda mostrados cuando se dispara la detección de riesgo.

Versión inicial: mapeo simple por palabras clave sobre el campo "ciudad"
que la persona cargó en el onboarding (texto libre, opcional). No es
geolocalización real — es deliberadamente así, para no pedir ubicación
exacta del navegador. Si el proyecto crece, esto se puede reemplazar por
una tabla más completa por país, o un servicio externo de directorios de
líneas de ayuda.
"""

from typing import Optional

ARGENTINA_KEYWORDS = [
    "argentina", "buenos aires", "caba", "capital federal", "amba",
    "cordoba", "córdoba", "rosario", "mendoza", "la plata",
]

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
