"""Tests for src.db — client factories.

We mock `supabase-py`'s create_client so tests stay offline."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import flask
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def app_with_session(monkeypatch: pytest.MonkeyPatch) -> flask.Flask:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    monkeypatch.setenv("FLASK_SECRET_KEY", "k" * 64)
    app = flask.Flask(__name__)
    app.secret_key = "k" * 64
    return app


def test_anon_client_uses_url_and_publishable_key(app_with_session: flask.Flask) -> None:
    from src import db
    with patch("src.db.create_client") as mock_create:
        mock_create.return_value = MagicMock()
        db.anon_client()
    mock_create.assert_called_once_with("https://x.supabase.co", "sb_publishable_test")


def test_user_client_returns_none_when_session_empty(app_with_session: flask.Flask) -> None:
    from src import db
    with app_with_session.test_request_context():
        assert db.user_client() is None


def test_user_client_binds_tokens_from_session(app_with_session: flask.Flask) -> None:
    from src import db
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.access_token = "access-old"
    mock_session.refresh_token = "refresh-old"
    mock_client.auth.get_session.return_value = mock_session

    with patch("src.db.create_client", return_value=mock_client):
        with app_with_session.test_request_context():
            flask.session["access_token"] = "access-old"
            flask.session["refresh_token"] = "refresh-old"
            client = db.user_client()

    assert client is mock_client
    mock_client.auth.set_session.assert_called_once_with("access-old", "refresh-old")


def test_user_client_persists_refreshed_tokens(app_with_session: flask.Flask) -> None:
    from src import db
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.access_token = "access-new"   # different from session value
    mock_session.refresh_token = "refresh-new"
    mock_client.auth.get_session.return_value = mock_session

    with patch("src.db.create_client", return_value=mock_client):
        with app_with_session.test_request_context():
            flask.session["access_token"] = "access-old"
            flask.session["refresh_token"] = "refresh-old"
            db.user_client()
            assert flask.session["access_token"] == "access-new"
            assert flask.session["refresh_token"] == "refresh-new"
