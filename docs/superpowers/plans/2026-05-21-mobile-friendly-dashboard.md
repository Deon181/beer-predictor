# Mobile-Friendly Broadsheet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Beer Predictor Dash dashboard usable on phones (≥360px wide) without changing the desktop experience or visual identity.

**Architecture:** All changes in a single file (`dashboard/app.py`). CSS additions live in the embedded `app.index_string`. Python changes touch `_radar_layout`, `_reco_table` (split into table-view + card-view children), and add a sidebar-collapse toggle button + callback. No new files, no new dependencies. The recommender (`src/recommender.py`) is untouched.

**Tech Stack:** Dash 2.x, dash-bootstrap-components, Plotly. Verification is browser-based (Chrome/Firefox DevTools device emulation) — the existing pytest suite covers `src/`, not UI.

**Verification convention:** Each task ends with a manual browser check. The local dev server runs at `http://127.0.0.1:8050` via `uv run python dashboard/app.py`. Toggle DevTools' device toolbar (Ctrl+Shift+M / Cmd+Shift+M) and test at **375px (iPhone), 414px, 768px (iPad portrait), 1024px, 1280px**. The dev server hot-reloads CSS-in-`index_string` changes only after a manual reload of the browser tab.

**Spec:** `docs/superpowers/specs/2026-05-21-mobile-friendly-dashboard-design.md`

---

### Task 1: Viewport meta tag + start the dev server baseline

**Files:**
- Modify: `dashboard/app.py:60-66` (the `dash.Dash(...)` constructor call)

This is blocker #1 — without a viewport meta tag, mobile browsers render at desktop width and zoom out, defeating all responsive CSS.

- [ ] **Step 1: Start the dev server in the background and confirm it loads**

Run:
```bash
uv run python dashboard/app.py
```

Open `http://127.0.0.1:8050` in a desktop browser. Confirm the broadsheet renders. Open DevTools, switch to device emulation at 375px width. Note that the page is rendered at ~1100px and scaled down — controls are tiny. This is the baseline.

- [ ] **Step 2: Add viewport meta tag via `meta_tags` parameter**

Edit `dashboard/app.py`, change the `dash.Dash(...)` call:

```python
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="The Beer Predictor — A Taste-Profile Broadsheet",
    meta_tags=[
        {"name": "viewport",
         "content": "width=device-width, initial-scale=1, viewport-fit=cover"},
    ],
)
```

- [ ] **Step 3: Restart the dev server, reload the browser at 375px**

Stop and restart `uv run python dashboard/app.py` (the `index_string` is rendered at startup; meta_tags require a restart). Reload the browser.

Expected: the page now renders at the device's actual width (375px) instead of being scaled-down desktop. Everything is too cramped — that's fine, that's what the next tasks fix.

- [ ] **Step 4: Commit**

```bash
git add dashboard/app.py
git commit -m "feat(dashboard): add viewport meta tag for mobile rendering"
```

---

### Task 2: Widen tablet breakpoint and add mobile CSS scaffold

**Files:**
- Modify: `dashboard/app.py` — inside `app.index_string`, the `<style>` block

We make two structural CSS changes: widen the existing `960px` breakpoint (which collapses the spread to one column) to `1099px` so it covers small tablets, and add a new `767px` breakpoint as the home for all phone-specific overrides.

- [ ] **Step 1: Widen the existing single-column breakpoint**

Find this block (around line 221–224 in current source):

```css
@media (max-width: 960px) {
    .spread { grid-template-columns: 1fr; }
    .tasting-card { border-right: 0 !important; border-bottom: 1px solid var(--hairline); }
}
```

Change `960px` to `1099px`:

```css
@media (max-width: 1099px) {
    .spread { grid-template-columns: 1fr; }
    .tasting-card {
        border-right: 0 !important;
        border-bottom: 1px solid var(--hairline);
        position: static;
        max-height: none;
        overflow-y: visible;
    }
}
```

The added `position: static; max-height: none; overflow-y: visible` overrides drop the sticky/nested-scroll behavior at tablet width and below.

