# Sticky-Sidebar Fix & CSS Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the bug where the tasting card (filters + sliders) remains fixed on screen at mobile/tablet widths, causing the radar graphs to scroll behind it; add regression tests; extract CSS to a standalone file with a mobile-first cascade.

**Architecture:** Move the ~700-line CSS block from `dashboard/app.py`'s `app.index_string` into a dedicated `dashboard/assets/style.css` file (Dash auto-loads anything under `/assets`). Convert the cascade from desktop-first (`@media (max-width: …)`) to mobile-first (`@media (min-width: 1100px)`). Drop `position: sticky` from the base `.tasting-card` rule and re-introduce it only inside the desktop media query. Add `tests/test_dashboard_css.py` that parses the new stylesheet and asserts structural invariants. No changes to Python layout, callbacks, or the recommender.

**Tech Stack:** Dash 2.x, dash-bootstrap-components, Plotly. Python tests use stdlib `re` + `pathlib` only — no new dependencies. Manual verification uses Chrome/Firefox DevTools device emulation.

**Spec:** `docs/superpowers/specs/2026-05-21-sticky-sidebar-fix-and-css-hardening-design.md`

**Verification convention:** Each task ends with a check. The dev server runs at `http://127.0.0.1:8050` via `uv run python dashboard/app.py`. Toggle DevTools device emulation (Ctrl+Shift+M) and test at 375px (iPhone), 768px (iPad portrait), 1024px (iPad landscape), 1280px (desktop). Restart the server after any change to `app.index_string` or after creating `dashboard/assets/style.css`; Dash watches assets in debug mode but the server here runs with `debug=False`.

**Project note:** This repo is not currently a git repo (`git status` exits 128). The plan does **not** include `git add` / `git commit` steps. If the user wants version control, run `git init` once before starting. The tasks are self-contained so individual rollback is possible by re-running the dev server and noting which task introduced an issue.

## File Structure

| File | Responsibility | Status |
|---|---|---|
| `dashboard/assets/style.css` | All page styling. Mobile-first cascade. Single source of truth for visual rules. | New — created in Task 1, rewritten mobile-first in Task 3. |
| `dashboard/app.py` | Dash layout, callbacks, figure construction. The `<style>` block inside `app.index_string` is deleted; the rest of the file is unchanged. | Modified in Task 1 only. |
| `tests/test_dashboard_css.py` | Three structural invariants: (a) no `@media (max-width:)` queries; (b) base `.tasting-card` doesn't contain sticky/overflow/max-height; (c) a `@media (min-width: 1100px) .tasting-card` block exists with `position: sticky`. | New — created in Task 2. |

`src/`, `data/`, `scripts/`, `notebooks/`, `pyproject.toml` are untouched.

---

### Task 1: Extract CSS to `dashboard/assets/style.css` verbatim

**Goal of this task:** Move the existing CSS out of the Python string into a real file with **zero behaviour change**. We do not fix the bug yet; we only relocate the styles. This sets up the next task (writing the regression test) to read from a real file, and makes the Task 3 refactor a CSS-only diff.

**Files:**
- Create: `dashboard/assets/style.css`
- Modify: `dashboard/app.py:76-789` (the `app.index_string` value; specifically the `<style>` block that runs from `<style>` to `</style>`)

- [ ] **Step 1: Create the assets directory**

```bash
mkdir -p dashboard/assets
```

Confirm with:

```bash
ls dashboard/
```

Expected output includes `app.py` and `assets`.

- [ ] **Step 2: Create `dashboard/assets/style.css` with the current CSS verbatim**

Open `dashboard/app.py`. Find the line `app.index_string = """<!DOCTYPE html>` (around line 76) and find the closing `</style>` tag (around line 779). Copy everything **between** `<style>` and `</style>` — but not the `<style>` / `</style>` tags themselves — into a new file `dashboard/assets/style.css`.

That copy starts with `:root {` and ends with the closing `}` of the `.colophon { … }` rule. Preserve all whitespace, comments, and selector formatting exactly. The file will be ~692 lines.

The very first lines of the new file should be:

