from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files.

    All required secrets (``DATABASE_URL``, ``REDIS_URL``, ``SERVICE_SECRET``,
    ``RS256_PUBLIC_KEY``) must be provided via the environment or a
    ``.env`` / ``.env.local`` file.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SERVICE_NAME: str = "user-service"
    SERVICE_VERSION: str = "0.1.0"
    SERVICE_ID: str = "user-service"
    SERVICE_SECRET: str

    DATABASE_URL: str
    REDIS_URL: str

    AUTH_SERVICE_URL: str = "http://auth-service:8080"
    FILE_SERVICE_URL: str = "http://file-service:8080"
    RS256_PUBLIC_KEY: str

    @field_validator("RS256_PUBLIC_KEY", mode="before")
    @classmethod
    def expand_newlines(cls, value: str) -> str:
        """Normalise escaped newlines in the RS256 public key.

        Some deployment environments store the key with literal ``\\n`` escape
        sequences rather than real newlines. This validator converts them so
        that the key parses correctly.

        Args:
            value: The raw ``RS256_PUBLIC_KEY`` string from the environment.

        Returns:
            The key string with ``\\n`` replaced by actual newline characters.
        """
        return value.replace("\\n", "\n")

    APP_ENV: str = "production"
    WORKERS: int = 4
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    NOISE_LOG_LEVEL: str = "WARNING"
    SKIP_SERVICE_AUTH: bool = False


settings = Settings()
