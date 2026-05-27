"""User profile page: /profile.

Sections:
  - Editable display_name
  - Personalized radar (Fig. III) — current personalized defaults
  - Ledger of rated beers (sortable, with Remove action)
"""
from __future__ import annotations

import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, dcc, html, no_update

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.recommender import load_catalog
from src.db import user_client
from src import auth as A
from src.personalization import personalized_defaults
from dashboard.components.masthead import masthead
# Import via `pages.recommender` (not `dashboard.pages.recommender`) so
# we share the same module object Dash's auto-discovery loaded. Importing
# the same physical file under a different module name creates a second
# module instance, which causes a duplicate `dash.register_page(...)` at
# path "/" — and Dash can serve the duplicate (with layout=None) instead
# of the real one, dropping the masthead's me-strip from the rendered DOM.
from pages.recommender import (  # noqa: E402
    _colophon, _radar_layout, COPPER, INK, OXBLOOD, SERIF_STACK,
)

dash.register_page(__name__, path="/profile", title="Profile · The Beer Predictor")
CATALOG = load_catalog()


def _personalized_radar(profile: dict | None) -> go.Figure:
    cats = ["Bitter","Sweet","Malty","Hoppy","Body","Sour","Strength"]
    keys = ["bitterness","sweetness","maltiness","hoppiness","body","sourness","abv_preference"]
    vals = [profile.get(k, 5.0) for k in keys] if profile else [5.0]*7
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]], fill="toself",
        name="Your taste", line=dict(color=COPPER, width=2.5),
        fillcolor="rgba(176,101,30,0.22)",
        marker=dict(size=6, color=COPPER, line=dict(color=INK, width=1)),
        hovertemplate="<b>%{theta}</b>  %{r:.1f}<extra></extra>",
    ))
    fig.update_layout(**_radar_layout("Your taste", legend=False))
    return fig


def _fetch_profile_and_ratings():
    try:
        client = user_client()
        if client is None:
            return None, []
        uid = A.current_user_id()
        if uid is None:
            return None, []
        prof = client.table("profiles").select("display_name").eq("id", uid).single().execute().data
        ratings = client.table("user_beers").select("beer_id, rating, rated_at").execute().data or []
        return prof, ratings
    except Exception:
        return None, []


def _ledger_table(ratings: list[dict], catalog: pd.DataFrame) -> html.Div:
    if not ratings:
        return html.Div("Rate a few beers to populate your ledger.", className="lc-empty")
    cat_by_id = catalog.set_index("beer_id")
    rows = []
    for r in sorted(ratings, key=lambda x: x.get("rated_at", ""), reverse=True):
        bid = r["beer_id"]
        if bid not in cat_by_id.index:
            continue
        c = cat_by_id.loc[bid]
        rows.append(html.Tr([
            html.Td(c["name"]),
            html.Td(c["brewery"]),
            html.Td(c["style"]),
            html.Td(f"★ {float(r['rating']):g}"),
            html.Td(html.Button("Remove",
                                id={"role": "prof-remove", "beer_id": bid},
                                n_clicks=0, className="linkish")),
        ]))
    return html.Table(
        [
            html.Thead(html.Tr([html.Th("Beer"), html.Th("Brewery"),
                                html.Th("Style"), html.Th("Rating"), html.Th("")])),
            html.Tbody(rows),
        ],
        className="profile-ledger",
    )


def layout(**_kwargs):
    if not A.current_user_id():
        return html.Div([
            masthead(),
            html.Main(
                html.Div(
                    [html.H2("Create an account to view your profile."),
                     html.A("Account", href="/auth/login", className="ink-btn")],
                    className="profile-gate"),
                className="feature"),
            _colophon(),
        ])
    prof, ratings = _fetch_profile_and_ratings()
    display_name = (prof or {}).get("display_name", "")
    defaults = personalized_defaults(ratings, CATALOG)

    caption_right = ["Personalized profile"]
    if defaults is None:
        caption_right.append(
            html.Span(" ⓘ", className="chart-hint",
                      **{"data-tip": "Rate beers ≥ 4★ to populate this chart"}))

    return html.Div([
        masthead(),
        html.Main(
            [
                html.Div([
                    html.Div("No. 02 — Reader's Card", className="article-no"),
                    html.H2("Your profile."),
                ], className="feature-header"),

                html.Section(
                    html.Div([
                        html.Span("Display name", className="prof-label"),
                        html.Div([
                            dcc.Input(id="prof-name", type="text",
                                      value=display_name, maxLength=50,
                                      className="prof-input",
                                      placeholder="Enter a display name"),
                            html.Button("Save", id="prof-name-save",
                                        n_clicks=0, className="prof-save"),
                        ], className="prof-field"),
                        html.Span("", id="prof-name-status",
                                  className="prof-status"),
                    ], className="prof-row"),
                    className="profile-name-section",
                ),

                html.Section(
                    [
                        html.Div([html.Span("Fig. III"),
                                  html.Span(caption_right)],
                                 className="chart-caption"),
                        dcc.Graph(
                            figure=_personalized_radar(defaults),
                            config={"displayModeBar": False, "responsive": True},
                            style={"height": "360px"},
                            className="radar-graph",
                        ),
                    ],
                    className="chart-card",
                ),

                html.Section(
                    [
                        html.H3("Your ledger"),
                        html.Div(_ledger_table(ratings, CATALOG), id="prof-ledger"),
                    ],
                    className="ledger-section",
                ),

                html.Section(
                    html.Form(
                        html.Button("Sign out", type="submit",
                                    className="ink-btn ink-btn--secondary"),
                        action="/auth/logout",
                        method="post",
                    ),
                    className="profile-signout-section",
                ),
            ],
            className="feature",
        ),
        _colophon(),
    ])


@callback(
    Output("prof-name-status", "children"),
    Input("prof-name-save", "n_clicks"),
    State("prof-name", "value"),
    prevent_initial_call=True,
)
def _save_display_name(_n, name):
    name = (name or "").strip()
    if not (1 <= len(name) <= 50):
        return "Name must be 1–50 chars."
    client = user_client()
    uid = A.current_user_id()
    if client is None or uid is None:
        return "Account required."
    try:
        client.table("profiles").update({"display_name": name}).eq("id", uid).execute()
        return "Saved."
    except Exception as e:  # noqa: BLE001
        return f"Save failed: {e}"


@callback(
    Output("prof-ledger", "children"),
    Input({"role": "prof-remove", "beer_id": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def _remove(_n_clicks_list):
    triggered = ctx.triggered_id
    if not triggered or "beer_id" not in triggered:
        return no_update
    if not any(_n_clicks_list or []):
        return no_update
    client = user_client()
    uid = A.current_user_id()
    if client is None or uid is None:
        return no_update
    try:
        client.table("user_beers").delete().eq("user_id", uid).eq("beer_id", triggered["beer_id"]).execute()
    except Exception:
        return no_update
    _, ratings = _fetch_profile_and_ratings()
    return _ledger_table(ratings, CATALOG)
