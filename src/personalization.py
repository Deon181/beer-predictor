"""Compute personalized slider defaults from a user's ratings.

Pure function — no Supabase calls. Tests run offline with fabricated data.
The caller (the recommender sidebar) is responsible for fetching the
user's ratings via user_client() and passing them in.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional

import numpy as np
import pandas as pd

from src.recommender import TASTE_COLS

# Inverse of SLIDER_TO_COLUMN, for the keys we expose: column → slider key.
_COL_TO_SLIDER = {
    "bitterness": "bitterness",
    "sweetness": "sweetness",
    "maltiness": "maltiness",
    "hoppiness": "hoppiness",
    "body": "body",
    "sourness": "sourness",
    "abv_normalized": "abv_preference",
}

SLIDER_AXES_KEYS = tuple(_COL_TO_SLIDER.values())

# Only ratings >= this threshold contribute to the personalized profile.
_LIKE_THRESHOLD = 4.0


def personalized_defaults(
    ratings: Iterable[Mapping[str, object]],
    catalog: pd.DataFrame,
) -> Optional[dict[str, float]]:
    """Return slider defaults from a user's likes, or None if no likes.

    Parameters
    ----------
    ratings
        Iterable of mappings with at least `beer_id` (str) and `rating` (float).
    catalog
        The processed beer catalog (one row per beer; must include
        `beer_id` and every column in TASTE_COLS).

    Returns
    -------
    dict[str, float] or None
        Slider-key dict (bitterness, sweetness, …, abv_preference) clipped
        to [0, 10]. Returns None if the user has no ratings >= 4★ (or all
        their liked beers are orphaned).
    """
    if catalog is None or catalog.empty:
        return None

    liked = [
        r for r in ratings
        if float(r.get("rating", 0.0)) >= _LIKE_THRESHOLD
    ]
    if not liked:
        return None

    # Index the catalog by beer_id for fast lookup.
    cat_by_id = catalog.set_index("beer_id")
    accum = np.zeros(len(TASTE_COLS), dtype=float)
    total_weight = 0.0

    for r in liked:
        beer_id = r["beer_id"]
        if beer_id not in cat_by_id.index:
            continue  # orphan — beer no longer in catalog
        rating = float(r["rating"])
        weight = rating - 3.0  # 4★→1.0, 4.5★→1.5, 5★→2.0
        row = cat_by_id.loc[beer_id, list(TASTE_COLS)].to_numpy(dtype=float)
        accum += weight * row
        total_weight += weight

    if total_weight == 0.0:
        return None

    vector = np.clip(accum / total_weight, 0.0, 10.0)
    out: dict[str, float] = {}
    for col, val in zip(TASTE_COLS, vector):
        slider_key = _COL_TO_SLIDER[col]
        out[slider_key] = float(val)
    return out
