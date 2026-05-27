"""Masthead with session-aware account block.

The masthead reads the Flask session and the current request path at
layout-build time (not from a callback) so the first paint already shows
the correct account block.
"""
from __future__ import annotations

import flask
from dash import html

from src import auth as A


def _account_link(signed_in: bool) -> html.Div:
    href = "/profile" if signed_in else "/auth/login"
    return html.Div(
        html.A("Account", href=href, className="nav-strip__link"),
        className="nav-strip__account",
    )


def _current_request_path() -> str:
    if flask.has_request_context():
        return flask.request.path
    return "/"


def masthead() -> html.Header:
    signed_in = A.current_user_id() is not None
    current_path = _current_request_path()
    is_profile = current_path == "/profile"

    if is_profile:
        vol_children = [html.A("← Front page", href="/", className="back-link")]
    else:
        vol_children = [
            html.Span("A taste-profile broadsheet"),
            _account_link(signed_in),
        ]

    return html.Header(
        [
            html.Div(vol_children, className="vol"),
            html.H1([
                "The Beer ",
                html.Span("&", className="amp"),
                " Predictor",
            ]),
            html.P(
                "Seven sliders, an honest catalogue, and the patience to read a chart.",
                className="kicker",
            ),
            html.Hr(className="doublerule"),
        ],
        className="masthead",
    )