- [ ] **Step 2: Add the mobile (`< 768px`) media query block**

Immediately after the `1099px` block, add an empty mobile block as scaffolding for the next tasks:

```css
/* ───── Mobile (phone) ──────────────────────────────────────────── */
@media (max-width: 767px) {
    /* Padding + masthead trim */
    .masthead { padding: 1.5rem 1.25rem 0.75rem 1.25rem; }
    .tasting-card { padding: 1.25rem 1.25rem 1.5rem 1.25rem; }
    .feature { padding: 1.25rem 1.25rem 2rem 1.25rem; }
    .colophon {
        margin: 2rem 1.25rem 1.5rem 1.25rem;
        flex-direction: column;
        gap: 0.4rem;
    }

    /* Headings — smaller floors */
    .feature-header h2 {
        font-size: clamp(1.7rem, 6vw, 2.8rem);
    }
    .ledger-head h3 {
        font-size: clamp(1.4rem, 5vw, 1.65rem);
    }
    .masthead .vol {
        flex-direction: column;
        gap: 0.2rem;
        align-items: flex-start;
    }
    .masthead .kicker {
        font-size: 1.0rem;
    }
}
```

- [ ] **Step 3: Restart the dev server and verify**

```bash
# Ctrl+C the running server, then:
uv run python dashboard/app.py
```

Reload the browser at 375px. Expected:
- The two-column spread is now a single column at 768px and below (previously only at 960px and below).
- Horizontal padding is visibly tighter — no more 48px gutters eating the screen.
- The masthead headline and feature h2 are smaller.
- The colophon footer wraps to two lines instead of squashing.

Test at 1024px (iPad landscape): should now show the *tablet* single-column layout (not desktop). Test at 1280px (desktop): unchanged.

- [ ] **Step 4: Commit**

```bash
git add dashboard/app.py
git commit -m "feat(dashboard): widen tablet breakpoint, add mobile CSS scaffold"
```

---

### Task 3: Slider touch targets + button sizing

**Files:**
- Modify: `dashboard/app.py` — inside the `@media (max-width: 767px)` block added in Task 2

- [ ] **Step 1: Add slider and button overrides to the mobile block**

Append to the `@media (max-width: 767px)` block (before the closing `}`):

```css
    /* Sliders — bigger touch targets */
    .rc-slider { padding: 16px 0; }
    .rc-slider-rail { height: 2px !important; opacity: 0.35; }
    .rc-slider-track { height: 3px !important; margin-top: -1px; }
    .rc-slider-handle {
        width: 24px !important;
        height: 24px !important;
        margin-top: -11px !important;
    }

    /* Buttons */
    .ink-btn {
        min-height: 48px;
        font-size: 0.78rem;
    }
```

- [ ] **Step 2: Add a hover-suppression block for touch devices**

Below the `767px` block, add:

```css
/* Disable hover transforms on touch devices so they don't stick after tap */
@media (hover: none) {
    .ink-btn:hover {
        transform: none !important;
        box-shadow: none !important;
        background: transparent !important;
        color: var(--ink) !important;
    }
    .ink-btn:active {
        background: var(--ink) !important;
        color: var(--paper) !important;
    }
}
```

- [ ] **Step 3: Restart server, reload at 375px, verify**

Expected:
- Slider handles are visibly larger and easier to grab.
- The "Reset profile" button is taller (48px tall).
- On a real touch device (or DevTools touch mode), tapping the button briefly inverts (active state) but doesn't stick in the hover state after release.

- [ ] **Step 4: Commit**

```bash
git add dashboard/app.py
git commit -m "feat(dashboard): mobile slider hit targets and button sizing"
```

---

### Task 4: Plotly radar — CSS-driven height + tighter margins

**Files:**
- Modify: `dashboard/app.py:881-917` (`_radar_layout` function)
- Modify: `dashboard/app.py:753-757, 768-772` (the two `dcc.Graph` calls in `_main()`)
- Modify: `dashboard/app.py` inside the `@media (max-width: 767px)` block

- [ ] **Step 1: Update `_radar_layout` — remove height, tighten margins**

