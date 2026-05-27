"""Beer Predictor — Dash dashboard bootstrap.

Run with:
    python dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc

_DIR = Path(__file__).resolve().parent
ROOT = _DIR.parent
for p in (str(ROOT), str(_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.config import load_settings  # noqa: E402
from dashboard.auth_routes import auth_bp  # noqa: E402

_SETTINGS = load_settings()

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="The Beer Predictor — A Taste-Profile Broadsheet",
    meta_tags=[
        {"name": "viewport",
         "content": "width=device-width, initial-scale=1, viewport-fit=cover"},
    ],
)
server = app.server
server.secret_key = _SETTINGS.flask_secret_key
server.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
)
server.register_blueprint(auth_bp)

app.index_string = """<!DOCTYPE html>
<html lang="en">
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,800;9..144,900&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    {%css%}
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>"""

from dash import html  # noqa: E402
app.layout = html.Div([dash.page_container])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)
