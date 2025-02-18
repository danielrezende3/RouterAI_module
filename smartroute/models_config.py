from smartroute.settings import Settings
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model


def start_chat_model(
    model_info: dict[str, str],
) -> BaseChatModel:
    return init_chat_model(
        model_info["name"],
        model_provider=model_info["provider"],
        api_key=model_info["api_key"],
    )


def get_chat_instances(
    models: dict[str, dict[str, str]],
) -> list[BaseChatModel]:
    return [start_chat_model(model_info[1]) for model_info in models.items()]


settings = Settings()  # type: ignore


FAST_MODELS = {
    "gpt-4o-mini": {
        "name": "gpt-4o-mini",
        "provider": "openai",
        "api_key": settings.openai_api_key,
    },
    "gemini-2.0-flash-lite-preview-02-05": {
        "name": "gemini-2.0-flash-lite-preview-02-05",
        "provider": "google_genai",
        "api_key": settings.gemini_api_key,
    },
    "claude-3-5-haiku-latest": {
        "name": "claude-3-5-haiku-latest",
        "provider": "anthropic",
        "api_key": settings.anthropic_api_key,
    },
}

MID_MODELS = {
    "gpt-4o": {
        "name": "gpt-4o",
        "provider": "openai",
        "api_key": settings.openai_api_key,
    },
    "claude-3-5-sonnet-latest": {
        "name": "claude-3-5-sonnet-latest",
        "provider": "anthropic",
        "api_key": settings.anthropic_api_key,
    },
}

REASONING_MODELS = {
    "gpt-o3-mini": {
        "name": "o1-mini-2024-09-12",
        "provider": "openai",
        "api_key": settings.openai_api_key,
    },
    "gemini-1.5-pro": {
        "name": "gemini-1.5-pro",
        "provider": "google_genai",
        "api_key": settings.gemini_api_key,
    },
    "claude-3-opus-latest": {
        "name": "claude-3-opus-latest",
        "provider": "anthropic",
        "api_key": settings.anthropic_api_key,
    },
}

ALL_MODELS = {**FAST_MODELS, **MID_MODELS, **REASONING_MODELS}