Find `_radar_layout` (starts ~line 881). Replace the `margin=...` and `height=...` lines:

```python
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
```

Note: removed `height=...`, added `autosize=True`, dropped margins to `l=25, r=25, t=20, b=55/25`.

- [ ] **Step 2: Add `style` + `className` + `responsive` to both `dcc.Graph` calls**

In `_main()`, find both `dcc.Graph` calls (currently at lines ~754 and ~769). Update each:

Find:
```python
dcc.Loading(
    dcc.Graph(id="profile-radar",
              config={"displayModeBar": False}),
    color=COPPER, type="default",
),
```

Replace with:
```python
dcc.Loading(
    dcc.Graph(
        id="profile-radar",
        config={"displayModeBar": False, "responsive": True},
        style={"height": "360px"},
        className="radar-graph",
    ),
    color=COPPER, type="default",
),
```

Do the same for the second `dcc.Graph` (id `comparison-radar`).

- [ ] **Step 3: Add the CSS rule for mobile radar height**

Append to the `@media (max-width: 767px)` block:

```css
    /* Charts — shorter on phones */
    .radar-graph { height: 300px !important; }
```

- [ ] **Step 4: Restart server, verify charts at multiple widths**

Reload the browser at 375px, 768px, 1024px, 1280px. Expected:
- At 375px and below, the radars are 300px tall.
- At 768px+, the radars are 360px tall.
- Margins look reasonable at all widths — no clipped labels, no awkward whitespace.
- The legend on the "You vs. top 3" chart still appears below and is readable.

If desktop margins feel too tight visually, the spec's fallback (clientside callback into a `dcc.Store`) is available — but only if observed to be a problem.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app.py
git commit -m "feat(dashboard): make Plotly radars responsive via CSS height"
```

---

### Task 5: Sidebar collapse toggle

**Files:**
- Modify: `dashboard/app.py:641-724` (`_sidebar()`)
- Modify: `dashboard/app.py:837-841` (`app.layout`)
- Modify: `dashboard/app.py` near the end of callbacks section (~line 1080)
- Modify: `dashboard/app.py` inside `@media (max-width: 767px)` block and add desktop hide rule

A toggle button at the top of the tasting card collapses/expands the controls. Only visible at `< 768px`. The button text/chevron flips; the body of the sidebar gets `display: none` when collapsed.

- [ ] **Step 1: Update `_sidebar()` to add toggle + wrapper around the body**

Replace the entire `_sidebar()` function (currently at line 641):

```python
def _sidebar() -> html.Div:
    sliders = [_slider(k, lab, tip) for (k, lab, tip) in SLIDER_AXES]
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
```

The structural changes: the body of the card is wrapped in a `Div(id="sidebar-body")`; a new `Button(id="btn-toggle-sidebar")` is prepended; the outer `Aside` gets `id="tasting-card"`.

- [ ] **Step 2: Add the toggle callback**

Find the existing reset callback (around line 1083). Add a new callback below it:

```python
@callback(
    Output("tasting-card", "className"),
    Input("btn-toggle-sidebar", "n_clicks"),
    prevent_initial_call=True,
)
def _toggle_sidebar(n_clicks):
    if n_clicks and n_clicks % 2 == 1:
        return "tasting-card collapsed"
    return "tasting-card"
```

- [ ] **Step 3: Add CSS — hide toggle on desktop, show on mobile, hide body when collapsed**

Add this block **outside** any media query (so it always applies):

```css
/* ───── Sidebar toggle (mobile collapse) ───────────────────────── */
.sidebar-toggle {
    display: none; /* hidden on desktop */
    width: 100%;
    background: transparent;
    border: 0;
    border-bottom: 1px solid var(--hairline);
    padding: 0.9rem 0;
    margin-bottom: 1rem;
    cursor: pointer;
    font-family: var(--mono);
    font-size: 0.7rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink);
    text-align: left;
    align-items: center;
    justify-content: space-between;
}
.sidebar-toggle .sidebar-chevron {
    color: var(--copper);
    font-size: 0.95rem;
    transition: transform 0.18s ease;
}
.tasting-card.collapsed .sidebar-toggle .sidebar-chevron {
    transform: rotate(-90deg);
}
.tasting-card.collapsed .sidebar-body {
    display: none;
}
```

Then add to the `@media (max-width: 767px)` block:

```css
    /* Sidebar collapse toggle visible only on phones */
    .sidebar-toggle { display: flex !important; }
