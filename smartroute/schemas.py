from typing import Literal, Optional, TypedDict
from pydantic import BaseModel


class InferenceRequest(BaseModel):
    text: str
    fallback: list[str] | None = None
    tier: Optional[Literal["fast", "mid", "reasoning"]] = None
    latency_mode: bool = False
    context_token: Optional[str] = None


class InferencePublic(BaseModel):
    output: str
    model_used: str
    context_token: str


class ModelDict(TypedDict):
    name: str
    provider: str
    api_key: str
    timeout: int
