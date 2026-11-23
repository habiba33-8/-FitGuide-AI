from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    """Tiny .env loader so we do not need an extra dependency."""
    for p in (Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env", Path(__file__).resolve().parents[2] / ".env"):
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", GEMINI_BASE).rstrip("/"))
    # Comma separated. First is tried first; the next ones are used when a model is rate limited or missing.
    models: tuple[str, ...] = field(default_factory=lambda: tuple(
        m.strip() for m in os.getenv("LLM_MODELS", "gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(",") if m.strip()))
    timeout_s: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_S", "40")))
    visit_webhook: str = field(default_factory=lambda: os.getenv("VISIT_LOG_WEBHOOK_URL", ""))
    allowed_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.api_key)


def get_settings() -> Settings:
    return Settings()
