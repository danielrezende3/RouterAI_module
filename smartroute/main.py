from fastapi import FastAPI
from langchain.chat_models import init_chat_model
from pydantic_settings import BaseSettings
import logging


class Settings(BaseSettings):
    openai_api_key: str
    gemini_api_key: str
    anthropic_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI()


@app.get("/")
async def get_welcome_message():
    return {
        "message": "Welcome to SmartRoute API! To access the docs, go to /docs or /redoc",
    }


@app.put("/v1/{text}")
async def invoke_ai_response(text: str):
    models = [
        {
            "name": "gpt-4o-mini",
            "provider": "openai",
            "api_key": settings.openai_api_key,
        },
        {
            "name": "gemini-1.5-flash",
            "provider": "google_genai",
            "api_key": settings.gemini_api_key,
        },
        {
            "name": "claude-3-5-haiku-latest",
            "provider": "anthropic",
            "api_key": settings.anthropic_api_key,
        },
    ]

    for model_info in models:
        try:
            # Initialize the model
            model = init_chat_model(
                model_info["name"],
                model_provider=model_info["provider"],
                api_key=model_info["api_key"],
                timeout=5,
            )
            # Invoke the model
            result = await model.ainvoke(text)
            logging.info(
                f"Model '{model_info['name']}' from provider '{model_info['provider']}' succeeded."
            )
            return {"output": result.content, "model_used": model_info["name"]}
        except Exception as e:  # Replace with actual exception
            logging.error(f"Model '{model_info['name']}' failed with error: {e}")
            continue  # Try the next model

    return {"error": "All models failed to process the request."}
