import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI, APIError, APITimeoutError

from .config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_REQUEST_TIMEOUT_SECONDS,
    MIN_AGE,
    build_system_prompt,
)
from .models import (
    OnboardingRequest,
    OnboardingResponse,
    ChatRequest,
    ChatResponse,
    SessionCloseRequest,
    SessionCloseResponse,
)
from . import storage
from . import summary as summary_module
from . import risk as risk_module
from . import resources as resources_module

router = APIRouter()

client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_REQUEST_TIMEOUT_SECONDS)

BLOCKED_MINOR_MESSAGE = (
    "Este espacio está pensado para personas mayores de 18 años. "
    "Lamentablemente no podemos iniciar el proceso. "
    "Si necesitás hablar con alguien, te recomendamos acudir a un adulto "
    "de confianza o a un profesional de salud mental."
)

INVALID_USERNAME_MESSAGE = (
    "Ese nombre de usuario no es válido. Usá solo letras, números, "
    "guiones o guiones bajos."
)

WRONG_PASSWORD_MESSAGE = "Contraseña incorrecta para ese nombre de usuario."

MISSING_SIGNUP_DATA_MESSAGE = (
    "Para crear una cuenta nueva necesitamos también tu nombre y tu edad."
)

GENERIC_ERROR_MESSAGE = (
    "Hubo un problema generando la respuesta. Intentá de nuevo en un momento."
)


@router.post("/onboarding", response_model=OnboardingResponse)
def onboarding(payload: OnboardingRequest):
    username = storage.normalize_username(payload.username)
    if not username:
        return OnboardingResponse(
            allowed=False, message=INVALID_USERNAME_MESSAGE, retry=True
        )

    existing_profile = storage.load_profile(username)

    if existing_profile:
        # ---- Flujo LOGIN: ya existe la cuenta ----
        authenticated = storage.authenticate_profile(username, payload.password)
        if authenticated is None:
            return OnboardingResponse(
                allowed=False, message=WRONG_PASSWORD_MESSAGE, retry=True
            )
        session_id = storage.create_session(
            name=authenticated["name"],
            age=authenticated["age"],
            city=authenticated["city"],
            username=username,
        )
        return OnboardingResponse(
            allowed=True, session_id=session_id, name=authenticated["name"]
        )

    # ---- Flujo SIGNUP: cuenta nueva ----
    if payload.name is None or payload.age is None:
        return OnboardingResponse(
            allowed=False, message=MISSING_SIGNUP_DATA_MESSAGE, retry=True
        )

    if payload.age < MIN_AGE:
        return OnboardingResponse(
            allowed=False, message=BLOCKED_MINOR_MESSAGE, retry=False
        )

    storage.get_or_create_profile(
        username=username,
        password=payload.password,
        name=payload.name,
        age=payload.age,
        city=payload.city,
    )
    session_id = storage.create_session(
        name=payload.name, age=payload.age, city=payload.city, username=username
    )
    return OnboardingResponse(allowed=True, session_id=session_id, name=payload.name)


def _build_call_context(session_id: str):
    session = storage.load_session(session_id)
    profile_summary = None
    username = session.get("username")
    if username:
        profile = storage.load_profile(username)
        if profile:
            profile_summary = profile.get("profile_summary") or None

    system_prompt = build_system_prompt(profile_summary)
    openai_messages = [{"role": "system", "content": system_prompt}]
    for m in session["messages"]:
        openai_messages.append({"role": m["role"], "content": m["content"]})
    return session, openai_messages


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    """Endpoint sin streaming — más simple para probar con curl/Postman."""
    session = storage.load_session(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    is_risk = risk_module.assess_risk(payload.message)
    risk_resources = (
        resources_module.get_help_resources(session.get("city"))
        if is_risk
        else None
    )

    storage.append_message(payload.session_id, "user", payload.message)
    _, openai_messages = _build_call_context(payload.session_id)

    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=openai_messages,
        )
    except (APIError, APITimeoutError):
        raise HTTPException(status_code=502, detail=GENERIC_ERROR_MESSAGE)

    reply = completion.choices[0].message.content
    storage.append_message(payload.session_id, "assistant", reply)

    return ChatResponse(reply=reply, risk_flag=is_risk, risk_resources=risk_resources)


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest):
    """
    Igual que /chat pero devuelve la respuesta como Server-Sent Events,
    token a token.

    Eventos: "risk" (una vez, si corresponde), "token" (uno por
    fragmento), "error" (si algo falla), "done" (al finalizar).
    """
    session = storage.load_session(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    is_risk = risk_module.assess_risk(payload.message)
    risk_resources = (
        resources_module.get_help_resources(session.get("city"))
        if is_risk
        else []
    )

    storage.append_message(payload.session_id, "user", payload.message)
    _, openai_messages = _build_call_context(payload.session_id)

    def event_generator():
        if is_risk:
            yield _sse("risk", {"resources": risk_resources})

        full_reply_parts = []
        try:
            stream = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=openai_messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_reply_parts.append(delta)
                    yield _sse("token", {"text": delta})
        except (APIError, APITimeoutError):
            yield _sse("error", {"message": GENERIC_ERROR_MESSAGE})
            return

        reply_text = "".join(full_reply_parts)
        if reply_text:
            storage.append_message(payload.session_id, "assistant", reply_text)

        yield _sse("done", {"risk_flag": is_risk})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/session/close", response_model=SessionCloseResponse)
def close_session(payload: SessionCloseRequest):
    session = storage.load_session(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    username = session.get("username")
    storage.mark_session_closed(payload.session_id)

    if not username or not session["messages"]:
        return SessionCloseResponse(status="closed_no_summary")

    profile = storage.load_profile(username)
    previous_summary = profile.get("profile_summary", "") if profile else ""

    try:
        new_summary = summary_module.generate_summary(
            previous_summary=previous_summary,
            session_messages=session["messages"],
        )
        storage.update_profile_summary(username, new_summary)
    except (APIError, APITimeoutError):
        return SessionCloseResponse(status="closed_no_summary")

    return SessionCloseResponse(status="closed")