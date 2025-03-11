from smartroute.schemas import AiModelDict
from smartroute.settings import Settings
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model
import random

settings = Settings()  # type: ignore
FAST_TIMEOUT = 60  # 1 minute
REASONING_TIMEOUT = 300  # 5 minutes
FAST_MODELS: dict[str, AiModelDict] = {
    "chatgpt-fast": {
        "name": "gpt-4o-mini-2024-07-18",
        "provider": "openai",
        "api_key": settings.openai_api_key,
        "timeout": FAST_TIMEOUT,
    },
    "gemini-fast": {
        "name": "gemini-2.0-flash-lite",
        "provider": "google_genai",
        "api_key": settings.gemini_api_key,
        "timeout": FAST_TIMEOUT,
    },
    "claude-fast": {
        "name": "claude-3-5-haiku-20241022",
        "provider": "anthropic",
        "api_key": settings.anthropic_api_key,
        "timeout": FAST_TIMEOUT,
    },
}
MID_MODELS: dict[str, AiModelDict] = {
    "chatgpt-mid": {
        "name": "gpt-4o-2024-11-20",
        "provider": "openai",
        "api_key": settings.openai_api_key,
        "timeout": FAST_TIMEOUT,
    },
    "claude-mid": {
        "name": "claude-3-5-sonnet-latest",
        "provider": "anthropic",
        "api_key": settings.anthropic_api_key,
        "timeout": FAST_TIMEOUT,
    },
    "gemini-mid": {
        "name": "gemini-2.0-flash",
        "provider": "google_genai",
        "api_key": settings.gemini_api_key,
        "timeout": FAST_TIMEOUT,
    },
}
REASONING_MODELS: dict[str, AiModelDict] = {
    "chatgpt-reasoning": {
        "name": "o3-mini-2025-01-31",
        "provider": "openai",
        "api_key": settings.openai_api_key,
        "timeout": REASONING_TIMEOUT,
    },
    "gemini-reasoning": {
        "name": "gemini-2.0-pro-exp-02-05",
        "provider": "google_genai",
        "api_key": settings.gemini_api_key,
        "timeout": REASONING_TIMEOUT,
    },
    "claude-reasoning": {
        "name": "claude-3-7-sonnet-20250219",
        "provider": "anthropic",
        "api_key": settings.anthropic_api_key,
        "timeout": REASONING_TIMEOUT,
    },
}
ALL_MODELS = {**FAST_MODELS, **MID_MODELS, **REASONING_MODELS}
TIER_MODEL_MAPPING = {
    "fast": FAST_MODELS,
    "mid": MID_MODELS,
    "reasoning": REASONING_MODELS,
}


def start_chat_model(
    model_info: AiModelDict,
) -> BaseChatModel:
    return init_chat_model(
        model_info["name"],
        model_provider=model_info["provider"],
        api_key=model_info["api_key"],
    )


def get_effective_timeout(model_configs: dict[str, AiModelDict]) -> float:
    """
    Computes the effective timeout for a given set of model configurations.

    The effective timeout is determined by taking the maximum timeout
    from all models in the configuration.
    """
    return max(model_info["timeout"] for model_info in model_configs.values())


def get_chat_instances(
    models: dict[str, AiModelDict],
) -> list[BaseChatModel]:
    # * Is this necessary?
    items = list(models.items())
    random.shuffle(items)
    return [start_chat_model(model_info) for _, model_info in items]


def get_model_name(model) -> str:
    """
    Extracts a user-friendly name from the model instance.

    The function checks for common attributes that indicate the model's name.
    If the name contains a forward slash, only the part after the last slash is returned.
    """
    name = getattr(model, "model", None) or getattr(
        model, "model_name", "unknown_model"
    )
    return name.split("/")[-1] if "/" in name else name
