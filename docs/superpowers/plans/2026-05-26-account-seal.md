# Account Seal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain dot-separated link strip in the top-right of the masthead with a framed "account seal" (eyebrow / name / hairline rule / actions) that fits the broadsheet aesthetic.

**Architecture:** Two surfaces change: (1) `dashboard/components/masthead.py` swaps the inline `me-strip` for a four-element `.account-seal` block; (2) `dashboard/assets/style.css` gains a mobile-first `.account-seal` style block. Position is unchanged — the seal remains the third child of `.masthead .vol`, so the existing desktop flex rule (`@media (min-width: 1100px)`) lands it at the right edge automatically. A new pure-function unit test pins the rendered HTML structure; an existing parametrized CSS structural test grows by one entry to require the new selector.

**Tech Stack:** Python 3 · Dash (`dash.html`) · `pytest` · CSS3 (mobile-first; no `max-width` media queries — enforced by `tests/test_dashboard_css.py`).

**Project state:** This project is NOT a git repository (verified with `test -d .git`). Skip all `git add` / `git commit` steps. Engineer should verify by running `test -d .git` themselves; if git was added later, use commit messages exactly as written below.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `dashboard/components/masthead.py` | Modify | Replace `_signed_in_links` / `_anon_links` with builders that emit the four-element `.account-seal` structure. `masthead()` itself does not change. |
| `dashboard/assets/style.css` | Modify | Add a new mobile-first `.account-seal { ... }` block (plus child-element rules) in the base section, placed near the existing `.masthead` rules. No desktop override required — the existing `.vol { flex-direction: row; justify-content: space-between }` rule inside `@media (min-width: 1100px)` already handles right-alignment. |
| `tests/test_dashboard_css.py` | Modify | Add `.account-seal` to the `test_required_selectors_present` parametrize list so the cascade test fails if the selector goes missing. |
| `tests/test_masthead.py` | Create | New unit-test file pinning the HTML structure of `_signed_in_links(name)` and `_anon_links()`. |

---

## Task 1: Pin the HTML structure of the signed-in seal (TDD red)

**Files:**
- Create: `tests/test_masthead.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_masthead.py` with the following content. The test imports the *private* helper directly because `masthead()` itself depends on Flask session and Supabase; the helpers are pure functions of their inputs.

```python
"""Structural tests for dashboard/components/masthead.py.

Pins the HTML structure of the account seal so future refactors of the
masthead can't silently drop the eyebrow, name, rule, or action row.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "dashboard")):
    if p not in sys.path:
        sys.path.insert(0, p)

from dashboard.components.masthead import _signed_in_links, _anon_links  # noqa: E402


def _walk_classes(component) -> set[str]:
    """Collect every className string anywhere in a Dash component tree."""
    found: set[str] = set()
    stack = [component]
    while stack:
        node = stack.pop()
        cls = getattr(node, "className", None)
        if isinstance(cls, str):
            found.update(cls.split())
        children = getattr(node, "children", None)
        if children is None:
            continue
        if isinstance(children, (list, tuple)):
            stack.extend(children)
        else:
            stack.append(children)
    return found


def _walk_text(component) -> str:
    """Concatenate every plain-string descendant in the component tree."""
    buf: list[str] = []
    stack = [component]
    while stack:
        node = stack.pop()
        if isinstance(node, str):
            buf.append(node)
            continue
        children = getattr(node, "children", None)
        if children is None:
            continue
        if isinstance(children, (list, tuple)):
            stack.extend(children)
        else:
            stack.append(children)
    return " ".join(buf)


def test_signed_in_seal_has_required_parts():
    seal = _signed_in_links("D. van Heerden")
    classes = _walk_classes(seal)

    # The four structural elements must all be present.
    assert "account-seal" in classes
    assert "account-seal__eyebrow" in classes
    assert "account-seal__name" in classes
    assert "account-seal__rule" in classes
    assert "account-seal__actions" in classes

    # The action elements share a class so the <a> and submit <button>
    # render identically.
    assert "account-seal__action" in classes


def test_signed_in_seal_renders_eyebrow_and_name():
    seal = _signed_in_links("D. van Heerden")
    text = _walk_text(seal)

    assert "ACCOUNT" in text
    assert "D. van Heerden" in text
    assert "Profile" in text
    assert "Sign out" in text


def test_anon_seal_has_required_parts():
    seal = _anon_links()
    classes = _walk_classes(seal)

    assert "account-seal" in classes
    assert "account-seal__eyebrow" in classes
    assert "account-seal__rule" in classes
    assert "account-seal__actions" in classes
    assert "account-seal__action" in classes


def test_anon_seal_renders_newsstand_copy():
    seal = _anon_links()
    text = _walk_text(seal)

    assert "NEWSSTAND" in text
    assert "Pick up a copy" in text
    assert "Sign in" in text
    assert "Sign up" in text
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_masthead.py -v`

Expected: All four tests FAIL with `AssertionError` because the current `_signed_in_links` / `_anon_links` produce a `<span class="me-strip">` with dot separators, not a `.account-seal` structure. The class assertions fail first.

