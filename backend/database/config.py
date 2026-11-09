from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=True)

class Settings(BaseSettings):

    DATABASE_URL: str
    API_KEY: str | None = None
    NEON_AUTH_BASE_URL: str | None = None
    NEON_AUTH_JWKS_URL: str | None = None
    NEON_AUTH_ISSUER: str | None = None
    NEON_AUTH_AUDIENCE: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
