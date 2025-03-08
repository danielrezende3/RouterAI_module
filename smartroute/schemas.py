from typing import Literal, Optional, TypedDict
from pydantic import BaseModel


class InvokeRequest(BaseModel):
    text: str
    fallback: list[str] | None = None
    tier: Optional[Literal["fast", "mid", "reasoning"]] = None
    latency_mode: bool = False


class InvokeWithContextRequest(InvokeRequest):
    context_token: Optional[str] = None


class InvokeResponse(BaseModel):
    output: str
    model_used: str
    context_token: str


class ModelDict(TypedDict):
    name: str
    provider: str
    api_key: str
    timeout: int