```css
:root {
    --paper:        #F1E8D3;
    --paper-deep:   #E6DABB;
    --paper-edge:   #DBCDA6;
```

The very last lines should be (the existing closing of `.colophon`):

```css
    .colophon {
        margin: 3rem 3rem 2rem 3rem;
        padding-top: 1rem;
        border-top: 1px solid var(--hairline);
        font-family: var(--mono);
        font-size: 0.65rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: var(--ink-faint);
        display: flex;
        justify-content: space-between;
        position: relative;
        z-index: 2;
    }
```

(Note: keep the existing 4-space indentation from inside the `<style>` block. Dash does not care about indentation; preserving it makes the next-task diff smaller.)

- [ ] **Step 3: Delete the inline `<style>` block from `app.index_string`**

In `dashboard/app.py`, edit `app.index_string` so that the `<style>...</style>` block is removed entirely. The `<head>` section should now look like this (note the four Dash template tokens stay in place):

```python
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
```

`{%css%}` is the Dash placeholder that gets replaced by `external_stylesheets` (Bootstrap) plus any `assets/*.css` files (our new `style.css`). Dash auto-discovers `assets/style.css` because the file lives in the conventional `/assets` folder alongside `app.py`.

- [ ] **Step 4: Run the dashboard and confirm visual parity at desktop width**

```bash
uv run python dashboard/app.py
```

Open `http://127.0.0.1:8050` at desktop width (>1100px). Expected: the page renders **identically to before** — same fonts, same paper grain, same copper accents, same two-column spread, same sticky sidebar (the bug still exists; we have not fixed it yet).

If the page looks bare (no styling), Dash didn't load `assets/style.css`. Common causes:
1. File is in `dashboard/style.css` (wrong) instead of `dashboard/assets/style.css` (right).
2. The dashboard was started from a different working directory. Dash resolves `assets/` relative to the directory of `app.py`. Run from the repo root: `uv run python dashboard/app.py`.

Stop the server with Ctrl+C when verified.

- [ ] **Step 5: Run the existing pytest suite to confirm no regression**

```bash
uv run pytest tests/ -v
```

Expected: all existing tests pass. We changed only `app.index_string` and added a new CSS file; nothing in `src/` was touched.

---

### Task 2: Add the regression test — `tests/test_dashboard_css.py`

**Goal of this task:** Write the regression tests **before** fixing the bug. The tests will fail against the verbatim CSS we just extracted because that CSS is still desktop-first. Task 3 makes them pass.

**Files:**
- Create: `tests/test_dashboard_css.py`

- [ ] **Step 1: Write the test file**

Create `tests/test_dashboard_css.py` with the following content:

