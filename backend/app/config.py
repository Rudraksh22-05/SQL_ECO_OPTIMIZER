from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env next to the backend folder so the app works from any working directory.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str
    benchmark_database_url: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        # utf-8-sig tolerates the BOM Windows Notepad may add.
        env_file_encoding="utf-8-sig"
    )


settings = Settings()