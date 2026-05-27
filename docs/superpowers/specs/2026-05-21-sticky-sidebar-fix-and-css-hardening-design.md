# Sticky-Sidebar Fix & CSS Hardening — Design

## Context

After the mobile-friendly broadsheet work (`2026-05-21-mobile-friendly-dashboard-design.md`) the dashboard regressed: on phones and tablets the tasting card (filters + profile sliders) stays fixed on screen, and as the user scrolls down, the radar graphs slide behind it.

The cause is not a missing rule — the mobile override exists. It is a CSS **source-order bug**.

In `dashboard/app.py` the embedded stylesheet declares, in this order:

1. `@media (max-width: 1099px) { .tasting-card { position: static; max-height: none; overflow-y: visible; } }` (line 225–234)
2. `.tasting-card { ... position: sticky; top: 0; max-height: 100vh; overflow-y: auto; }` (line 337–347)

Media queries do not raise specificity. With equal specificity the later rule wins. The base rule with `position: sticky` is declared *after* the media query that tries to switch to `position: static`, so on every viewport the sidebar is sticky. The `border-right: 0 !important` override survives only because it carries `!important`; the position/overflow overrides do not.

Two other forces compound the visual: the tasting card has `background: linear-gradient(to right, transparent calc(100% - 1px), var(--paper-deep) ...)` — so its background is *transparent except for a 1px right edge*. With nothing behind it, the graphs are visible through the card as the user scrolls. The card is not opaque on top of them; it is genuinely sticky and they are scrolling through.

## Goal

1. Fix the bug: the tasting card must not stick to the viewport at any width below the desktop breakpoint (≤ 1099px).
2. Add a regression test so this exact class of CSS source-order bug is caught by `pytest`, not by a user opening the app on their phone.
3. Reduce the surface area for this bug class in the future without rewriting the dashboard.

## Non-goals

- No changes to the recommender (`src/`), data, or callback semantics.
- No changes to the desktop layout above 1099px (visual identity preserved).
- No new heavy dependencies (Playwright, Selenium, stylelint, etc.). Goal is fast unit-level signal.
- No splitting `dashboard/app.py` into multiple Python modules. That is a worthwhile refactor but out of scope here.
- No dark mode, no print stylesheet, no new features.

## Design

### 1. The fix — move CSS to `dashboard/assets/style.css`, mobile-first

Dash auto-loads any `.css` file under `dashboard/assets/`, attaching it to every page. We extract the entire `<style>` block currently embedded in `app.index_string` into a real stylesheet file and rewrite the cascade in a mobile-first style.

Why both moves in one change:
- Extracting alone removes the worst symptom (no triple-quoted 700-line blob inside Python) but leaves the existing desktop-first ordering, which is what caused the bug.
- Converting to mobile-first inside the index_string is possible but means churning the string and re-shipping the same fragile arrangement.
- Doing both at once is cheaper than doing them sequentially and removes the conditions that created the bug.

The cascade after the change:

```
/* Base — mobile-first */
.tasting-card {
    padding: 1.25rem 1.25rem 1.5rem 1.25rem;
    border-bottom: 1px solid var(--hairline);
    /* no position: sticky here */
}

/* Desktop enhancements */
@media (min-width: 1100px) {
    .tasting-card {
        padding: 1.6rem 1.75rem 2rem 3rem;
        border-right: 1px solid var(--hairline);
        border-bottom: 0;
        background: linear-gradient(to right, transparent calc(100% - 1px), var(--paper-deep) calc(100% - 1px));
        position: sticky;
        top: 0;
        align-self: start;
        max-height: 100vh;
        overflow-y: auto;
    }
}
```

The sticky behaviour now lives where it is wanted (desktop, two-column spread) and is invisible at every smaller width by construction. There is no override to lose to source order because there is nothing to override.

The same mobile-first inversion is applied across the file:
- `.spread` — base is `grid-template-columns: 1fr` (single column); `@media (min-width: 1100px)` switches to `23rem 1fr`.
- `.charts-row` — base is single column; `@media (min-width: 1100px)` switches to `1fr 1fr`.
- `.feature` / `.masthead` / `.colophon` — base uses tight phone padding; `@media (min-width: 1100px)` applies desktop padding.
- Sliders, buttons, radar chart heights, the ledger card-view-vs-table-view split — all base values are the phone-friendly ones, with desktop overrides.
- Decoration rules (`body::before`, `body::after`, animations) are size-agnostic and keep their current form.

The `@media (max-width: 767px)` block is removed; its rules become the base.
The `@media (max-width: 1099px)` block is removed; the single-column collapse becomes the base, `@media (min-width: 1100px)` undoes it for desktop.

Visual outcome: at desktop, identical to today. At tablet/phone, sticky behaviour is gone, the column collapses, and the user scrolls through cleanly.

### 2. The regression test — `tests/test_dashboard_css.py`

A small unit test that imports `dashboard.app`, reads the rendered CSS (now in `dashboard/assets/style.css`, but readable from disk), and asserts structural invariants. No browser, no Dash server, no Plotly rendering. Targets ~10ms total.

Three layers of check:

**(a) Source-order invariant — the bug we just fixed**