```

- [ ] **Step 4: Restart server, verify on phone width**

Reload at 375px:
- A "Profile · tap to adjust ▾" bar appears at the top of the tasting card.
- Tapping it hides all sliders/filters; chevron rotates.
- Tapping again restores them.
- At 1024px+: no toggle bar visible; everything looks as before.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app.py
git commit -m "feat(dashboard): add collapsible sidebar on phone widths"
```

---

### Task 6: Card view for ledger results

**Files:**
- Modify: `dashboard/app.py:978-1079` (`_reco_table` function)
- Modify: `dashboard/app.py` inside `@media (max-width: 767px)` block and add desktop hide rules

Replace the single DataTable with a wrapper Div containing both the existing table (visible at ≥768px) and a new card list (visible at <768px). Both built from the same `recos` DataFrame.

- [ ] **Step 1: Refactor `_reco_table` to return dual-view container**

Replace the existing `_reco_table` function:

```python
def _reco_table(recos: pd.DataFrame, profile: dict) -> html.Div:
    if recos.empty:
        return dbc.Alert(
            "No beers in the cellar match those filters. "
            "Loosen the ABV range, or strike a style.",
            color="warning",
        )

    rows = []
    cards = []
    for rank, (_, r) in enumerate(recos.iterrows(), start=1):
        rank_str = f"{rank:02d}"
        name = r["name"]
        brewery = r["brewery"]
        style = r["style"]
        country = r["country"]
        abv = f"{float(r['abv']):.1f}%"
        ibu = f"{int(round(float(r['ibu'])))}"
        match = f"{float(r['match_score']):.1f}"
        why = explain(r, profile)

        rows.append({
            "Rank": rank_str,
            "Beer": name,
            "Brewery": brewery,
            "Style": style,
            "Country": country,
            "ABV": abv,
            "IBU": f"{int(round(float(r['ibu']))):>3d}",
            "Match": match,
            "Why": why,
        })

        cards.append(
            html.Article(
                [
                    html.Div(
                        [
                            html.Span(f"№ {rank_str}", className="lc-rank"),
                            html.Span(f"Match · {match}", className="lc-match"),
                        ],
                        className="lc-top",
                    ),
                    html.H4(name, className="lc-name"),
                    html.Div(brewery, className="lc-brewery"),
                    html.Div(
                        f"{style} · {country} · {abv} · IBU {ibu}",
                        className="lc-meta",
                    ),
                    html.Div(why, className="lc-why"),
                ],
                className="ledger-card" + (" first" if rank == 1 else ""),
            )
        )

    table = dash_table.DataTable(
        data=rows,
        columns=[
            {"name": "№",         "id": "Rank"},
            {"name": "Beer",      "id": "Beer"},
            {"name": "Brewery",   "id": "Brewery"},
            {"name": "Style",     "id": "Style"},
            {"name": "Country",   "id": "Country"},
            {"name": "ABV",       "id": "ABV"},
            {"name": "IBU",       "id": "IBU"},
            {"name": "Match",     "id": "Match"},
            {"name": "Notes",     "id": "Why"},
        ],
        sort_action="native",
        page_action="none",
        style_table={"overflowX": "auto", "border": "0"},
        style_as_list_view=True,
        style_cell={
            "fontFamily": SERIF_STACK,
            "fontSize": "0.95rem",
            "textAlign": "left",
            "padding": "0.55rem 0.6rem",
            "whiteSpace": "normal",
            "height": "auto",
            "backgroundColor": "transparent",
            "color": INK,
            "border": "0",
        },
        style_header={
            "backgroundColor": "transparent",
            "fontWeight": 600,
            "color": INK,
            "fontFamily": MONO_STACK,
            "fontSize": "0.66rem",
            "letterSpacing": "0.2em",
            "textTransform": "uppercase",
            "borderTop": f"1px solid {INK}",
            "borderBottom": f"1px solid {INK}",
        },
        style_cell_conditional=[
            {"if": {"column_id": "Rank"},
             "fontFamily": '"Fraunces", Georgia, serif',
             "fontSize": "1.4rem",
             "fontWeight": 800,
             "color": COPPER,
             "width": "3rem",
             "textAlign": "left",
             "fontVariantNumeric": "lining-nums tabular-nums"},
            {"if": {"column_id": "Beer"},
             "fontWeight": 600, "fontSize": "1.02rem"},
            {"if": {"column_id": "Brewery"},
             "fontStyle": "italic", "color": INK_SOFT},
            {"if": {"column_id": "Style"},
             "fontFamily": MONO_STACK, "fontSize": "0.78rem",
             "textTransform": "uppercase", "letterSpacing": "0.08em",
             "color": INK_SOFT},
            {"if": {"column_id": "Country"},
             "fontFamily": MONO_STACK, "fontSize": "0.78rem",
             "color": INK_SOFT},
            {"if": {"column_id": "ABV"},
             "fontFamily": MONO_STACK, "fontSize": "0.85rem",
             "fontVariantNumeric": "tabular-nums",
             "color": INK, "width": "4rem"},
            {"if": {"column_id": "IBU"},
             "fontFamily": MONO_STACK, "fontSize": "0.85rem",
             "fontVariantNumeric": "tabular-nums",
             "color": INK_SOFT, "width": "3.5rem"},
            {"if": {"column_id": "Match"},
             "fontFamily": MONO_STACK, "fontSize": "0.95rem",
             "fontWeight": 600,
             "fontVariantNumeric": "tabular-nums",
             "color": COPPER, "width": "4.5rem"},
            {"if": {"column_id": "Why"},
             "fontStyle": "italic", "color": INK_SOFT,
             "fontSize": "0.88rem", "maxWidth": "32rem"},
        ],
        style_data_conditional=[
            {"if": {"row_index": 0},
             "backgroundColor": "rgba(176,101,30,0.06)"},
        ],
    )

    return html.Div(
        [
            html.Div(table, className="ledger-table-view"),
            html.Div(cards, className="ledger-card-view"),
        ]
    )
```

