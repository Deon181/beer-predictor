"""Supabase client factories.

`anon_client()` — unauthenticated; uses the `anon` Postgres role for RLS.
`user_client()` — Flask-request-scoped; bound to the signed-in user's JWT
so RLS sees `auth.uid()` and rows are authorized correctly.
"""
from __future__ import annotations

from typing import Optional

import flask
from supabase import Client, create_client

from src.config import load_settings

_SETTINGS = None


def _settings():
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = load_settings()
    return _SETTINGS


def anon_client() -> Client:
    """Unauthenticated client — uses the `anon` Postgres role for RLS."""
    s = _settings()
    return create_client(s.supabase_url, s.supabase_publishable_key)


def user_client() -> Optional[Client]:
    """Return a Supabase client bound to the signed-in user, or None."""
    access = flask.session.get("access_token")
    refresh = flask.session.get("refresh_token")
    if not access or not refresh:
        return None

    s = _settings()
    client = create_client(s.supabase_url, s.supabase_publishable_key)
    client.auth.set_session(access, refresh)

    sess = client.auth.get_session()
    if sess is not None and (
        sess.access_token != access or sess.refresh_token != refresh
    ):
        flask.session["access_token"] = sess.access_token
        flask.session["refresh_token"] = sess.refresh_token
    return client
