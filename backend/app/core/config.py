from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str

    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    mfapi_base_url: str = "https://api.mfapi.in/mf"

    scheduler_enabled: bool = True

    ai_provider: str = "rules"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    class Config:
        env_file = ".env"


settings = Settings()
