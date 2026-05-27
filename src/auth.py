"""Thin wrappers around supabase-py auth calls.

Route handlers go through these helpers so:
  - we centralise the session-cookie writing (no scattered duplication)
  - tests can mock at this layer instead of supabase-py
  - we never reference user_metadata in authorization decisions
"""
from __future__ import annotations

from typing import Optional

import flask

from src.db import anon_client, user_client


def _callback_url() -> str:
    """Absolute URL to /auth/callback for this request's host."""
    return flask.url_for("auth.callback", _external=True)


def _write_session(sess) -> None:
    flask.session["access_token"] = sess.access_token
    flask.session["refresh_token"] = sess.refresh_token
    flask.session["user_id"] = sess.user.id


def sign_up(email: str, password: str, display_name: str) -> None:
    """Create a new auth user. Display name lives in user_metadata.

    Note: user_metadata is user-editable and MUST NOT be used in any
    authorization decision. It's purely cosmetic.
    """
    client = anon_client()
    client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "data": {"display_name": display_name},
            "email_redirect_to": _callback_url(),
        },
    })


def sign_in(email: str, password: str) -> None:
    """Sign in with email + password; persists tokens to Flask session."""
    client = anon_client()
    resp = client.auth.sign_in_with_password({"email": email, "password": password})
    _write_session(resp.session)


def sign_out() -> None:
    client = user_client()
    if client is not None:
        try:
            client.auth.sign_out()
        except Exception:
            pass  # we still clear local session even if remote revoke fails
    flask.session.pop("access_token", None)
    flask.session.pop("refresh_token", None)
    flask.session.pop("user_id", None)


def request_password_reset(email: str) -> None:
    client = anon_client()
    client.auth.reset_password_for_email(email, {"redirect_to": _callback_url()})


def update_password(new_password: str) -> None:
    client = user_client()
    if client is None:
        raise RuntimeError("Not signed in")
    client.auth.update_user({"password": new_password})


def exchange_code_for_session(code: str) -> None:
    """Used by /auth/callback for PKCE confirm-email / reset-password flows."""
    client = anon_client()
    resp = client.auth.exchange_code_for_session({"auth_code": code})
    _write_session(resp.session)


def current_user_id() -> Optional[str]:
    return flask.session.get("user_id")