The function still has the same name and signature; the type hint changes from `dash_table.DataTable | html.Div` to `html.Div`. Callers in `_update()` already treat it as a generic component, no other change needed.

- [ ] **Step 2: Add card-view CSS (always-on, not in any media query)**

Add this block (place it near the existing `.ledger` styles, around line 522):

```css
/* ───── Ledger card view (mobile) ──────────────────────────────── */
.ledger-card-view { display: none; }

.ledger-card {
    padding: 1.1rem 0 1rem 0;
    border-bottom: 1px solid var(--hairline-soft);
}
.ledger-card.first {
    background: rgba(176, 101, 30, 0.06);
    padding-left: 0.6rem;
    padding-right: 0.6rem;
    margin-left: -0.6rem;
    margin-right: -0.6rem;
}
.ledger-card .lc-top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.45rem;
}
.ledger-card .lc-rank {
    font-family: var(--display);
    font-size: 1.5rem;
    font-weight: 800;
    color: var(--copper);
    font-variant-numeric: lining-nums tabular-nums;
}
.ledger-card .lc-match {
    font-family: var(--mono);
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--copper);
    letter-spacing: 0.04em;
    font-variant-numeric: tabular-nums;
}
.ledger-card .lc-name {
    font-family: var(--serif);
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--ink);
    margin: 0 0 0.1rem 0;
    line-height: 1.25;
}
.ledger-card .lc-brewery {
    font-family: var(--serif);
    font-style: italic;
    color: var(--ink-soft);
    font-size: 0.95rem;
    margin-bottom: 0.55rem;
}
.ledger-card .lc-meta {
    font-family: var(--mono);
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-soft);
    margin-bottom: 0.55rem;
}
.ledger-card .lc-why {
    font-family: var(--serif);
    font-style: italic;
    color: var(--ink-soft);
    font-size: 0.92rem;
    line-height: 1.45;
}
```

