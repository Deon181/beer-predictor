"""Tests for the OBDB → BJCP style alias map."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.style_aliases import OBDB_TO_BJCP, to_bjcp
from src.style_attributes import STYLE_ATTRS

OBDB_STYLES = ROOT / "data" / "raw" / "obdb" / "styles.csv"


def test_every_mapped_value_is_a_valid_bjcp_key() -> None:
    bjcp_keys = set(STYLE_ATTRS.keys())
    bad = {k: v for k, v in OBDB_TO_BJCP.items() if v not in bjcp_keys}
    assert not bad, f"mapped values not in STYLE_ATTRS: {bad}"


def test_to_bjcp_returns_none_for_unmapped_style() -> None:
    assert to_bjcp("Definitely Not A Real Style") is None


def test_to_bjcp_returns_mapping_for_known_style() -> None:
    assert to_bjcp("American-Style India Pale Ale") == "American IPA"


def test_map_covers_styles_needed_by_recommender_tests() -> None:
    """The recommender's extreme-profile tests depend on specific BJCP keys
    appearing in the final catalog. Confirm the alias map can produce each."""
    required_bjcp = {
        "American IPA",
        "Imperial IPA",
        "American Barleywine",
        "Sweet Stout",
        "Imperial Stout",
        "Saison",
        "Doppelbock",
    }
    produced = set(OBDB_TO_BJCP.values())
    missing = required_bjcp - produced
    assert not missing, f"alias map cannot produce: {missing}"


@pytest.mark.skipif(not OBDB_STYLES.exists(), reason="run scripts/fetch_obdb.py first")
def test_alias_map_covers_at_least_half_of_obdb_styles() -> None:
    styles = pd.read_csv(OBDB_STYLES)
    obdb_names = set(styles["style_name"].dropna().astype(str))
    covered = obdb_names & set(OBDB_TO_BJCP.keys())
    ratio = len(covered) / max(1, len(obdb_names))
    assert ratio >= 0.5, (
        f"only {ratio:.0%} of OBDB styles mapped "
        f"({len(covered)}/{len(obdb_names)})"
    )