```python
"""Structural tests for dashboard/assets/style.css.

These tests pin two invariants that, together, prevent the class of bug
where a base rule for .tasting-card silently overrides a mobile media
query — which was the regression that motivated this test file.

The stylesheet should be mobile-first:
- Base rules are for phone/tablet (< 1100px).
- @media (min-width: 1100px) blocks enhance the experience for desktop.
- No @media (max-width: …) queries (with a narrow exception for hover/pointer
  feature queries, which are unrelated).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CSS_PATH = ROOT / "dashboard" / "assets" / "style.css"


@pytest.fixture(scope="module")
def css_text() -> str:
    assert CSS_PATH.exists(), (
        f"Expected stylesheet at {CSS_PATH}. "
        "Did you delete or move dashboard/assets/style.css?"
    )
    return CSS_PATH.read_text(encoding="utf-8")


def _strip_block_comments(text: str) -> str:
    """Remove /* ... */ comments (possibly multi-line) from CSS."""
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _find_rule_body(css: str, selector_pattern: str) -> str | None:
    """Return the body (between { and matching }) of the *first* base-scope
    rule whose selector matches selector_pattern, or None.

    Only the top level is searched — rules inside @media blocks are skipped.
    """
    stripped = _strip_block_comments(css)
    i = 0
    while i < len(stripped):
        # Skip @media (and any other @-rule) at the top level by jumping
        # over the entire balanced block that follows.
        if stripped[i] == "@":
            # find the opening brace of the @-rule's block
            brace = stripped.find("{", i)
            if brace == -1:
                break
            depth = 1
            j = brace + 1
            while j < len(stripped) and depth > 0:
                if stripped[j] == "{":
                    depth += 1
                elif stripped[j] == "}":
                    depth -= 1
                j += 1
            i = j
            continue

        # Find the next selector ending at "{"
        brace = stripped.find("{", i)
        if brace == -1:
            break
        selector = stripped[i:brace].strip()
        if re.search(selector_pattern, selector):
            # Walk to the matching close brace
            depth = 1
            j = brace + 1
            while j < len(stripped) and depth > 0:
                if stripped[j] == "{":
                    depth += 1
                elif stripped[j] == "}":
                    depth -= 1
                j += 1
            return stripped[brace + 1: j - 1]
        # Skip past this rule's body
        depth = 1
        j = brace + 1
        while j < len(stripped) and depth > 0:
            if stripped[j] == "{":
                depth += 1
            elif stripped[j] == "}":
                depth -= 1
            j += 1
        i = j
    return None


def _find_media_block(css: str, condition_substring: str) -> str | None:
    """Return the body of the first @media query whose condition contains
    the substring (e.g. 'min-width: 1100px'), or None.
    """
    stripped = _strip_block_comments(css)
    pattern = re.compile(r"@media\s*\(([^)]*)\)\s*\{", re.IGNORECASE)
    for match in pattern.finditer(stripped):
        condition = match.group(1)
        if condition_substring.lower() not in condition.lower():
            continue
        brace = match.end() - 1
        depth = 1
        j = brace + 1
        while j < len(stripped) and depth > 0:
            if stripped[j] == "{":
                depth += 1
            elif stripped[j] == "}":
                depth -= 1
            j += 1
        return stripped[brace + 1: j - 1]
    return None


# ───────────────────────── Invariant (a) ─────────────────────────
# No max-width media queries. The cascade is mobile-first.

def test_no_max_width_media_queries(css_text: str) -> None:
    """Mobile-first stylesheet: there should be no @media (max-width: …).

    Hover/pointer/feature queries like @media (hover: none) are fine —
    they target the substring 'max-width' only.
    """
    stripped = _strip_block_comments(css_text)
    offenders = re.findall(r"@media\s*\([^)]*max-width[^)]*\)", stripped,
                           flags=re.IGNORECASE)
    assert not offenders, (
        "Found @media (max-width: …) queries — the stylesheet should be "
        f"mobile-first. Offenders: {offenders}"
    )


# ───────────────────────── Invariant (b) ─────────────────────────
# The base .tasting-card rule must not declare sticky behavior.

def test_tasting_card_base_is_not_sticky(css_text: str) -> None:
    """The base (non-media-query) .tasting-card rule must not contain
    position: sticky, max-height: 100vh, or overflow-y: auto. These
    belong only inside the desktop @media (min-width: 1100px) block.

    This is the exact regression that motivated the test: previously
    the base rule had position: sticky and a @media (max-width: 1099px)
    override tried to set position: static — but lost due to source
    order. With mobile-first, the base never claims sticky.
    """
    body = _find_rule_body(css_text, r"^\.tasting-card$")
    assert body is not None, (
        "Could not locate a base-scope `.tasting-card { ... }` rule "
        "in the stylesheet. Did the selector get renamed?"
    )
    forbidden = {
        "position": "sticky",
        "max-height": "100vh",
        "overflow-y": "auto",
    }
    for prop, value in forbidden.items():
        pattern = re.compile(rf"\b{re.escape(prop)}\s*:\s*{re.escape(value)}\b")
        assert not pattern.search(body), (
            f"Base .tasting-card rule contains `{prop}: {value}` — this "
            "belongs only inside @media (min-width: 1100px). On phones/"
            "tablets it makes the sidebar stick to the viewport and the "
            "graphs scroll behind it."
        )


# ───────────────────────── Invariant (c) ─────────────────────────
# Desktop media query must re-introduce sticky behavior.

def test_desktop_media_query_makes_tasting_card_sticky(css_text: str) -> None:
    """A @media (min-width: 1100px) block must exist and must declare
    .tasting-card with position: sticky and overflow-y: auto. This is
    where the desktop sticky behaviour now lives.
    """
    block = _find_media_block(css_text, "min-width: 1100px")
    assert block is not None, (
        "No @media (min-width: 1100px) block found. The mobile-first "
        "cascade needs this block to enhance the desktop experience."
    )
    # Locate the .tasting-card declaration inside the media block.
    # We don't need a full parser here — substring is enough because the
    # selector is unique.
    inner = re.search(
        r"\.tasting-card\s*\{([^}]*)\}", block, flags=re.DOTALL
    )
    assert inner is not None, (
        "@media (min-width: 1100px) exists but contains no .tasting-card "
        "rule. The desktop sticky sidebar lives there now."
    )
    inner_body = inner.group(1)
    assert re.search(r"\bposition\s*:\s*sticky\b", inner_body), (
        "Desktop .tasting-card must set position: sticky."
    )
    assert re.search(r"\boverflow-y\s*:\s*auto\b", inner_body), (
        "Desktop .tasting-card must set overflow-y: auto."
    )


# ───────────────────────── Sanity: required selectors ─────────────────────────

@pytest.mark.parametrize("selector", [
    ".tasting-card",
    ".feature",
    ".spread",
    ".charts-row",
    ".ledger-table-view",
    ".ledger-card-view",
    ".sidebar-toggle",
    ".ink-btn",
    ".masthead",
    ".colophon",
])
def test_required_selectors_present(css_text: str, selector: str) -> None:
    """Selectors emitted by the Python layout must exist somewhere in
    the stylesheet (base or media block — we don't care which).
    """
    stripped = _strip_block_comments(css_text)
    # Match the selector as a whole word (preceded by start/whitespace/comma
    # and followed by whitespace, comma, {, ., :, etc.).
    pattern = re.compile(
        rf"(^|[\s,]){re.escape(selector)}(?=[\s,{{.:])",
        flags=re.MULTILINE,
    )
    assert pattern.search(stripped), (
        f"Selector {selector!r} is referenced by the Python layout but "
        "is not defined in dashboard/assets/style.css."
    )
```

