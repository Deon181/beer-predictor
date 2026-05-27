"""beer_id must be a stable, slug-format string suitable for use as a
foreign reference from external systems (Supabase user_beers)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from pandas.api.types import is_string_dtype

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_catalog import slugify_beer_id

SLUG_RE = re.compile(r"^[a-z0-9-]+__[a-z0-9-]+$")


def test_slugify_basic() -> None:
    assert slugify_beer_id("Stone Brewing", "Arrogant Bastard Ale") == (
        "stone-brewing__arrogant-bastard-ale"
    )


def test_slugify_strips_punctuation() -> None:
    assert slugify_beer_id("Devil's Peak", "King's Blockhouse IPA") == (
        "devils-peak__kings-blockhouse-ipa"
    )


def test_slugify_collapses_whitespace() -> None:
    assert slugify_beer_id("  Sierra   Nevada  ", "Pale Ale") == (
        "sierra-nevada__pale-ale"
    )


def test_slugify_handles_ampersand_and_slashes() -> None:
    assert slugify_beer_id("Brew & Co", "IPA/Pale") == "brew-co__ipa-pale"


def test_slugify_keeps_digits() -> None:
    assert slugify_beer_id("Brewery 21", "Beer #4") == "brewery-21__beer-4"


def test_slug_matches_format() -> None:
    """Every produced slug matches SLUG_RE."""
    cases = [
        ("Stone Brewing", "Arrogant Bastard"),
        ("Devil's Peak", "King's Blockhouse"),
        ("Brewery 21", "Beer #4"),
        ("Brew & Co", "IPA/Pale"),
    ]
    for brewery, name in cases:
        slug = slugify_beer_id(brewery, name)
        assert SLUG_RE.match(slug), f"bad slug: {slug}"


def test_slugify_preserves_asterisk_as_star() -> None:
    """BrewDog convention: `Tokyo*` is the high-ABV variant of `Tokyo` —
    they're distinct beers and must produce distinct slugs."""
    assert slugify_beer_id("BrewDog Ltd", "Tokyo*") == "brewdog-ltd__tokyo-star"
    assert slugify_beer_id("BrewDog Ltd", "Tokyo") == "brewdog-ltd__tokyo"
    assert slugify_beer_id("BrewDog Ltd", "Tokyo*") != slugify_beer_id("BrewDog Ltd", "Tokyo")


def test_built_catalog_slugs_are_strings_and_unique() -> None:
    """End-to-end: the generated CSV uses string slugs and they're unique."""
    csv = ROOT / "data" / "raw" / "curated_beers.csv"
    assert csv.exists(), "run scripts/build_catalog.py first"
    df = pd.read_csv(csv)
    assert is_string_dtype(df["beer_id"]), (
        f"beer_id should be string, got {df['beer_id'].dtype}"
    )
    assert df["beer_id"].is_unique
    for slug in df["beer_id"].head(20):
        assert SLUG_RE.match(slug), f"bad slug in built catalog: {slug}"
