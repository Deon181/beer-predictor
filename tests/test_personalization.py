"""Tests for src.personalization.personalized_defaults — pure function."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.personalization import (
    SLIDER_AXES_KEYS,
    personalized_defaults,
)


def _mini_catalog() -> pd.DataFrame:
    """Tiny catalog: two distinct taste-vector beers for testing."""
    rows = [
        # hop bomb
        {"beer_id": "hop__bomb", "name": "Hop Bomb", "brewery": "X", "style": "IPA",
         "country": "USA", "abv": 7.0, "ibu": 90, "srm": 6,
         "bitterness": 9.0, "sweetness": 1.0, "maltiness": 3.0, "hoppiness": 9.0,
         "body": 5.0, "sourness": 0.0, "abv_normalized": 5.8},
        # malt bomb
        {"beer_id": "malt__bomb", "name": "Malt Bomb", "brewery": "Y", "style": "Stout",
         "country": "USA", "abv": 8.0, "ibu": 35, "srm": 35,
         "bitterness": 3.0, "sweetness": 7.0, "maltiness": 9.0, "hoppiness": 2.0,
         "body": 9.0, "sourness": 0.0, "abv_normalized": 6.7},
    ]
    return pd.DataFrame(rows)


def test_returns_none_when_no_ratings() -> None:
    cat = _mini_catalog()
    assert personalized_defaults([], cat) is None


def test_returns_none_when_no_ratings_at_or_above_4() -> None:
    cat = _mini_catalog()
    ratings = [
        {"beer_id": "hop__bomb", "rating": 3.5},
        {"beer_id": "malt__bomb", "rating": 2.0},
    ]
    assert personalized_defaults(ratings, cat) is None


def test_single_5star_returns_that_beer_vector_as_sliders() -> None:
    cat = _mini_catalog()
    ratings = [{"beer_id": "hop__bomb", "rating": 5.0}]
    defaults = personalized_defaults(ratings, cat)
    assert defaults is not None
    # abv_normalized maps to abv_preference for the slider
    assert defaults["bitterness"] == 9.0
    assert defaults["hoppiness"] == 9.0
    assert defaults["abv_preference"] == 5.8
    # all returned keys are slider keys, not column keys
    assert set(defaults.keys()) == set(SLIDER_AXES_KEYS)


def test_weighted_average_5star_outweighs_4star() -> None:
    """5★ has weight 2.0, 4★ has weight 1.0 — so result leans toward 5★."""
    cat = _mini_catalog()
    ratings = [
        {"beer_id": "hop__bomb", "rating": 5.0},   # weight 2.0
        {"beer_id": "malt__bomb", "rating": 4.0},  # weight 1.0
    ]
    defaults = personalized_defaults(ratings, cat)
    assert defaults is not None
    # bitterness: (2.0*9.0 + 1.0*3.0) / 3.0 = 7.0
    assert defaults["bitterness"] == pytest.approx(7.0)
    # hoppiness:  (2.0*9.0 + 1.0*2.0) / 3.0 = 6.666...
    assert defaults["hoppiness"] == pytest.approx(20.0 / 3.0)


def test_clips_to_0_10() -> None:
    """Hypothetical out-of-range beer values still produce clipped sliders."""
    cat = pd.DataFrame([{
        "beer_id": "wild__one", "name": "X", "brewery": "Y", "style": "Z",
        "country": "USA", "abv": 5, "ibu": 0, "srm": 0,
        "bitterness": 15.0, "sweetness": -3.0, "maltiness": 5.0, "hoppiness": 5.0,
        "body": 5.0, "sourness": 5.0, "abv_normalized": 5.0,
    }])
    defaults = personalized_defaults([{"beer_id": "wild__one", "rating": 5.0}], cat)
    assert defaults is not None
    assert defaults["bitterness"] == 10.0
    assert defaults["sweetness"] == 0.0


def test_orphan_beer_id_is_skipped() -> None:
    """Ratings whose beer_id no longer exists in the catalog are dropped."""
    cat = _mini_catalog()
    ratings = [
        {"beer_id": "vanished__beer", "rating": 5.0},
        {"beer_id": "hop__bomb", "rating": 5.0},
    ]
    defaults = personalized_defaults(ratings, cat)
    assert defaults is not None
    # Should equal the hop bomb vector alone (the orphan is dropped).
    assert defaults["bitterness"] == 9.0
