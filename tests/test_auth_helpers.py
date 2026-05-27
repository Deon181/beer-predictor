"""Tests for src.auth — sign up / in / out helpers.

We mock the supabase client returned by anon_client() and assert the
helpers pass the right arguments through."""
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
def app(monkeypatch: pytest.MonkeyPatch) -> flask.Flask:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    monkeypatch.setenv("FLASK_SECRET_KEY", "k" * 64)
    a = flask.Flask(__name__)
    a.secret_key = "k" * 64
    # Register a stub `auth.callback` endpoint so url_for resolves in tests.
    @a.route("/auth/callback", endpoint="auth.callback")
    def _cb():
        return ""
    return a


def test_sign_up_passes_email_password_and_display_name(app: flask.Flask) -> None:
    from src import auth as A
    mock = MagicMock()
    mock.auth.sign_up.return_value.user.id = "uid-1"
    with patch("src.auth.anon_client", return_value=mock):
        with app.test_request_context():
            A.sign_up("a@b.com", "secret-pw", "Alice")
    args = mock.auth.sign_up.call_args.args[0]
    assert args["email"] == "a@b.com"
    assert args["password"] == "secret-pw"
    assert args["options"]["data"] == {"display_name": "Alice"}
    assert args["options"]["email_redirect_to"].endswith("/auth/callback")


def test_sign_in_writes_tokens_to_session(app: flask.Flask) -> None:
    from src import auth as A
    mock = MagicMock()
    sess = MagicMock()
    sess.access_token = "AT"
    sess.refresh_token = "RT"
    sess.user.id = "uid-1"
    mock.auth.sign_in_with_password.return_value.session = sess
    with patch("src.auth.anon_client", return_value=mock):
        with app.test_request_context():
            A.sign_in("a@b.com", "secret-pw")
            assert flask.session["access_token"] == "AT"
            assert flask.session["refresh_token"] == "RT"
            assert flask.session["user_id"] == "uid-1"


def test_sign_out_clears_session(app: flask.Flask) -> None:
    from src import auth as A
    mock = MagicMock()
    with patch("src.auth.user_client", return_value=mock):
        with app.test_request_context():
            flask.session["access_token"] = "x"
            flask.session["refresh_token"] = "y"
            flask.session["user_id"] = "z"
            A.sign_out()
            assert "access_token" not in flask.session
            assert "refresh_token" not in flask.session
            assert "user_id" not in flask.session


def test_current_user_id_reads_session(app: flask.Flask) -> None:
    from src import auth as A
    with app.test_request_context():
        assert A.current_user_id() is None
        flask.session["user_id"] = "uid-1"
        assert A.current_user_id() == "uid-1"


def test_exchange_code_writes_tokens(app: flask.Flask) -> None:
    from src import auth as A
    mock = MagicMock()
    sess = MagicMock()
    sess.access_token = "AT2"
    sess.refresh_token = "RT2"
    sess.user.id = "uid-2"
    mock.auth.exchange_code_for_session.return_value.session = sess
    with patch("src.auth.anon_client", return_value=mock):
        with app.test_request_context():
            A.exchange_code_for_session("the-code")
            assert flask.session["access_token"] == "AT2"
            assert flask.session["user_id"] == "uid-2"
