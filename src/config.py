"""Centralised env-driven settings. Loaded once at app startup."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_publishable_key: str
    flask_secret_key: str


def load_settings(dotenv_path: Path | None = None) -> Settings:
    """Read settings from env (loading `.env` first if present).

    Raises RuntimeError if any required key is missing — fail loud at startup
    rather than mid-request.
    """
    if dotenv_path is None:
        dotenv_path = ROOT / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)

    def _require(name: str) -> str:
        v = os.environ.get(name)
        if not v:
            raise RuntimeError(
                f"{name} is required but not set. "
                f"Copy .env.example to .env and fill it in."
            )
        return v

    return Settings(
        supabase_url=_require("SUPABASE_URL"),
        supabase_publishable_key=_require("SUPABASE_PUBLISHABLE_KEY"),
        flask_secret_key=_require("FLASK_SECRET_KEY"),
    )
