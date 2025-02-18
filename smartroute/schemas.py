from pydantic import BaseModel


class InferenceRequest(BaseModel):
    text: str
    fallback: list[str] | None = None
    tier_model: str | None = None


class InferencePublic(BaseModel):
    output: str
    model_used: str
