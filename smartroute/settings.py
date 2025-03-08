from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logging.getLogger("openai").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("uvicorn").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("anthropic").setLevel(logging.CRITICAL)
logging.getLogger("grpc").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("watchfiles").setLevel(logging.CRITICAL)


class Settings(BaseSettings):
    openai_api_key: str
    gemini_api_key: str
    anthropic_api_key: str
    database_url: str
    model_config = SettingsConfigDict(env_file=".env")
