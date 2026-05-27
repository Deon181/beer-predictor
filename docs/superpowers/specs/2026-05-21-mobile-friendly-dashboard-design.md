# Mobile-Friendly Broadsheet — Design

## Context

The Beer Predictor dashboard (`dashboard/app.py`) is a Dash app styled as a print broadsheet — Fraunces/Newsreader serif, IBM Plex Mono accents, cream paper, copper details, hairline rules, paper-grain texture. The desktop experience is finished and well-loved.

The mobile experience is not. Existing responsive behavior is limited to two breakpoints:

- `@media (max-width: 1100px)` — charts row collapses from two columns to one.
- `@media (max-width: 960px)` — the main spread collapses from two columns to one.

Concrete problems at phone widths (~360–414px):

1. The masthead, tasting card, and feature column all use `3rem` horizontal padding — on a 375px screen that consumes 16% of the viewport width on each side.
2. The tasting card uses `position: sticky; top: 0; max-height: 100vh; overflow-y: auto` on desktop. When stacked above the main column on mobile, this creates a nested-scroll region that hides results until the user scrolls past it.
3. The 9-column DataTable (Rank, Beer, Brewery, Style, Country, ABV, IBU, Match, Why) does not fit on phones.
4. Slider handles are 16px square — below the iOS 44pt touch-target minimum.
5. Plotly radars are fixed at 360px tall with 50px L/R margins — squeezed on a 375px screen.

## Goal

Make the dashboard usable and legible on phones (≥360px wide) without altering the desktop experience or the visual identity.

## Non-goals

- No changes to the recommender (`src/recommender.py`).
- No changes to data, callbacks, or filter semantics.
- No change to the desktop layout above 1100px.
- No new files; no new dependencies.

## Breakpoints

| Range | Layout |
|---|---|
| `≥ 1100px` | Desktop — unchanged. Two-column spread, charts side-by-side, full table. |
| `768–1099px` | Tablet — single column (already collapsed at 960px), charts stacked, table keeps all columns with horizontal scroll if needed. Padding tuned but layout same as current. |
| `< 768px` | Phone — collapsible controls, charts stacked with reduced height, table replaced by card view. |

The current `@media (max-width: 960px)` breakpoint is widened to `1099px` so iPad-portrait (768px) gets the single-column layout but not the phone treatment.

## Design

### 1. Sidebar (tasting card) — collapsible at top of page

On phones the tasting card stacks above the main content (existing behavior at the 960px breakpoint) but with two changes:

- The `position: sticky; max-height: 100vh; overflow-y: auto` rules are dropped. The card scrolls with the rest of the page.
- A toggle button is added at the top of the card. Two states:
  - **Expanded** (default on first load): full sliders + filters visible.
  - **Collapsed**: card shows a single summary line and a `▾` chevron, e.g. `Profile · ABV 0–14% · 10 results — tap to adjust`. The values in the summary are static placeholder text in v1 — making them dynamic would require an additional callback. Deferred unless it feels wrong in practice.

Implementation:

- A new `dcc.Store(id="sidebar-collapsed", data=False)` holds the state.
- A `html.Button(id="btn-toggle-sidebar")` flips it.
- A callback returns a CSS class on the tasting-card wrapper (`collapsed` or empty); CSS controls the visual transition.
- Visible only at `< 768px` via CSS — the button is `display: none` on desktop.

Rejected alternatives:

- **Bottom-sheet drawer** — modern but app-like, fights the newspaper metaphor.
- **Just stack with no collapse** — current 960px behavior; on a phone, the sliders eat the entire first screen before any beer appears.

### 2. Ledger (results table) — card view on phones

Below 768px, the DataTable is hidden via CSS and replaced by a stack of "classified-ad" cards built from the same recommendation DataFrame.

Each card structure:

```
╭─────────────────────────────────────────╮
│ № 01                    Match · 87.3    │  rank + match (copper, large)
│                                          │
│ Pliny the Elder                          │  name — serif, 1.15rem, weight 600
│ Russian River Brewing                    │  brewery — italic, INK_SOFT
│                                          │
│ DIPA · USA · 8.0% · IBU 100             │  meta — mono, 0.78rem, uppercase, INK_SOFT
│                                          │
│ Hop-forward and bracingly bitter,        │  why — italic, INK_SOFT, 0.88rem
│ matching your hoppiness and              │
│ bitterness preferences.                  │
╰─────────────────────────────────────────╯
        ──── hairline ────
```

All colors, fonts, and rules already exist in the palette. The first card gets the same `rgba(176,101,30,0.06)` background tint the first table row gets.

Implementation:

- `_reco_table` is renamed `_reco_results` and returns a `html.Div` containing two children:
  - `html.Div(table, className="ledger-table-view")`
  - `html.Div(cards, className="ledger-card-view")`
- CSS controls visibility: `.ledger-card-view { display: none }` above 768px; `.ledger-table-view { display: none }` below 768px.
- The card list is built inline as a `[html.Article(...) for _, r in recos.iterrows()]`.
- The empty-state Alert is unchanged — it's small enough to render fine on either view.

Rejected alternatives:

