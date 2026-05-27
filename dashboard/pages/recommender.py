"""The recommender (and home) page: /. The bulk of the existing layout
lives here so Dash Pages can register it cleanly."""
from __future__ import annotations

import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dash_table, dcc, html

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.recommender import TASTE_COLS, explain, load_catalog, recommend  # noqa: E402
from dashboard.components.masthead import masthead  # noqa: E402
from src.db import user_client  # noqa: E402
from src import auth as A  # noqa: E402
from src.personalization import personalized_defaults  # noqa: E402

dash.register_page(__name__, path="/", title="The Beer Predictor")

# ---------------------------------------------------------------------------
# Data + constants
# ---------------------------------------------------------------------------
CATALOG = load_catalog()
STYLES = sorted(CATALOG["style"].dropna().unique().tolist())
COUNTRIES = sorted(CATALOG["country"].dropna().unique().tolist())
ABV_MIN = float(CATALOG["abv"].min())
ABV_MAX = float(CATALOG["abv"].max())

SLIDER_AXES = [
    ("bitterness", "Bitter", "How sharp / hop-bitter you want it"),
    ("sweetness", "Sweet", "Caramel, residual sugar, malt sweetness"),
    ("maltiness", "Malty", "Bread, biscuit, toast, dark crystal"),
    ("hoppiness", "Hoppy", "Hop aroma + flavour intensity"),
    ("body", "Body", "Mouthfeel from light/crisp to thick/chewy"),
    ("sourness", "Sour", "Tart / acidic / Brettanomyces character"),
    ("abv_preference", "Strength", "Session beer (0) → barleywine (10)"),
]

# Broadsheet palette
PAPER = "#F1E8D3"
PAPER_DEEP = "#E6DABB"
INK = "#1A1410"
INK_SOFT = "#4A382A"
COPPER = "#B0651E"
COPPER_DIM = "#8A4E16"
OXBLOOD = "#6B1F1F"
HAIRLINE = "rgba(26,20,16,0.20)"

# Plotly font stacks
SERIF_STACK = '"Newsreader", "Fraunces", Georgia, "Times New Roman", serif'
MONO_STACK = '"IBM Plex Mono", "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace'


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------
def _fetch_my_ratings() -> list[dict]:
    """Return the signed-in user's rated beers, or [] if anon / error."""
    try:
        if not A.current_user_id():
            return []
        client = user_client()
        if client is None:
            return []
        resp = client.table("user_beers").select("beer_id, rating").execute()
        return list(resp.data or [])
    except Exception:
        return []


def _initial_slider_values() -> dict:
    defaults = personalized_defaults(_fetch_my_ratings(), CATALOG)
    return defaults or {}


def _slider(key: str, label: str, tooltip: str, initial: float = 5.0) -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Span(label),
                    html.Span("info", id=f"tt-{key}", className="tip"),
                ],
                className="axis-label",
            ),
            dbc.Tooltip(tooltip, target=f"tt-{key}", placement="right"),
            dcc.Slider(
                id=f"slider-{key}",
                min=0, max=10, step=0.5, value=initial,
                marks={0: "0", 5: "5", 10: "10"},
                tooltip={"placement": "bottom", "always_visible": False},
            ),
        ],
        className="axis-row",
    )


