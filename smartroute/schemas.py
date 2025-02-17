from pydantic import BaseModel


class InferenceRequest(BaseModel):
    text: str
    fallback: list[str] | None = None