- [ ] **Step 2: Run the new test file — confirm tests FAIL**

```bash
uv run pytest tests/test_dashboard_css.py -v
```

Expected: **three of the four tests fail** (we are still at the verbatim desktop-first CSS):

- `test_no_max_width_media_queries` — FAILS (current file contains `@media (max-width: 1099px)` and `@media (max-width: 767px)`).
- `test_tasting_card_base_is_not_sticky` — FAILS (base `.tasting-card` still has `position: sticky` and friends).
- `test_desktop_media_query_makes_tasting_card_sticky` — FAILS (no `@media (min-width: 1100px)` exists yet).
- `test_required_selectors_present` — PASSES (all selectors already exist somewhere).

If a different set of tests fails, stop and investigate. The four tests are a baseline contract for the next task.

- [ ] **Step 3: Run the full test suite — confirm only the new tests fail**

```bash
uv run pytest tests/ -v
```

Expected: the recommender and data-prep tests still pass; only the three new structural tests fail. If anything else fails, that's an unrelated regression — investigate before continuing.

---

### Task 3: Convert the CSS to mobile-first and fix the bug

**Goal of this task:** Rewrite `dashboard/assets/style.css` so that the cascade is mobile-first. The base rules are for phone/tablet widths; `@media (min-width: 1100px)` enhances for desktop. After this task, all four tests in `test_dashboard_css.py` pass, and a real browser at 375px no longer sticks the sidebar.

**Files:**
- Modify: `dashboard/assets/style.css` (full rewrite of the responsive blocks; static decoration/typography rules stay as-is)

- [ ] **Step 1: Add a breakpoint contract comment at the very top of the file**

Open `dashboard/assets/style.css`. Above the existing `:root { … }` block, insert:

```css
/*
 * Beer Predictor — stylesheet
 *
 * Breakpoints (mobile-first):
 *   base               0 -  1099px   — phone & tablet
 *   desktop      >=    1100px        — two-column spread, sticky sidebar
 *
 * Any @media (max-width: ...) query is a smell. The structural tests in
 * tests/test_dashboard_css.py enforce this. If you find yourself needing
 * one, you probably want to invert the rule and put it in the base.
 *
 * Hover/pointer feature queries (e.g. @media (hover: none)) are unrelated
 * to width breakpoints and remain allowed.
 */
```

