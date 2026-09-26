from typing import Optional, Literal, List
from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    password: str = Field(..., min_length=4, max_length=100)
    # Only filled in during the "signup" flow. In the "login" flow
    # (existing account) they're left empty and the profile's stored
    # data is used instead.
    name: Optional[str] = Field(None, max_length=80)
    age: Optional[int] = Field(None, ge=0, le=120)
    city: Optional[str] = Field(None, max_length=120)


class OnboardingResponse(BaseModel):
    allowed: bool
    session_id: Optional[str] = None
    message: Optional[str] = None
    # True if the error is recoverable (e.g. wrong password, can retry);
    # False if it's a hard stop (e.g. underage).
    retry: bool = False
    # Name to show in the chat greeting — comes from the backend so it
    # also works in the login flow (where the frontend doesn't ask for
    # the name again).
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