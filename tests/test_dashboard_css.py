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

    Limitation: only matches the bare ``@media (<condition>) { ... }`` form.
    Compound queries with type or operator prefixes — such as
    ``@media screen and (min-width: 1100px) { ... }`` or
    ``@media only screen and (min-width: 1100px) { ... }`` — are not
    matched by the underlying regex ``r"@media\\s*\\(([^)]*)\\)\\s*\\{"``.
    The project convention is to write bare media queries so that this helper
    continues to work.  If you add a compound query and this helper returns
    None when you expect a match, that is the reason.
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
    ".nav-strip",
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
