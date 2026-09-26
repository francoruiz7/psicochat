from typing import Optional, Literal, List
from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    password: str = Field(..., min_length=4, max_length=100)
    # Solo se completan en el flujo de "crear cuenta" (signup). En el
    # flujo de "ya tengo cuenta" (login) van vacíos y se usan los datos
    # ya guardados en el perfil.
    name: Optional[str] = Field(None, max_length=80)
    age: Optional[int] = Field(None, ge=0, le=120)
    city: Optional[str] = Field(None, max_length=120)


class OnboardingResponse(BaseModel):
    allowed: bool
    session_id: Optional[str] = None
    message: Optional[str] = None
    # True si el error es recuperable (ej. contraseña incorrecta, se puede
    # reintentar); False si es un corte definitivo (ej. menor de edad).
    retry: bool = False
    # Nombre a mostrar en el saludo del chat — viene del backend para que
    # funcione igual en el flujo de login (donde el frontend no pide el
    # nombre de nuevo).
    name: Optional[str] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
    risk_flag: bool = False
    risk_resources: Optional[List[str]] = None


class SessionCloseRequest(BaseModel):
    session_id: str


class SessionCloseResponse(BaseModel):
    status: Literal["closed", "closed_no_summary"]