def _sidebar(initial_values: dict | None = None) -> html.Div:
    iv = initial_values or {}
    sliders = [_slider(k, lab, tip, iv.get(k, 5.0)) for (k, lab, tip) in SLIDER_AXES]
    body = html.Div(
        [
            html.Div("Profile / vii axes", className="section-label"),
            html.Div(sliders, className="stagger"),

            html.Div("Filters", className="section-label"),

            html.Div(
                [
                    html.Div(
                        [
                            html.Span("ABV range"),
                            html.Span("% v/v", className="tip"),
                        ],
                        className="axis-label",
                    ),
                    dcc.RangeSlider(
                        id="flt-abv",
                        min=0, max=14, step=0.5, value=[0, 14],
                        marks={0: "0", 5: "5", 10: "10", 14: "14"},
                        tooltip={"placement": "bottom"},
                    ),
                ],
                className="axis-row",
            ),

            html.Div(
                [
                    html.Div(
                        [html.Span("Styles"),
                         html.Span("multi", className="tip")],
                        className="axis-label",
                    ),
                    dcc.Dropdown(
                        id="flt-styles",
                        options=[{"label": s, "value": s} for s in STYLES],
                        value=[], multi=True, clearable=True,
                        placeholder="any style",
                    ),
                ],
                className="axis-row",
            ),

            html.Div(
                [
                    html.Div(
                        [html.Span("Countries"),
                         html.Span("multi", className="tip")],
                        className="axis-label",
                    ),
                    dcc.Dropdown(
                        id="flt-countries",
                        options=[{"label": c, "value": c} for c in COUNTRIES],
                        value=[], multi=True, clearable=True,
                        placeholder="any country",
                    ),
                ],
                className="axis-row",
            ),

            html.Div(
                [
                    html.Div(
                        [html.Span("Results"),
                         html.Span("3 – 20", className="tip")],
                        className="axis-label",
                    ),
                    dcc.Slider(
                        id="flt-topk", min=3, max=20, step=1, value=10,
                        marks={3: "3", 10: "10", 20: "20"},
                        tooltip={"placement": "bottom"},
                    ),
                ],
                className="axis-row",
            ),

            html.Div(style={"height": "1.4rem"}),
            html.Button("Reset profile", id="btn-reset",
                        n_clicks=0, className="ink-btn"),
        ],
        id="sidebar-body",
        className="sidebar-body",
    )

    toggle = html.Button(
        [
            html.Span("Profile · tap to adjust", className="sidebar-summary"),
            html.Span("▾", className="sidebar-chevron"),
        ],
        id="btn-toggle-sidebar",
        n_clicks=0,
        className="sidebar-toggle",
    )

    return html.Aside(
        [toggle, body],
        id="tasting-card",
        className="tasting-card",
    )


def _main() -> html.Div:
    return html.Main(
        [
            html.Div(
                [
                    html.Div("No. 01 — Tonight's Pour", className="article-no"),
                    html.H2("A glass, suggested."),
                    html.P(
                        "Beers ranked by Euclidean distance over a seven-axis "
                        "taste vector. Match score is 100 × (1 / (1 + distance)) "
                        "— closer to your profile, higher the score.",
                        className="dek",
                    ),
                ],
                className="feature-header",
            ),

            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [html.Span("Fig. I"),
                                 html.Span("Your profile")],
                                className="chart-caption",
                            ),
                            dcc.Loading(
                                dcc.Graph(
                                    id="profile-radar",
                                    config={"displayModeBar": False, "responsive": True},
                                    style={"height": "360px"},
                                    className="radar-graph",
                                ),
                                color=COPPER, type="default",
                            ),
                        ],
                        className="chart-card",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [html.Span("Fig. II"),
                                 html.Span("You vs. top 3")],
                                className="chart-caption",
                            ),
                            dcc.Loading(
                                dcc.Graph(
                                    id="comparison-radar",
                                    config={"displayModeBar": False, "responsive": True},
                                    style={"height": "360px"},
                                    className="radar-graph",
                                ),
                                color=COPPER, type="default",
                            ),
                        ],
                        className="chart-card",
                    ),
                ],
                className="charts-row",
            ),

            html.Section(
                [
                    html.Div(
                        [
                            html.H3("The Ledger"),
                            html.Span("Sorted · highest match first",
                                      className="legend"),
                        ],
                        className="ledger-head",
                    ),
                    dcc.Loading(
                        html.Div(id="reco-table-container", className="ledger"),
                        color=COPPER, type="default",
                    ),
                ],
                className="ledger-section",
            ),
        ],
        className="feature",
    )


def _colophon() -> html.Div:
    return html.Div(
        [
            html.Span("Set in Fraunces, Newsreader & IBM Plex Mono"),
            html.Span("Printed on cream, in copper ink"),
        ],
        className="colophon",
    )


def layout(**_kwargs):
    return html.Div([
        masthead(),
        html.Div([_sidebar(_initial_slider_values()), _main()], className="spread"),
        _colophon(),
    ])


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
SLIDER_IDS = [f"slider-{k}" for k, _, _ in SLIDER_AXES]


