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
    "chatgpt-fast": {
        "name": "chatgpt-4o-mini",
        "provider": "openai",
        "api_key": settings.openai_api_key,
    },
    "gemini-fast": {
        "name": "gemini-2.0-flash-lite",
        "provider": "google_genai",
        "api_key": settings.gemini_api_key,
    },
    "claude-fast": {
        "name": "claude-3-5-haiku-20241022",
        "provider": "anthropic",
        "api_key": settings.anthropic_api_key,
    },
}

MID_MODELS = {
    "chatgpt-mid": {
        "name": "chatgpt-4o",
        "provider": "openai",
        "api_key": settings.openai_api_key,
    },
    "claude-mid": {
        "name": "claude-3-5-sonnet-latest",
        "provider": "anthropic",
        "api_key": settings.anthropic_api_key,
    },
    "gemini-mid": {
        "name": "gemini-2.0-flash",
        "provider": "google_genai",
        "api_key": settings.gemini_api_key,
    },
}

REASONING_MODELS = {
    "chatgpt-reasoning": {
        "name": "o3-mini-2025-01-31",
        "provider": "openai",
        "api_key": settings.openai_api_key,
    },
    "gemini-reasoning": {
        "name": "gemini-2.0-pro-exp-02-05",
        "provider": "google_genai",
        "api_key": settings.gemini_api_key,
    },
    "claude-reasoning": {
        "name": "claude-3-7-sonnet-20250219",
        "provider": "anthropic",
        "api_key": settings.anthropic_api_key,
    },
}

ALL_MODELS = {**FAST_MODELS, **MID_MODELS, **REASONING_MODELS}
