from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("uvicorn").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("anthropic").setLevel(logging.ERROR)
logging.getLogger("grpc").setLevel(logging.ERROR)


class Settings(BaseSettings):
    openai_api_key: str
    gemini_api_key: str
    anthropic_api_key: str
    database_url: str
    model_config = SettingsConfigDict(env_file=".env")
