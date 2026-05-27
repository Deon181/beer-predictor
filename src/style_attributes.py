"""Style → taste-attribute mapping.

For each beer style we publish a baseline tuple
``(sweetness, maltiness, hoppiness_base, body, sourness)``
on a 0–10 scale, derived from BJCP style guideline descriptions.

These are baselines: per-beer ABV / IBU then refine the final taste
vector. ``bitterness`` is computed from IBU directly (IBU/10 capped),
``hoppiness`` blends the style baseline with IBU, and the other four
attributes are pure style baselines.

Rare styles fall back to ``DEFAULT_STYLE_ATTRS``.

Reference: BJCP 2021 Style Guidelines (publicly available, fair use of
factual descriptors).
"""
from __future__ import annotations

from typing import Mapping

# (sweetness, maltiness, hoppiness_base, body, sourness) — all 0–10
StyleTuple = tuple[float, float, float, float, float]

STYLE_ATTRS: Mapping[str, StyleTuple] = {
    # IPAs
    "American IPA": (3, 5, 8, 6, 0),
    "Imperial IPA": (3, 6, 9, 7, 0),
    "Session IPA": (2, 3, 7, 4, 0),
    "New England IPA": (4, 5, 8, 6, 1),
    # Pale Ales / Bitters
    "American Pale Ale": (3, 5, 6, 5, 0),
    "English Pale Ale": (4, 6, 4, 5, 0),
    "Premium Bitter": (3, 5, 5, 5, 0),
    "Strong Bitter": (4, 6, 5, 6, 0),
    "Ordinary Bitter": (3, 4, 4, 4, 0),
    "Belgian Pale Ale": (4, 5, 4, 5, 1),
    # Ambers / Reds
    "American Amber Ale": (5, 6, 5, 6, 0),
    "Irish Red Ale": (5, 7, 3, 5, 0),
    "American Amber Lager": (4, 5, 3, 4, 0),
    # Browns
    "British Brown Ale": (5, 7, 3, 5, 0),
    "American Brown Ale": (5, 7, 5, 6, 0),
    # Porters
    "English Porter": (5, 7, 4, 6, 0),
    "American Porter": (5, 7, 5, 7, 0),
    "Smoked Porter": (4, 7, 5, 7, 0),
    "Baltic Porter": (6, 8, 4, 8, 0),
    # Stouts
    "Irish Stout": (3, 6, 4, 6, 1),
    "Sweet Stout": (8, 7, 3, 8, 0),
    "Oatmeal Stout": (6, 7, 3, 7, 0),
    "American Stout": (5, 7, 6, 7, 0),
    "Imperial Stout": (7, 8, 5, 9, 0),
    "Russian Imperial Stout": (7, 9, 5, 9, 0),
    "Foreign Extra Stout": (6, 8, 5, 8, 0),
    # Lagers
    "Czech Pilsner": (3, 5, 5, 4, 0),
    "German Pilsner": (2, 4, 6, 3, 0),
    "Munich Helles": (4, 6, 3, 5, 0),
    "Munich Dunkel": (5, 7, 3, 6, 0),
    "Märzen": (5, 7, 3, 6, 0),
    "Vienna Lager": (4, 6, 3, 5, 0),
    "Schwarzbier": (4, 6, 3, 5, 0),
    "American Lager": (3, 3, 2, 3, 0),
    "American Light Lager": (2, 2, 1, 2, 0),
    "International Pale Lager": (3, 4, 3, 3, 0),
    # Bocks
    "Doppelbock": (7, 9, 3, 8, 0),
    "Eisbock": (8, 9, 3, 9, 0),
    "Weizenbock": (6, 8, 3, 7, 1),
    # Wheats
    "Hefeweizen": (5, 5, 3, 5, 1),
    "Dunkelweizen": (5, 6, 3, 6, 1),
    "Witbier": (4, 4, 3, 4, 2),
    "American Wheat": (4, 4, 4, 4, 1),
    # Sour / Wild
    "Berliner Weisse": (3, 3, 2, 3, 9),
    "Gose": (3, 3, 2, 3, 8),
    "Gueuze": (3, 4, 3, 4, 9),
    "Fruit Lambic": (5, 4, 2, 4, 8),
    "Flanders Red": (5, 5, 3, 5, 8),
    "Flanders Pale Ale": (4, 5, 3, 5, 6),
    "American Wild Ale": (4, 4, 4, 5, 7),
    # Belgian
    "Belgian Tripel": (5, 5, 6, 6, 1),
    "Belgian Dubbel": (6, 7, 4, 7, 1),
    "Belgian Strong Pale": (5, 5, 5, 6, 1),
    "Belgian Strong Dark": (7, 8, 4, 8, 1),
    "Quadrupel": (8, 9, 4, 9, 1),
    "Saison": (3, 4, 5, 4, 2),
    # Specialty / Strong
    "Rauchbier": (4, 7, 3, 6, 0),
    "Kölsch": (3, 4, 4, 4, 0),
    "Cream Ale": (4, 4, 3, 4, 0),
    "American Barleywine": (6, 8, 7, 8, 0),
    "English Barleywine": (7, 9, 5, 8, 0),
    "Old Ale": (6, 8, 4, 8, 0),
    "Wee Heavy": (7, 9, 3, 8, 0),
    "Scotch Ale": (7, 9, 3, 8, 0),
    "American Strong Ale": (5, 7, 7, 7, 0),
    "Christmas/Winter Ale": (6, 7, 4, 7, 0),
    "Wood-Aged Ale": (6, 7, 3, 7, 0),
    "Düsseldorf Altbier": (4, 6, 4, 5, 0),
    "Fruit Beer": (6, 4, 3, 4, 1),
}

DEFAULT_STYLE_ATTRS: StyleTuple = (4, 5, 4, 5, 0)


def style_lookup(style: str) -> StyleTuple:
    """Return the BJCP-derived baseline tuple for a beer style."""
    return STYLE_ATTRS.get(style, DEFAULT_STYLE_ATTRS)


# Group rare/long-tail styles into broader buckets if they ever appear.
# For our curated catalog every style above is already covered, but the
# function is useful when ingesting external data.
STYLE_NORMALIZATION: Mapping[str, str] = {
    "IPA": "American IPA",
    "Double IPA": "Imperial IPA",
    "DIPA": "Imperial IPA",
    "NEIPA": "New England IPA",
    "Hazy IPA": "New England IPA",
    "Pale Ale": "American Pale Ale",
    "APA": "American Pale Ale",
    "Stout": "American Stout",
    "Porter": "American Porter",
    "Bitter": "Premium Bitter",
    "Pilsner": "German Pilsner",
    "Pils": "German Pilsner",
    "Wheat Beer": "American Wheat",
    "Lager": "American Lager",
    "Light Lager": "American Light Lager",
    "Tripel": "Belgian Tripel",
    "Dubbel": "Belgian Dubbel",
    "Quad": "Quadrupel",
}


def normalize_style(style: str) -> str:
    """Map alternate names to canonical style keys used by STYLE_ATTRS."""
    if style in STYLE_ATTRS:
        return style
    return STYLE_NORMALIZATION.get(style, style)
