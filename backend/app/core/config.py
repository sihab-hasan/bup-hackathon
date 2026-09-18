from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = BACKEND_ROOT.parent
load_dotenv(REPOSITORY_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env", override=True)


def _positive_float(name: str, default: float) -> float:
    value = float(getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    app_env: str
    llm_timeout_seconds: float
    llm_provider: str
    llm_model: str
    gemini_api_key: str | None
    optimizer_timeout_seconds: float
    cors_origins: tuple[str, ...]


@lru_cache
def get_settings() -> Settings:
    origins = tuple(
        origin.strip()
        for origin in getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
        ).split(",")
        if origin.strip()
    )
    return Settings(
        app_name=getenv("APP_NAME", "GridWise API"),
        app_env=getenv("APP_ENV", "development"),
        llm_timeout_seconds=_positive_float("LLM_TIMEOUT_SECONDS", 20),
        llm_provider=getenv("LLM_PROVIDER", "gemini").strip().lower(),
        llm_model=getenv("LLM_MODEL", "gemini-2.5-flash").strip(),
        gemini_api_key=(getenv("GEMINI_API_KEY") or "").strip() or None,
        optimizer_timeout_seconds=_positive_float("OPTIMIZER_TIMEOUT_SECONDS", 20),
        cors_origins=origins,
    )