Parse the stylesheet. For each class with rules in *both* the base scope and inside a media query, assert that any rule changing `position`, `overflow`, `overflow-y`, `max-height`, `display`, or `grid-template-columns` in the **non-matching scope** for that breakpoint cannot be silently overridden. The simplest expression: for mobile-first stylesheets, any time a `position: sticky` / `overflow: auto` / `max-height: 100vh` is declared inside `@media (min-width: …)`, it must not also be declared in the base scope. If the file ever reverts to a desktop-first arrangement, this test fires.

**(b) Specific tasting-card invariant — the symptom**

Assert directly:
- The base `.tasting-card` rule does not contain `position: sticky`, `max-height: 100vh`, or `overflow-y: auto`.
- A `@media (min-width: 1100px) { .tasting-card { ... } }` exists with `position: sticky` and `overflow-y: auto`.

If someone later types `position: sticky` into the base block by mistake, this test fires with a clear message naming the property.

**(c) Required-rules invariant — light schema**

Assert the stylesheet contains the rules the app depends on existing (e.g., `.ledger-card-view`, `.ledger-table-view`, `.sidebar-toggle` exist; `.ink-btn:hover` is wrapped by a `@media (hover: none)` block or equivalent). These are claims the Python code already makes by emitting class names; the test makes the contract explicit.

The CSS is parsed with a small home-grown function (~30 lines) using `re` from the stdlib — the stylesheet is small, structured, and we control both ends. No `tinycss2` dependency. If we later want a real parser, swapping it in changes one helper and leaves the assertions intact.

### 3. Best-practice improvements bundled with the fix

These are not free-floating refactors; they exist because they directly reduce the chance of this bug class returning. None of them require a behaviour change for the user.

1. **CSS in its own file (`dashboard/assets/style.css`).** Already covered above. Side benefit: future contributors get editor syntax highlighting and proper diffs.
2. **`:root` custom properties for the two breakpoint values** — `--bp-desktop: 1100px` and `--bp-phone: 768px` are *not* something CSS natively supports inside `@media` queries (`@media (min-width: var(--bp-desktop))` does not work). Instead we document the two breakpoints in a single CSS comment at the top of the file and assert their values from the test. This is the lightweight equivalent.
3. **A top-of-file CSS comment block** that describes the breakpoint contract:
   ```
   /* Breakpoints:
    *   base       0 - 1099px    — phone & tablet (mobile-first)
    *   desktop    >= 1100px     — two-column spread
    * Any rule using @media (max-width: …) is a smell — see test_dashboard_css.
    */
   ```
4. **Pytest assertion** that no `@media (max-width: …)` query exists in the stylesheet. Hover/pointer feature queries like `@media (hover: none)` are unrelated and remain allowed; the assertion targets the `max-width:` substring specifically. With mobile-first this should always be true; the test fires if anyone reintroduces desktop-first thinking.

Explicitly *not* in this change but worth the user's awareness:

- Splitting `dashboard/app.py` (1346 lines) into `layout.py`, `callbacks.py`, `figures.py` would help maintainability but does not relate to this bug. Recommend doing it separately, after this change is in.
- Playwright/headless-browser end-to-end tests give higher confidence than the structural CSS test, but at a cost of >1s per test and a Chromium dependency. Recommend deferring until at least one bug slips past the structural test.
- Stylelint would be the proper way to enforce CSS conventions long-term. Deferred — we have ~1 stylesheet right now.

## Implementation scope

Files changed:

- **New file:** `dashboard/assets/style.css` — content moved out of `app.index_string`, rewritten mobile-first.
- **Modified:** `dashboard/app.py` — `app.index_string` shrinks to just the document scaffold and the Google Fonts `<link>`; the `<style>` block is removed. Python layout/callbacks unchanged.
- **New file:** `tests/test_dashboard_css.py` — three test functions covering the three assertion layers above. Pure stdlib (`re`, `pathlib`); no Dash import needed.

Files not changed: `src/`, `data/`, `scripts/`, `notebooks/`, `pyproject.toml`.

## Verification

Automated:
- `uv run pytest tests/` passes, including the new `test_dashboard_css.py`.

Manual:
- Restart `uv run python dashboard/app.py`.
- Open at 1280px desktop — visually identical to today (same fonts, same paper grain, same sticky sidebar, same charts).
- Resize to 1024px — single column, no sticky, scroll cleanly past the sidebar to reach the graphs.
- Resize to 414px — same, plus phone-specific overrides (card-view ledger, larger slider handles, collapse toggle visible).
- Real iPhone via local IP — scroll down: filter card scrolls away with the page, graphs come into view in the normal flow.

## Risks

- **Asset loading order vs Google Fonts `<link>`.** The font links live in `index_string` and load before any stylesheet referencing them; that order is preserved. `dashboard/assets/style.css` is auto-included by Dash *after* `external_stylesheets` (Bootstrap), which matches the current arrangement.
- **Removing `<style>` from `index_string`** invalidates any selector that depended on being loaded *before* Bootstrap. None do — the existing rules all use `!important` where they fight Bootstrap; behaviour is unchanged.
- **The regression test depends on the stylesheet's textual form.** If a future contributor changes the stylesheet's formatting (e.g., runs Prettier with different settings), the regex parser may break. Mitigation: the parser tolerates whitespace and is forgiving about whether rules are on one line or many.
- **Mobile-first conversion is a textual rewrite of ~700 lines of CSS.** Risk of typos. Mitigation: the new structural test acts as a smoke test; the manual verification covers the rest.
