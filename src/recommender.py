"""Beer recommender — content-based on the engineered taste vector.

Core API
--------
- ``load_catalog()``: cached load of the processed parquet catalog.
- ``recommend(taste_profile, top_k, filters)``: return the top-``k`` closest
  beers to the user's slider profile, optionally constrained by filters.
- ``explain(beer_row, taste_profile)``: short, human-readable description of
  why a beer matched.

Distance is plain Euclidean over the seven 0–10 axes. Match score is mapped
to 0–100 via ``100 / (1 + distance)`` so a perfect match prints 100.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "processed" / "beers.parquet"

TASTE_COLS: tuple[str, ...] = (
    "bitterness",
    "sweetness",
    "maltiness",
    "hoppiness",
    "body",
    "sourness",
    "abv_normalized",
)

# Friendly slider labels exposed by the dashboard. The dashboard uses
# "abv preference" as a slider label and we map it onto abv_normalized.
SLIDER_TO_COLUMN: Mapping[str, str] = {
    "bitterness": "bitterness",
    "sweetness": "sweetness",
    "maltiness": "maltiness",
    "hoppiness": "hoppiness",
    "body": "body",
    "sourness": "sourness",
    "abv": "abv_normalized",
    "abv_preference": "abv_normalized",
    "abv_normalized": "abv_normalized",
}


@lru_cache(maxsize=1)
def load_catalog(path: str | None = None) -> pd.DataFrame:
    """Load the processed beer catalog. Cached so callers can hammer it."""
    p = Path(path) if path else CATALOG_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"Processed catalog not found at {p}. Run the data_prep notebook first."
        )
    df = pd.read_parquet(p)
    return df.reset_index(drop=True)


def _resolve_profile(taste_profile: Mapping[str, float]) -> np.ndarray:
    """Coerce a free-form taste-profile dict into an ordered taste vector."""
    out: list[float] = []
    for col in TASTE_COLS:
        # Find any incoming key that maps to this column.
        value: float | None = None
        if col in taste_profile:
            value = float(taste_profile[col])
        else:
            for key, mapped in SLIDER_TO_COLUMN.items():
                if mapped == col and key in taste_profile:
                    value = float(taste_profile[key])
                    break
        if value is None:
            value = 5.0  # neutral default
        out.append(float(np.clip(value, 0.0, 10.0)))
    return np.asarray(out, dtype=float)


def _apply_filters(
    df: pd.DataFrame, filters: Mapping[str, object] | None
) -> pd.DataFrame:
    if not filters:
        return df
    out = df
    min_abv = filters.get("min_abv")
    max_abv = filters.get("max_abv")
    if min_abv is not None:
        out = out[out["abv"] >= float(min_abv)]
    if max_abv is not None:
        out = out[out["abv"] <= float(max_abv)]
    styles = filters.get("styles")
    if styles:
        out = out[out["style"].isin(list(styles))]
    exclude_styles = filters.get("exclude_styles")
    if exclude_styles:
        out = out[~out["style"].isin(list(exclude_styles))]
    countries = filters.get("countries")
    if countries:
        out = out[out["country"].isin(list(countries))]
    return out.reset_index(drop=True)


def recommend(
    taste_profile: Mapping[str, float],
    top_k: int = 10,
    filters: Mapping[str, object] | None = None,
    catalog: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return the top-``k`` closest beers to ``taste_profile``.

    Parameters
    ----------
    taste_profile
        Mapping like ``{"bitterness": 7.0, "sweetness": 3.0, ...}``. Missing
        axes default to a neutral ``5.0``. Values are clipped to ``[0, 10]``.
    top_k
        Number of recommendations to return (clipped to the catalog size).
    filters
        Optional dict with any of: ``min_abv`` (float), ``max_abv`` (float),
        ``styles`` (Iterable[str]), ``exclude_styles`` (Iterable[str]),
        ``countries`` (Iterable[str]).
    catalog
        Override the default catalog (mostly for tests).

    Returns
    -------
    DataFrame
        Top-``k`` beers sorted by ``match_score`` descending. Adds
        ``distance`` and ``match_score`` (0–100) columns to the catalog
        columns.
    """
    df = catalog if catalog is not None else load_catalog()
    df = _apply_filters(df, filters)
    if df.empty:
        return df.assign(distance=pd.Series(dtype=float),
                         match_score=pd.Series(dtype=float))

    profile = _resolve_profile(taste_profile)
    matrix = df[list(TASTE_COLS)].to_numpy(dtype=float)
    diffs = matrix - profile
    distance = np.sqrt((diffs * diffs).sum(axis=1))
    score = 100.0 / (1.0 + distance)

    out = df.copy()
    out["distance"] = distance
    out["match_score"] = score
    out = out.sort_values("match_score", ascending=False, kind="mergesort")
    k = max(1, min(int(top_k), len(out)))
    return out.head(k).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Explanations
# ---------------------------------------------------------------------------
_LABELS: dict[str, tuple[str, str]] = {
    # column → (positive descriptor, negative descriptor)
    "bitterness": ("more bitter than", "less bitter than"),
    "sweetness": ("sweeter than", "drier than"),
    "maltiness": ("more malt-forward than", "less malty than"),
    "hoppiness": ("more hop-forward than", "less hop-forward than"),
    "body": ("fuller-bodied than", "lighter-bodied than"),
    "sourness": ("more sour than", "less sour than"),
    "abv_normalized": ("stronger than", "lighter in alcohol than"),
}


def _readable(col: str) -> str:
    return "ABV" if col == "abv_normalized" else col


def explain(
    beer_row: pd.Series | Mapping[str, float],
    taste_profile: Mapping[str, float],
) -> str:
    """Return a one-sentence reason for why ``beer_row`` matched ``taste_profile``.

    Focuses on the axes where the user expressed a strong preference
    (slider far from the neutral 5.0): for each, says whether the beer
    matched or missed.
    """
    profile = _resolve_profile(taste_profile)
    beer_vec = np.asarray(
        [float(beer_row[c]) for c in TASTE_COLS], dtype=float
    )
    diffs = beer_vec - profile  # positive => beer higher than asked
    abs_diffs = np.abs(diffs)

    # User intensity = how far each slider is from neutral 5.0
    intensity = np.abs(profile - 5.0)
    # Rank axes by user intensity (most opinionated first)
    ranked = np.argsort(-intensity)

    name = beer_row["name"] if "name" in beer_row else "this beer"
    style = beer_row.get("style", "") if hasattr(beer_row, "get") else beer_row["style"]

    matches: list[str] = []
    misses: list[tuple[str, float]] = []  # (column, signed diff)

    for idx in ranked:
        if intensity[idx] < 1.5:
            break  # the user didn't really care beyond this point
        col = TASTE_COLS[idx]
        if abs_diffs[idx] <= 1.5:
            matches.append(col)
        else:
            misses.append((col, float(diffs[idx])))

    parts: list[str] = []
    if matches:
        nice = ", ".join(_readable(c) for c in matches[:2])
        parts.append(f"Strong match on {nice}")
    else:
        # No strong opinions — find the 2 closest axes overall.
        overall = np.argsort(abs_diffs)[:2]
        nice = ", ".join(_readable(TASTE_COLS[i]) for i in overall)
        parts.append(f"Balanced match across {nice}")

    if misses:
        col, diff = misses[0]
        pos, neg = _LABELS[col]
        descriptor = pos if diff > 0 else neg
        parts.append(f"slightly {descriptor} you asked ({_readable(col)} off by {abs(diff):.1f})")

    style_text = f" — a {style}" if style else ""
    return f"{name}{style_text}. " + "; ".join(parts) + "."
