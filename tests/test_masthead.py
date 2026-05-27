"""Structural tests for dashboard/components/masthead.py.

Pins the helpers that build the masthead header: account link and
back-link behaviour on the profile page.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dash import html

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.masthead import (  # noqa: E402
    _account_link,
)


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


def _walk_anchors(component) -> list[dict]:
    """Return every html.A in the tree as {href, className, text}."""
    result: list[dict] = []
    stack = [component]
    while stack:
        node = stack.pop()
        if isinstance(node, html.A):
            result.append({
                "href": getattr(node, "href", None),
                "className": getattr(node, "className", "") or "",
                "text": _walk_text(node),
            })
        children = getattr(node, "children", None)
        if children is None:
            continue
        if isinstance(children, (list, tuple)):
            stack.extend(children)
        else:
            stack.append(children)
    return result


# ───── account link ───────────────────────────────────────────────

def test_signed_in_account_links_to_profile():
    block = _account_link(signed_in=True)
    classes = _walk_classes(block)
    text = _walk_text(block)
    anchors = _walk_anchors(block)

    assert "nav-strip__account" in classes
    assert "nav-strip__link" in classes
    assert "Account" in text
    assert any(a["href"] == "/profile" for a in anchors)


def test_anon_account_links_to_login():
    block = _account_link(signed_in=False)
    classes = _walk_classes(block)
    text = _walk_text(block)
    anchors = _walk_anchors(block)

    assert "nav-strip__account" in classes
    assert "nav-strip__link" in classes
    assert "Account" in text
    assert any(a["href"] == "/auth/login" for a in anchors)
