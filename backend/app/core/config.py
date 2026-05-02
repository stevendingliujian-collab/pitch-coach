from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://pitchcoach:pitchcoach_dev@localhost:5432/pitchcoach"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO / OSS
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket: str = "pitchcoach"
    minio_secure: bool = False

    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # LLM
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_max_tokens: int = 8192
    llm_temperature: float = 0.3

    # TTS
    fish_audio_api_key: str = ""
    fish_audio_base_url: str = "https://api.fish.audio/v1"
    tts_provider: str = "fish_audio"

    # ASR
    asr_provider: str = "paraformer"
    paraformer_api_key: str = ""

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # File upload limits
    max_ppt_size_mb: int = 50
    max_ppt_pages: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