@callback(
    Output("profile-radar", "figure"),
    Output("comparison-radar", "figure"),
    Output("reco-table-container", "children"),
    [Input(s_id, "value") for s_id in SLIDER_IDS]
    + [Input("flt-abv", "value"),
       Input("flt-styles", "value"),
       Input("flt-countries", "value"),
       Input("flt-topk", "value")],
)
def _update(*values):
    *slider_values, abv_range, styles, countries, top_k = values
    profile = {k: float(v) for (k, _, _), v in zip(SLIDER_AXES, slider_values)}

    filters: dict[str, object] = {
        "min_abv": abv_range[0],
        "max_abv": abv_range[1],
    }
    if styles:
        filters["styles"] = styles
    if countries:
        filters["countries"] = countries

    recos = recommend(profile, top_k=int(top_k or 10), filters=filters)

    profile_fig = _profile_radar(profile)
    comparison_fig = _comparison_radar(profile, recos)
    table = _reco_table(recos, profile)
    return profile_fig, comparison_fig, table


def _radar_layout(title_text: str, *, legend: bool = False) -> dict:
    return dict(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                range=[0, 10],
                showticklabels=True,
                tickvals=[2, 4, 6, 8, 10],
                tickfont=dict(family=MONO_STACK, size=9, color=INK_SOFT),
                gridcolor=HAIRLINE,
                gridwidth=1,
                linecolor="rgba(0,0,0,0)",
                tickangle=45,
            ),
            angularaxis=dict(
                tickfont=dict(family=MONO_STACK, size=10, color=INK),
                gridcolor=HAIRLINE,
                linecolor=INK,
                linewidth=1,
                rotation=90,
                direction="clockwise",
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.18,
            xanchor="center", x=0.5,
            font=dict(family=SERIF_STACK, size=11, color=INK),
            bgcolor="rgba(0,0,0,0)",
        ),
        title=dict(text="", font=dict(size=1)),
        margin=dict(l=25, r=25, t=20, b=55 if legend else 25),
        autosize=True,
        font=dict(family=SERIF_STACK, color=INK),
    )


def _profile_radar(profile: dict) -> go.Figure:
    cats = ["Bitter", "Sweet", "Malty", "Hoppy", "Body", "Sour", "Strength"]
    keys = ["bitterness", "sweetness", "maltiness", "hoppiness", "body",
            "sourness", "abv_preference"]
    vals = [profile.get(k, 5.0) for k in keys]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=cats + [cats[0]],
        fill="toself",
        name="You",
        line=dict(color=COPPER, width=2.5),
        fillcolor="rgba(176,101,30,0.22)",
        marker=dict(size=6, color=COPPER, line=dict(color=INK, width=1)),
        hovertemplate="<b>%{theta}</b>  %{r:.1f}<extra></extra>",
    ))
    fig.update_layout(**_radar_layout("Your profile", legend=False))
    return fig


def _comparison_radar(profile: dict, recos: pd.DataFrame) -> go.Figure:
    cats = ["Bitter", "Sweet", "Malty", "Hoppy", "Body", "Sour", "Strength"]
    keys = ["bitterness", "sweetness", "maltiness", "hoppiness", "body",
            "sourness", "abv_preference"]
    profile_vals = [profile.get(k, 5.0) for k in keys]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=profile_vals + [profile_vals[0]],
        theta=cats + [cats[0]],
        fill="toself",
        name="You",
        line=dict(color=INK, width=1.5, dash="dot"),
        fillcolor="rgba(26,20,16,0.06)",
        hovertemplate="<b>You · %{theta}</b>  %{r:.1f}<extra></extra>",
    ))

    palette = [COPPER, OXBLOOD, INK_SOFT]
    for i, (_, r) in enumerate(recos.head(3).iterrows()):
        beer_vals = [
            float(r["bitterness"]), float(r["sweetness"]), float(r["maltiness"]),
            float(r["hoppiness"]), float(r["body"]), float(r["sourness"]),
            float(r["abv_normalized"]),
        ]
        name = str(r["name"])[:28]
        fig.add_trace(go.Scatterpolar(
            r=beer_vals + [beer_vals[0]],
            theta=cats + [cats[0]],
            name=name,
            line=dict(color=palette[i % len(palette)], width=2),
            marker=dict(size=4, color=palette[i % len(palette)]),
            hovertemplate=f"<b>{name} · %{{theta}}</b>  %{{r:.1f}}<extra></extra>",
        ))

    fig.update_layout(**_radar_layout("You vs. top 3", legend=True))
    return fig


