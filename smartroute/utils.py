from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model


def start_chat_model(
    model_info: dict[str, str, str],
) -> BaseChatModel:
    return init_chat_model(
        model_info["name"],
        model_provider=model_info["provider"],
        api_key=model_info["api_key"],
    )