- **CSS-only responsive table** (turning `<tr>` into block-level cards) — fragile against Dash's DataTable DOM.
- **Horizontal scroll** — reads as a leak, not a design choice.
- **Hide columns progressively** — loses the explanatory "Why" column at the size users most need it.

### 3. Sliders — bigger touch targets

Below 768px:

- `.rc-slider-handle` width/height: 16px → 24px; `margin-top: -7px → -11px`.
- `.rc-slider-rail` and `.rc-slider-track` heights: 1px/2px → 2px/3px.
- `.rc-slider` padding: 12px → 16px vertical to enlarge the tap zone past 44px.
- `dcc.Slider` tooltip already shows on hover/touch; no Python change needed.

### 4. Charts (Plotly radars)

The challenge: `dcc.Graph` figures are rendered server-side, so per-viewport margin/height tuning would need a clientside callback. We sidestep this by letting CSS control the container height and asking Plotly to autosize:

- Remove `height` from the Plotly `layout` dict in `_radar_layout`.
- Add `style={"height": "360px"}` to each `dcc.Graph` and `className="radar-graph"`.
- Set Plotly margins to values that work at both sizes: `l=25, r=25, b=55` (legend) / `b=25` (no legend), `t=20`.
- Add CSS `@media (max-width: 767px) { .radar-graph { height: 300px !important; } }`.
- Set `config={"displayModeBar": False, "responsive": True}` on each Graph (the `responsive` flag is the key).

If the slightly-tighter margins look wrong on desktop after this change, fall back to a `dcc.Store` populated by a clientside callback reading `window.innerWidth`, and branch the layout in `_radar_layout`. Default is to ship without that complexity.

### 5. Padding and container widths

Below 768px:

- `.masthead`: `3.5rem 3rem 1.25rem 3rem` → `1.5rem 1.25rem 0.75rem 1.25rem`
- `.tasting-card`: `1.6rem 1.75rem 2rem 3rem` → `1.25rem 1.25rem 1.5rem 1.25rem`
- `.feature`: `1.6rem 3rem 3rem 3rem` → `1.25rem 1.25rem 2rem 1.25rem`
- `.colophon`: `3rem 3rem 2rem 3rem` → `2rem 1.25rem 1.5rem 1.25rem`; flex-direction column (stack the two spans).

### 6. Typography on phones

Most type already uses `clamp()` with appropriate floors. Two tweaks:

- `.feature-header h2` — `clamp(1.9rem, 3.4vw, 2.8rem)` → `clamp(1.7rem, 6vw, 2.8rem)` (smaller floor so it doesn't dominate on phones).
- `.ledger-head h3` — `1.65rem` → `clamp(1.4rem, 5vw, 1.65rem)`.

### 7. Buttons

Below 768px:

- `.ink-btn` `min-height: 48px`.
- Inside `@media (hover: none)`: disable the `:hover` transform/shadow rules so they don't stick on touch tap.

### 8. Decorations

No changes to:

- Body paper grain (`body::before`)
- Top hairline rule (`body::after`)
- Masthead double rule (`.doublerule`)
- Stagger entrance animation
- `inkBleed` masthead animation

All scale gracefully.

## Implementation scope

All changes in **`dashboard/app.py`**:

- **CSS** — add `@media (max-width: 767px)` block (~100 lines); widen and tune the existing `@media (max-width: 960px)` block (a few line edits).
- **Python** — add card-view rendering in `_reco_table` (renamed `_reco_results`, ~40 lines); add the sidebar collapse toggle button, store, and callback (~20 lines).
- **Plotly** — adjust `_radar_layout` defaults (height, margins).

No changes to:

- `src/recommender.py`
- `src/style_attributes.py`
- `scripts/`, `notebooks/`, `tests/`
- `data/`
- `pyproject.toml`

## Verification

Manual:

- Browser DevTools at 360px, 414px, 768px, 1024px, 1280px — each viewport renders without horizontal scroll, all controls reachable, results visible without nested scrolling.
- Real iPhone (Safari) and Android (Chrome) — slider drag works without page-scroll hijack; tooltips appear on tap; collapse toggle responds.
- Desktop unchanged — visually diff a screenshot of the desktop layout before/after the CSS additions.

Automated:

- Existing `tests/` cover the recommender; mobile is presentation-only, so no new unit tests are needed.
- Add no new tests unless the card-view rendering grows non-trivial logic. (TBD during implementation; default is no new tests.)

## Risks

- **`dcc.Loading` wrapper** currently wraps the single table child. The new wrapper `Div` containing both views is itself the single child, so this should be fine. Verify on first render.
- **Slider tooltip on touch** — `always_visible: False` may hide values on tap. If this is a problem, switch to `True` on phones only (would require a clientside hack since `dcc.Slider` props are set at render time). Defer until observed.
- **Plotly margins shrinkage on desktop** — if 20px L/R margin looks wrong on desktop, fall back to the `dcc.Store` + clientside callback approach described in §4.
- **Page-scroll vs slider drag conflict** — `dcc.Slider` handles this internally; verify on real device.

## Out of scope (explicitly deferred)

- A native-app feel (transitions, gesture support beyond the toggle).
- Reordering content based on viewport (e.g., putting the radar before the sliders on mobile).
- Dark mode.
- Print stylesheet.
- Saving the collapsed state across sessions.
