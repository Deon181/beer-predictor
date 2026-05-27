"""Env-loader contract: required keys raise when absent."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_settings_reads_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    monkeypatch.setenv("FLASK_SECRET_KEY", "a" * 64)
    from src import config
    settings = config.load_settings()
    assert settings.supabase_url == "https://x.supabase.co"
    assert settings.supabase_publishable_key == "sb_publishable_test"
    assert settings.flask_secret_key == "a" * 64


def test_settings_missing_required_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    from src import config
    # Pass a non-existent dotenv path so a real .env at the repo root
    # doesn't repopulate the deleted env vars.
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        config.load_settings(dotenv_path=tmp_path / "absent.env")