def _rating_options() -> list[dict]:
    """Half-star scale: 0.5 → 5.0."""
    return [
        {"label": f"{v:g} ★", "value": v}
        for v in [0.5,1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0]
    ]


def _rating_control(beer_id: str, current: float | None,
                    signed_in: bool) -> html.Div:
    if not signed_in:
        return html.Div(
            [
                dcc.Dropdown(
                    id={"role": "rate-disabled", "beer_id": beer_id},
                    options=_rating_options(), value=None,
                    placeholder="account needed", disabled=True,
                    clearable=False, style={"width": "9rem"},
                ),
                dbc.Tooltip(
                    "Create an account to log and rate this beer.",
                    target={"role": "rate-disabled", "beer_id": beer_id},
                    placement="left",
                ),
            ],
            className="lc-rate",
        )
    return html.Div(
        [
            dcc.Dropdown(
                id={"role": "rate", "beer_id": beer_id},
                options=_rating_options(), value=current,
                placeholder="rate", clearable=True,
                style={"width": "9rem"},
            ),
            html.Span(
                "✓" if current else "",
                id={"role": "rate-tick", "beer_id": beer_id},
                className="lc-rate-tick",
            ),
        ],
        className="lc-rate",
    )


def _reco_table(recos: pd.DataFrame, profile: dict) -> html.Div:
    if recos.empty:
        return dbc.Alert(
            "No beers in the cellar match those filters. Loosen the ABV range, or strike a style.",
            color="warning",
        )
    signed_in = A.current_user_id() is not None
    my_ratings = {r["beer_id"]: float(r["rating"]) for r in _fetch_my_ratings()}

    cards = []
    for rank, (_, r) in enumerate(recos.iterrows(), start=1):
        rank_str = f"{rank:02d}"
        beer_id = r["beer_id"]
        name = r["name"]; brewery = r["brewery"]; style = r["style"]
        country = r["country"]
        abv = f"{float(r['abv']):.1f}%"
        ibu = f"{int(round(float(r['ibu'])))}"
        match = f"{float(r['match_score']):.1f}"
        why = explain(r, profile)
        cards.append(html.Article(
            [
                html.Div([html.Span(f"№ {rank_str}", className="lc-rank"),
                          html.Span(f"Match · {match}", className="lc-match")],
                         className="lc-top"),
                html.H4(name, className="lc-name"),
                html.Div(brewery, className="lc-brewery"),
                html.Div(f"{style} · {country} · {abv} · IBU {ibu}", className="lc-meta"),
                html.Div(why, className="lc-why"),
                _rating_control(beer_id, my_ratings.get(beer_id), signed_in),
            ],
            className="ledger-card" + (" first" if rank == 1 else ""),
        ))
    return html.Div(cards, className="ledger-card-view")


# Reset button
@callback(
    [Output(s_id, "value") for s_id in SLIDER_IDS],
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True,
)
def _reset(_n):
    return [5.0] * len(SLIDER_IDS)


@callback(
    Output("tasting-card", "className"),
    Input("btn-toggle-sidebar", "n_clicks"),
    prevent_initial_call=True,
)
def _toggle_sidebar(n_clicks):
    if n_clicks and n_clicks % 2 == 1:
        return "tasting-card collapsed"
    return "tasting-card"


from dash import ALL, MATCH, ctx, no_update  # noqa: E402

@callback(
    Output({"role": "rate-tick", "beer_id": MATCH}, "children"),
    Input({"role": "rate", "beer_id": MATCH}, "value"),
    prevent_initial_call=True,
)
def _save_rating(value):
    triggered = ctx.triggered_id
    if not triggered or "beer_id" not in triggered:
        return no_update
    beer_id = triggered["beer_id"]
    client = user_client()
    if client is None:
        return no_update  # silently no-op for anon; the dropdown is disabled anyway
    uid = A.current_user_id()
    if uid is None:
        return no_update
    try:
        if value is None:
            client.table("user_beers").delete().eq("user_id", uid).eq("beer_id", beer_id).execute()
            return ""
        else:
            client.table("user_beers").upsert(
                {"user_id": uid, "beer_id": beer_id, "rating": float(value)},
                on_conflict="user_id,beer_id",
            ).execute()
            return "✓"
    except Exception:
        return no_update