- [ ] **Step 3: Commit (skip if not a git repo)**

```bash
git add tests/test_masthead.py
git commit -m "test: pin account seal HTML structure"
```

If `test -d .git` returns false, skip this step — the project is not yet under version control.

---

## Task 2: Implement the new HTML structure (TDD green)

**Files:**
- Modify: `dashboard/components/masthead.py:12-31`

- [ ] **Step 1: Replace `_signed_in_links` and `_anon_links`**

Open `dashboard/components/masthead.py`. Replace the existing `_signed_in_links` and `_anon_links` functions (currently spanning roughly lines 12-31) with the implementations below. Keep all other code — imports, `_fetch_display_name`, `masthead()` — exactly as it is.

```python
def _signed_in_links(display_name: str) -> html.Div:
    return html.Div(
        [
            html.Div("ACCOUNT", className="account-seal__eyebrow"),
            html.Div(display_name, className="account-seal__name"),
            html.Div(className="account-seal__rule"),
            html.Div(
                [
                    html.A("Profile", href="/profile",
                           className="account-seal__action"),
                    html.Span(" · ", className="account-seal__sep"),
                    html.Form(
                        html.Button(
                            "Sign out",
                            type="submit",
                            className="account-seal__action",
                        ),
                        action="/auth/logout",
                        method="post",
                        style={"display": "inline"},
                    ),
                ],
                className="account-seal__actions",
            ),
        ],
        className="account-seal",
    )


def _anon_links() -> html.Div:
    return html.Div(
        [
            html.Div("NEWSSTAND", className="account-seal__eyebrow"),
            html.Div("Pick up a copy", className="account-seal__name"),
            html.Div(className="account-seal__rule"),
            html.Div(
                [
                    html.A("Sign in", href="/auth/login",
                           className="account-seal__action"),
                    html.Span(" · ", className="account-seal__sep"),
                    html.A("Sign up", href="/auth/signup",
                           className="account-seal__action"),
                ],
                className="account-seal__actions",
            ),
        ],
        className="account-seal",
    )
```

Notes:
- The container is now an `html.Div` (not `html.Span`) so it can be a block-level frame with padding/border.
- The body of the anon variant reuses the `account-seal__name` class for the "Pick up a copy" line so its serif italic styling matches the display-name slot. Acceptable because that class is purely visual, not semantic.
- The `Form` wrapper around the sign-out `Button` is preserved so the existing POST logout flow continues to work.

- [ ] **Step 2: Run the masthead tests and verify they now pass**

Run: `python -m pytest tests/test_masthead.py -v`

Expected: All four tests PASS.

- [ ] **Step 3: Commit (skip if not a git repo)**

```bash
git add dashboard/components/masthead.py
git commit -m "feat(masthead): emit account seal structure"
```

---

## Task 3: Pin the new CSS selector (TDD red)

**Files:**
- Modify: `tests/test_dashboard_css.py:211-222`

- [ ] **Step 1: Add `.account-seal` to the required-selectors parametrize list**

Open `tests/test_dashboard_css.py`. Locate the `@pytest.mark.parametrize` decorator on `test_required_selectors_present` (around line 211). Add `".account-seal",` to the list, alongside the other masthead/layout selectors. The block should read:

```python
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
    ".account-seal",
])
def test_required_selectors_present(css_text: str, selector: str) -> None:
```

- [ ] **Step 2: Run the CSS structural test and verify the new case fails**

Run: `python -m pytest tests/test_dashboard_css.py -v -k "required_selectors"`

Expected: 10 tests PASS (the existing selectors), 1 test FAILS for `selector='.account-seal'` with a message like:

```
AssertionError: Selector '.account-seal' is referenced by the Python layout but is not defined in dashboard/assets/style.css.
```

- [ ] **Step 3: Commit (skip if not a git repo)**

```bash
git add tests/test_dashboard_css.py
git commit -m "test(css): require .account-seal selector"
```

---

## Task 4: Implement the seal styles (TDD green)

**Files:**
- Modify: `dashboard/assets/style.css` — add a new block in the base section, right after the existing `.masthead .doublerule { ... }` rule (around line 146).

- [ ] **Step 1: Insert the `.account-seal` block**

Open `dashboard/assets/style.css`. Find the `.masthead .doublerule` rule (around line 136-146) — it's the last `.masthead` descendant rule in the base section. Immediately after its closing `}`, before the `/* ───── Page grid ─────... */` comment that introduces `.spread`, insert the following block (keep the existing 4-space indent that the surrounding rules use):

