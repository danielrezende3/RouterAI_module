import asyncio
import logging

from fastapi import FastAPI, HTTPException, status

from smartroute.schemas import InferenceRequest
from smartroute.settings import Settings
from smartroute.utils import start_chat_model

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


@app.get("/")
async def get_welcome_message():
    return {
        "message": "Welcome to SmartRoute API! To access the docs, go to /docs or /redoc",
    }


@app.post(
    "/v1/invoke/", status_code=status.HTTP_200_OK, response_model=InferenceRequest
)
async def invoke_ai_response(inference_request: InferenceRequest):
    if inference_request.fallback:
        try:
            models = [
                start_chat_model(available_models_dict[model])
                for model in inference_request.fallback
            ]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not initialize model: {e}",
            )
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model not available: {e}",
            )
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model not available: {e}",
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

    raise HTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        detail="All models failed to process the request.",
    )