- [ ] **Step 2: Delete the two desktop-first media queries**

Find these two blocks in `dashboard/assets/style.css` and **delete** them entirely:

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

    /* Charts — shorter on phones */
    .radar-graph { height: 300px !important; }

    /* Sidebar collapse toggle visible only on phones */
    .sidebar-toggle { display: flex !important; }

    /* Ledger: cards instead of table */
    .ledger-table-view { display: none; }
    .ledger-card-view { display: block; }
}
```

Also delete the smaller desktop-first media query that lives inside the charts-row group (search for it; it's `@media (max-width: 1100px)` and contains `.charts-row { grid-template-columns: 1fr; }`):

```css
@media (max-width: 1100px) {
    .charts-row { grid-template-columns: 1fr; }
}
```

- [ ] **Step 3: Move mobile values into the base rules**

Replace the following base rules in `dashboard/assets/style.css` with their mobile-first equivalents. Each rule below shows the **complete replacement** body, not a diff.

Find and replace `.masthead { … }` (the block that starts `.masthead { padding: 3.5rem 3rem 1.25rem 3rem; ... }`):

```css
.masthead {
    padding: 1.5rem 1.25rem 0.75rem 1.25rem;
    position: relative;
    animation: inkBleed 1.2s ease-out both;
}
```

Find and replace `.masthead .vol`:

```css
.masthead .vol {
    font-family: var(--mono);
    font-size: 0.72rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-soft);
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    align-items: flex-start;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--hairline);
}
```

Find and replace `.masthead .kicker`:

```css
.masthead .kicker {
    font-family: var(--serif);
    font-style: italic;
    font-size: 1.0rem;
    color: var(--ink-soft);
    max-width: 56ch;
    margin: 0.25rem 0 1.2rem 0;
}
```

Find and replace `.spread`:

```css
.spread {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0;
    position: relative;
    z-index: 2;
}
```

Find and replace `.tasting-card` (this is the critical fix — note that `position: sticky`, `top`, `align-self`, `max-height`, and `overflow-y` are **gone** from the base):

```css
.tasting-card {
    padding: 1.25rem 1.25rem 1.5rem 1.25rem;
    border-bottom: 1px solid var(--hairline);
    background:
        linear-gradient(to right, transparent calc(100% - 1px), var(--paper-deep) calc(100% - 1px));
}
```

Find and replace `.rc-slider`:

```css
.rc-slider {
    height: 28px;
    padding: 16px 0;
}
```

Find and replace `.rc-slider-rail`:

```css
.rc-slider-rail {
    background: var(--ink) !important;
    height: 2px !important;
    border-radius: 0 !important;
    opacity: 0.35;
}
```

Find and replace `.rc-slider-track`:

```css
.rc-slider-track {
    background: var(--copper) !important;
    height: 3px !important;
    border-radius: 0 !important;
    margin-top: -1px;
}
```

Find and replace `.rc-slider-handle`:

```css
.rc-slider-handle {
    background: var(--copper) !important;
    border: 2px solid var(--ink) !important;
    width: 24px !important;
    height: 24px !important;
    margin-top: -11px !important;
    box-shadow:
        inset 0 1px 0 rgba(255,220,170,0.6),
        0 1px 2px rgba(0,0,0,0.25) !important;
    opacity: 1 !important;
}
```

Find and replace `.ink-btn`:

```css
.ink-btn {
    display: inline-block;
    font-family: var(--mono);
    font-size: 0.78rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink);
    background: transparent;
    border: 1px solid var(--ink);
    padding: 0.55rem 1rem;
    cursor: pointer;
    position: relative;
    transition: all 0.15s ease;
    border-radius: 0;
    width: 100%;
    min-height: 48px;
}
```

Find and replace `.feature`:

```css
.feature {
    padding: 1.25rem 1.25rem 2rem 1.25rem;
    min-width: 0;
}
```

Find and replace `.feature-header h2`:

```css
.feature-header h2 {
    font-family: var(--display);
    font-weight: 800;
    font-size: clamp(1.7rem, 6vw, 2.8rem);
    line-height: 1.0;
    letter-spacing: -0.02em;
    margin: 0.3rem 0 0.6rem 0;
    font-variation-settings: "opsz" 72;
}
```

Find and replace `.charts-row`:

```css
.charts-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.5rem;
    margin-top: 1.4rem;
    padding-top: 1.4rem;
    border-top: 1px solid var(--hairline);
}
```

Find and replace `.ledger-head h3`:

```css
.ledger-head h3 {
    font-family: var(--display);
    font-weight: 800;
    font-size: clamp(1.4rem, 5vw, 1.65rem);
    margin: 0;
    letter-spacing: -0.01em;
}
```

Find and replace `.ledger-card-view` (currently `display: none`) and `.ledger-table-view` (which doesn't exist as a standalone base rule but is hidden inside the deleted phone media query):

```css
.ledger-card-view { display: block; }
.ledger-table-view { display: none; }
```

(Below the existing block of `.ledger-card-view` styles, change the very first rule from `display: none` to `display: block`, and add a new `.ledger-table-view { display: none; }` rule beside it. These two rules together flip the ledger to phone-first.)

Find and replace `.colophon`:

```css
.colophon {
    margin: 2rem 1.25rem 1.5rem 1.25rem;
    padding-top: 1rem;
    border-top: 1px solid var(--hairline);
    font-family: var(--mono);
    font-size: 0.65rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-faint);
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    justify-content: space-between;
    position: relative;
    z-index: 2;
}
```

Find and replace `.sidebar-toggle`:

```css
.sidebar-toggle {
    display: flex; /* visible by default (phone-first); desktop hides it */
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
```

Find and replace `.radar-graph` (this rule currently exists only inside `@media (max-width: 767px)`; add it at top level near the chart styles):

```css
.radar-graph { height: 300px; }
```

- [ ] **Step 4: Add a single `@media (min-width: 1100px)` block at the end of the stylesheet**

Append this block at the very end of `dashboard/assets/style.css` (before the file ends — there should be no further rules after it):

```css
/* ───── Desktop (≥ 1100px) — two-column spread, sticky sidebar ─────── */
@media (min-width: 1100px) {
    .masthead {
        padding: 3.5rem 3rem 1.25rem 3rem;
    }

    .masthead .vol {
        flex-direction: row;
        gap: 0;
        align-items: stretch;
        justify-content: space-between;
    }

    .masthead .kicker {
        font-size: 1.15rem;
    }

    .spread {
        grid-template-columns: 23rem 1fr;
    }

    .tasting-card {
        padding: 1.6rem 1.75rem 2rem 3rem;
        border-bottom: 0;
        border-right: 1px solid var(--hairline);
        position: sticky;
        top: 0;
        align-self: start;
        max-height: 100vh;
        overflow-y: auto;
    }

    .rc-slider { padding: 12px 0; }
    .rc-slider-rail { height: 1px !important; }
    .rc-slider-track { height: 2px !important; margin-top: -0.5px; }
    .rc-slider-handle {
        width: 16px !important;
        height: 16px !important;
        margin-top: -7px !important;
    }

    .ink-btn {
        font-size: 0.72rem;
        min-height: auto;
    }

    .feature {
        padding: 1.6rem 3rem 3rem 3rem;
    }

    .charts-row {
        grid-template-columns: 1fr 1fr;
    }

    .radar-graph { height: 360px; }

    .ledger-table-view { display: block; }
    .ledger-card-view { display: none; }

    .sidebar-toggle { display: none; }

    .colophon {
        margin: 3rem 3rem 2rem 3rem;
        flex-direction: row;
        gap: 0;
    }
}
```

- [ ] **Step 5: Run the structural tests — they should now all pass**

```bash
uv run pytest tests/test_dashboard_css.py -v
```

Expected: **all four tests (parametrized count: 4 + 10 sanity = 14) pass**. If any of the three core tests still fails, the failure message will name the property that's wrong; fix and rerun.

- [ ] **Step 6: Run the full suite to confirm no regressions**

```bash
uv run pytest tests/ -v
```

Expected: every test passes (recommender, data prep, and the new structural tests).

- [ ] **Step 7: Visual verification at every breakpoint**

```bash
uv run python dashboard/app.py
```

Open the dashboard in Chrome with DevTools (Ctrl+Shift+I), enable device-toolbar mode (Ctrl+Shift+M), and check each width:

| Width | Expected |
|---|---|
| 1280px | Two-column spread, sticky sidebar (scroll past the page, sidebar stays in viewport). Identical to before the bug. |
| 1100px | Two-column spread still. Sticky still works. |
| 1099px | One-column. Sidebar scrolls **with the page**, not stuck. Graphs appear in the normal flow as you scroll. |
| 1024px | Same as 1099px. |
| 768px | Same — one column, no sticky. Card-view ledger may still be hidden depending on the breakpoint; verify table is visible at this width (≥ 768px is "tablet" — table view). |
| 414px / 375px | One column. Ledger renders as cards. Sidebar collapse toggle is visible. Slider handles are 24px. Scrolling past the sidebar reveals the graphs — **not behind** the sidebar. |

If at 1099px the sidebar is still sticky, the `@media (min-width: 1100px) { .tasting-card { position: sticky } }` block is being applied at 1099px — check that the breakpoint is `1100px` not `1099px` in the media query.

If at 1280px the layout has collapsed to one column, the `@media (min-width: 1100px)` block did not match — check the file path (`dashboard/assets/style.css`) and confirm `{%css%}` is still in `app.index_string`.

Stop the server with Ctrl+C when verification is complete.

---

### Task 4: End-to-end verification

**Goal of this task:** No code changes — final sanity pass before declaring the work done.

- [ ] **Step 1: Run the entire test suite**

```bash
uv run pytest tests/ -v
```

Expected: every test passes.

- [ ] **Step 2: Verify the dashboard at desktop and phone widths in two browsers**

Start the server:

```bash
uv run python dashboard/app.py
```

In Chrome and Firefox, at 1280px and 375px, confirm:

1. The page renders with the broadsheet styling (fonts loaded, paper grain visible, copper accents on sliders/buttons).
2. Moving sliders updates both radar charts and the ledger.
3. The "Reset profile" button works.
4. On phone widths, the sidebar collapse toggle expands and collapses the controls.
5. On phone widths, scrolling down past the sidebar reveals the radar graphs in the normal flow — they are **not** behind a sticky sidebar.

- [ ] **Step 3: Real device test (optional, if available)**

If a phone is available, navigate to `http://<laptop-IP>:8050` and confirm the same scroll behaviour. Skip if not available — DevTools device emulation is sufficient signal.

- [ ] **Step 4: Final cleanup**

Stop the dev server. The work is complete.

---

## Self-Review

**Spec coverage:**
- §1 The fix (mobile-first, extract to assets/style.css) → Task 1 + Task 3 ✓
- §2 Regression test (three layers a/b/c) → Task 2 ✓
- §3 Best-practice improvements (CSS in own file, breakpoint comment, no max-width assertion) → Task 1 + Task 3 ✓

**Placeholder scan:** No "TBD", "implement later", or vague steps. Every code-changing step contains the literal code or selector to write.

**Type consistency:** Selectors and CSS property names are spelled identically across all tasks. `.tasting-card`, `.sidebar-toggle`, `.ledger-card-view`, `.ledger-table-view`, `.radar-graph`, `.charts-row` — all match the Python `className` strings in `dashboard/app.py`.

**Risk acknowledged but not blocking:**
- The CSS extraction is a verbatim copy (Task 1) before any refactor (Task 3). If something visually breaks between Task 1 and Task 3, it's a refactor-time bug isolated to one task — easy to bisect.
- The regression tests fail intentionally between Task 2 and Task 3 — this is the TDD red→green cycle, not a bug.
- The plan assumes `dashboard/assets/style.css` is the only stylesheet Dash auto-discovers. If the project later adds `dashboard/assets/extra.css`, the structural tests will still apply only to `style.css`. Acceptable.