```css
    /* ───── Account seal (top-right of masthead) ─────────────────── */
    .account-seal {
        display: inline-block;
        padding: 0.55rem 0.85rem 0.6rem 0.85rem;
        border: 1px solid var(--ink);
        background: transparent;
        box-shadow: 3px 3px 0 var(--copper-soft);
        margin-top: 0.4rem;
        align-self: flex-start;
        max-width: 18rem;
    }
    .account-seal__eyebrow {
        font-family: var(--mono);
        font-size: 0.6rem;
        letter-spacing: 0.28em;
        text-transform: uppercase;
        color: var(--copper-dim);
        line-height: 1;
        margin-bottom: 0.35rem;
    }
    .account-seal__name {
        font-family: var(--serif);
        font-style: italic;
        font-size: 0.98rem;
        color: var(--ink);
        line-height: 1.15;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .account-seal__rule {
        height: 1px;
        background: var(--hairline);
        margin: 0.5rem 0 0.45rem 0;
    }
    .account-seal__actions {
        font-family: var(--mono);
        font-size: 0.62rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: var(--ink-soft);
        line-height: 1;
        display: flex;
        align-items: center;
        gap: 0;
    }
    .account-seal__sep {
        margin: 0 0.4rem;
        color: var(--ink-faint);
    }
    .account-seal__action {
        font: inherit;
        letter-spacing: inherit;
        text-transform: inherit;
        color: var(--ink);
        background: transparent;
        border: 0;
        padding: 0;
        cursor: pointer;
        text-decoration: none;
        transition: color 0.15s ease;
    }
    .account-seal__action:hover,
    .account-seal__action:focus-visible {
        color: var(--copper);
        text-decoration: underline;
        text-underline-offset: 3px;
        outline: 0;
    }
```

Why these values:
- Border / shadow / paper background mirrors the `.ink-btn` "stamp" aesthetic already established for hover state — the seal looks like a permanently-stamped button.
- Eyebrow `--copper-dim` matches `.section-label` and `.feature-header .article-no`.
- `.account-seal__action` resets browser button defaults (`border`, `padding`, `background`, `font`) so the `Sign out` `<button>` is visually indistinguishable from the `Profile` `<a>`. The current implementation uses an undefined `linkish` class on the button, which is why it currently renders with browser-default chrome.
- `align-self: flex-start` keeps the seal hugging the top when `.vol` becomes a row on desktop.
- `max-width: 18rem` keeps the box from spanning a phone-width column when stacked on mobile.

- [ ] **Step 2: Run the CSS structural tests and verify all pass**

Run: `python -m pytest tests/test_dashboard_css.py -v`

Expected: All tests PASS — including the new `.account-seal` required-selectors case, and the `test_no_max_width_media_queries` invariant (because the new block uses no `max-width` queries).

- [ ] **Step 3: Run the full test suite as a regression check**

Run: `python -m pytest -q`

Expected: All tests PASS. The masthead and CSS structural tests should both be green.

- [ ] **Step 4: Commit (skip if not a git repo)**

```bash
git add dashboard/assets/style.css
git commit -m "feat(css): style the account seal"
```

---

## Task 5: Manual visual verification

**Files:** none modified.

- [ ] **Step 1: Start the dev server**

Run: `python dashboard/app.py`

Expected: Dash boots on `http://127.0.0.1:8050/`. No traceback in the terminal.

- [ ] **Step 2: Open the app and check the signed-out state**

Visit `http://127.0.0.1:8050/` in a private/incognito window (no session cookie). Verify in the top-right of the masthead:

- A boxed frame appears with a thin ink border and a small copper-soft drop shadow offset to the bottom-right.
- The eyebrow reads `NEWSSTAND` in small-caps copper.
- Body reads `Pick up a copy` in serif italic.
- A 1px hairline rule sits below the body.
- Action row reads `SIGN IN · SIGN UP` in mono small-caps; hovering either link turns it copper and underlines.

Take a screenshot for the PR / record.

- [ ] **Step 3: Sign in and check the signed-in state**

Sign up or sign in via `/auth/signup` or `/auth/login`. Return to `/` and verify:

- Same frame as above.
- Eyebrow reads `ACCOUNT`.
- Body shows the display name in serif italic.
- Action row reads `PROFILE · SIGN OUT`; `Sign out` is now a styled link, NOT a default browser button.
- Clicking `Sign out` still posts to `/auth/logout` and returns to the signed-out state.

Take a screenshot.

- [ ] **Step 4: Resize the viewport**

Drag the browser narrower than 1100px:
- The seal should drop into the natural column flow of `.vol` (stacked below the `Vol. I` / tagline lines), still framed, still no wider than ~18rem.

Drag back to ≥ 1100px:
- The seal should snap to the right edge of the masthead via the existing flex rule.

- [ ] **Step 5: Hard-stop the dev server**

`Ctrl+C` in the terminal running `python dashboard/app.py`.

---

## Self-Review Notes

- **Spec coverage:** every section of `docs/superpowers/specs/2026-05-26-account-seal-design.md` maps to a task — visual treatment (Task 4), HTML structure (Task 2), test for selector presence (Task 3), test for component structure (Task 1), and the `Sign out` button restyle is covered by `.account-seal__action` in Task 4 + the structure assertion in Task 1.
- **No placeholders:** every code block is concrete; every command has an expected outcome.
- **Type / name consistency:** `_signed_in_links` / `_anon_links` return `html.Div` in Task 2 (previously `html.Span`); the test in Task 1 doesn't pin the wrapper element type, only classes and text — so the return-type change does not break Task 1's assertions.
- **No `@media (max-width: ...)`:** the new CSS block is base-only; no media queries added, so `test_no_max_width_media_queries` stays green.
