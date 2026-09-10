"""Application settings loaded from environment variables / .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration.

    Values are read from the process environment first, falling back to
    a `.env` file in the project root.
    """

    GEMINI_API_KEY: str = ""

    APP_HOST: str = "localhost"
    APP_PORT: int = 8000
    DEBUG: bool = True

    DATA_DIR: Path = Path("data")
    OMNIVOICE_MODEL_PATH: Path = Path("models/omnivoice")
    OMNIVOICE_DEVICE: str = "cuda"
    OMNIVOICE_MAX_CONCURRENT: int = 2

    FFMPEG_PATH: str = "ffmpeg"

    GOOGLE_TTS_API_KEY: str = ""
    AZURE_TTS_API_KEY: str = ""
    AZURE_TTS_REGION: str = "eastus"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def db_path(self) -> Path:
        """Path to the SQLite database file inside DATA_DIR."""
        return self.DATA_DIR / "app.db"


settings = Settings()