- [ ] **Step 3: Toggle which view is visible per breakpoint**

Add to the `@media (max-width: 767px)` block:

```css
    /* Ledger: cards instead of table */
    .ledger-table-view { display: none; }
    .ledger-card-view { display: block; }
```

- [ ] **Step 4: Restart server, verify at multiple widths**

Reload at:
- **375px**: ledger renders as a stack of cards. First card has a faint copper tint. Each card shows rank, match, name, brewery, meta line, why.
- **768px and above**: ledger renders as the existing table (no cards visible).
- **1280px**: unchanged from before.

Verify with extreme filters (e.g., bitterness=10, hoppiness=10, sweetness=0) that the cards display the expected IPAs. With filters that return no beers (ABV range 0-0.1, or impossible country combo): the warning Alert renders correctly at all widths.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app.py
git commit -m "feat(dashboard): add card-view ledger for phone widths"
```

---

### Task 7: End-to-end verification + run tests

**Files:** No file changes — verification only.

- [ ] **Step 1: Run the existing pytest suite to confirm no regressions**

```bash
uv run pytest tests/ -v
```

Expected: all tests pass. (None of our changes touch `src/recommender.py` or `src/style_attributes.py`, so they should pass unchanged.)

- [ ] **Step 2: Full browser walkthrough at every breakpoint**

Restart the dev server one more time. For each width, open in DevTools device emulation and confirm:

| Width | Spread | Charts | Ledger | Sidebar toggle |
|---|---|---|---|---|
| 1280px (desktop) | 2-col | 2-col | table | hidden |
| 1024px (iPad land) | 1-col | 1-col | table | hidden |
| 768px (iPad port) | 1-col | 1-col | table | hidden |
| 414px (large phone) | 1-col | 1-col | cards | visible |
| 375px (iPhone) | 1-col | 1-col | cards | visible |
| 360px (small Android) | 1-col | 1-col | cards | visible |

At each phone width, verify:
- No horizontal scroll on the page body.
- Sliders are tap-able without scrolling the page.
- Tap the toggle: card collapses cleanly, chevron rotates, tap again expands.
- Tap "Reset profile": all 7 sliders return to 5.
- Apply a filter (e.g., a Style): card list updates.

- [ ] **Step 3: Real-device test (if available)**

If you have a physical phone, navigate to `http://<your-laptop-ip>:8050`. Confirm the slider tooltip appears on tap-and-hold, sliders track touches, and there's no scroll hijack. Skip if no device available.

- [ ] **Step 4: Final commit (only if any tweaks made during verification)**

If verification turned up any visual polish needed, fix and commit:

```bash
git add dashboard/app.py
git commit -m "fix(dashboard): mobile polish from verification"
```

Otherwise, no commit needed.

---

## Self-Review

**Spec coverage:**
- §1 Sidebar collapsible → Task 5 ✓
- §2 Card view → Task 6 ✓
- §3 Sliders bigger → Task 3 ✓
- §4 Plotly responsive → Task 4 ✓
- §5 Padding/container → Task 2 ✓
- §6 Typography → Task 2 ✓
- §7 Buttons → Task 3 ✓
- §8 Decorations unchanged → no task needed ✓
- Blocker: viewport meta tag (not in spec but caught during planning) → Task 1 ✓

**Placeholder scan:** None. All code blocks contain the exact lines to write.

**Type consistency:** `_reco_table` signature stays the same (only the return-type hint widens to `html.Div`). The `_radar_layout` signature is unchanged. Component IDs introduced (`tasting-card`, `sidebar-body`, `btn-toggle-sidebar`) are used consistently across the layout, CSS, and callback.

**Risk acknowledged but not blocking:**
- Plotly desktop margin tuning may need the clientside-callback fallback if the new (25, 25) margins look too tight at 1280px. Verification step in Task 4 catches this.
- The viewport meta tag requires a server restart to take effect (Dash builds index_string at import time).
