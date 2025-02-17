import logging

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from langchain.chat_models import init_chat_model
from pydantic import BaseModel
from pydantic_settings import BaseSettings


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
    fallback = (
        inference_request.fallback
        if inference_request.fallback
        else [model[1] for model in available_models_dict.items()]
    )
    if fallback:
        try:
            models = [available_models_dict[model] for model in fallback]
        except KeyError as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"Model {e} is not available.",
            )
    else:
        models = [model[1] for model in available_models_dict.items()]

    text = inference_request.text
    for model_info in models:
        try:
            model = init_chat_model(
                model_info["name"],
                model_provider=model_info["provider"],
                api_key=model_info["api_key"],
                timeout=5,
            )
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
        try:
            # Initialize the model

            # Invoke the model
            result = await model.ainvoke(text)
            logging.info(
                f"Model '{model_info['name']}' from provider '{model_info['provider']}' succeeded."
            )
            return {"output": result.content, "model_used": model_info["name"]}
        except Exception as e:  # Replace with actual exception
            logging.error(f"Model '{model_info['name']}' failed with error: {e}")
            continue  # Try the next model

    return JSONResponse(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        content="All models failed to process the request.",
    )
