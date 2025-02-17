import logging

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import asyncio
from smartroute.utils import start_chat_model


class Settings(BaseSettings):
    openai_api_key: str
    gemini_api_key: str
    anthropic_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI()

available_models_dict = {
    "gpt-4o-mini": {
        "name": "gpt-4o-mini",
        "provider": "openai",
        "api_key": settings.openai_api_key,
    },
    "gemini-1.5-flash": {
        "name": "gemini-1.5-flash",
        "provider": "google_genai",
        "api_key": settings.gemini_api_key,
    },
    "claude-3-5-haiku-latest": {
        "name": "claude-3-5-haiku-latest",
        "provider": "anthropic",
        "api_key": settings.anthropic_api_key,
    },
}

available_models = [
    start_chat_model(model_info[1]) for model_info in available_models_dict.items()
]


class InferenceRequest(BaseModel):
    text: str
    fallback: list[str] | None = None


@app.get("/")
async def get_welcome_message():
    return {
        "message": "Welcome to SmartRoute API! To access the docs, go to /docs or /redoc",
    }


@app.post("/v1/invoke")
async def invoke_ai_response(inference_request: InferenceRequest):
    if inference_request.fallback:
        try:
            models = [
                start_chat_model(available_models_dict[model])
                for model in inference_request.fallback
            ]
        except ValueError as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"Could not initialize model: {e}",
            )
        except ImportError as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"Could not import model: {e}",
            )
    else:
        models = available_models

    text = inference_request.text
    for model in models:
        try:
            # Invoke the model
            result = await asyncio.wait_for(model.ainvoke(text), timeout=5.0)
            if hasattr(model, "model"):
                model_name = model.model.split("/")[1]
            elif hasattr(model, "model_name"):
                model_name = model.model_name
            return {"output": result.content, "model_used": model_name}
        except asyncio.TimeoutError:
            logging.error(f"Model {model} timed out.")
            continue  # Try the next model

    return JSONResponse(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        content="All models failed to process the request.",
    )
