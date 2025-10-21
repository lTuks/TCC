from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = "Assistente de Redação PT-BR"
    app_env: str = Field("dev", alias="APP_ENV")
    secret_key: str = Field(default=None, alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(120, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    database_url: str = Field(default=None, alias="DATABASE_URL")

    llm_provider: str = Field(default=None, alias="LLM_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_model: str = Field(default=None, alias="LLM_MODEL")

    rate_limit_window_seconds: int = Field(60, alias="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_max_calls: int = Field(30, alias="RATE_LIMIT_MAX_CALLS")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
