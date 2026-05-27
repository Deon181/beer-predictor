"""Map OpenBeerDB style names → BJCP keys used by src/style_attributes.py.

OBDB ships ~140 style names (in data/raw/obdb/styles.csv). Most map cleanly
to a BJCP equivalent; a handful (gluten-free, non-alcoholic, "out of
category", sake-yeast, etc.) have no good match and are intentionally
absent. Rows whose OBDB style is absent from this map are dropped during
sampling.

When two OBDB styles map to the same BJCP key, that's by design — OBDB
slices styles more finely than the BJCP taste-attribute table.
"""
from __future__ import annotations

from typing import Mapping

OBDB_TO_BJCP: Mapping[str, str] = {
    # ---- English ales ----
    "Classic English-Style Pale Ale": "English Pale Ale",
    "English-Style India Pale Ale": "American IPA",
    "Ordinary Bitter": "Ordinary Bitter",
    "Special Bitter or Best Bitter": "Premium Bitter",
    "Extra Special Bitter": "Strong Bitter",
    "English-Style Summer Ale": "English Pale Ale",
    "English-Style Pale Mild Ale": "British Brown Ale",
    "English-Style Dark Mild Ale": "British Brown Ale",
    "English-Style Brown Ale": "British Brown Ale",
    "Old Ale": "Old Ale",
    "Strong Ale": "American Strong Ale",
    "British-Style Imperial Stout": "Russian Imperial Stout",
    "British-Style Barley Wine Ale": "English Barleywine",
    "Brown Porter": "English Porter",

    # ---- Scottish ----
    "Scottish-Style Light Ale": "Scotch Ale",
    "Scottish-Style Heavy Ale": "Scotch Ale",
    "Scottish-Style Export Ale": "Scotch Ale",
    "Scotch Ale": "Wee Heavy",

    # ---- Irish ----
    "Irish-Style Red Ale": "Irish Red Ale",
    "Classic Irish-Style Dry Stout": "Irish Stout",
    "Foreign (Export)-Style Stout": "Foreign Extra Stout",

    # ---- American ales ----
    "American-Style Pale Ale": "American Pale Ale",
    "Fresh Hop Ale": "American IPA",
    "American-Style Strong Pale Ale": "American Strong Ale",
    "American-Style India Pale Ale": "American IPA",
    "Imperial or Double India Pale Ale": "Imperial IPA",
    "American-Style Amber/Red Ale": "American Amber Ale",
    "Imperial or Double Red Ale": "American Strong Ale",
    "American-Style Barley Wine Ale": "American Barleywine",
    "American-Style Wheat Wine Ale": "American Barleywine",
    "Golden or Blonde Ale": "American Pale Ale",
    "American-Style Brown Ale": "American Brown Ale",
    "Pale American-Belgo-Style Ale": "Belgian Pale Ale",
    "Dark American-Belgo-Style Ale": "Belgian Strong Dark",
    "American-Style Sour Ale": "American Wild Ale",
    "American-Style India Black Ale": "American Stout",
    "American-Style Stout": "American Stout",
    "American-Style Imperial Stout": "Imperial Stout",
    "American-Style Imperial Porter": "American Porter",
    "Robust Porter": "American Porter",
    "Smoke Porter": "Smoked Porter",
    "Porter": "American Porter",
    "Sweet Stout": "Sweet Stout",
    "Oatmeal Stout": "Oatmeal Stout",
    "Specialty Stouts": "American Stout",

    # ---- German ales & wheats ----
    "German-Style Kolsch": "Kölsch",
    "Berliner-Style Weisse": "Berliner Weisse",
    "Leipzig-Style Gose": "Gose",
    "South German-Style Hefeweizen": "Hefeweizen",
    "South German-Style Kristal Weizen": "Hefeweizen",
    "German-Style Leichtes Weizen": "Hefeweizen",
    "South German-Style Bernsteinfarbenes Weizen": "Hefeweizen",
    "South German-Style Dunkel Weizen": "Dunkelweizen",
    "South German-Style Weizenbock": "Weizenbock",
    "Bamberg-Style Weiss Rauchbier": "Rauchbier",
    "German-Style Brown Ale/Altbier": "Düsseldorf Altbier",

    # ---- Belgian / French ----
    "Belgian-Style Flanders/Oud Bruin": "Flanders Red",
    "Belgian-Style Dubbel": "Belgian Dubbel",
    "Belgian-Style Tripel": "Belgian Tripel",
    "Belgian-Style Quadrupel": "Quadrupel",
    "Belgian-Style Blonde Ale": "Belgian Pale Ale",
    "Belgian-Style Pale Ale": "Belgian Pale Ale",
    "Belgian-Style Pale Strong Ale": "Belgian Strong Pale",
    "Belgian-Style Dark Strong Ale": "Belgian Strong Dark",
    "Belgian-Style White": "Witbier",
    "Belgian-Style Lambic": "Gueuze",
    "Belgian-Style Gueuze Lambic": "Gueuze",
    "Belgian-Style Fruit Lambic": "Fruit Lambic",
    "Belgian-Style Table Beer": "Belgian Pale Ale",
    "Other Belgian-Style Ales": "Belgian Pale Ale",
    "French-Style Biere de Garde": "Saison",
    "French & Belgian-Style Saison": "Saison",

    # ---- Pale ale family (international) ----
    "International-Style Pale Ale": "American Pale Ale",
    "Australasian-Style Pale Ale": "American Pale Ale",

    # ---- European lagers ----
    "German-Style Pilsener": "German Pilsner",
    "Bohemian-Style Pilsener": "Czech Pilsner",
    "European Low-Alcohol Lager": "American Light Lager",
    "Munchner-Style Helles": "Munich Helles",
    "Dortmunder/European-Style Export": "Munich Helles",
    "Vienna-Style Lager": "Vienna Lager",
    "German-Style Marzen": "Märzen",
    "German-Style Oktoberfest": "Märzen",
    "European-Style Dark": "Munich Dunkel",
    "German-Style Schwarzbier": "Schwarzbier",
    "Bamberg-Style Marzen": "Rauchbier",
    "Bamberg-Style Helles Rauchbier": "Rauchbier",
    "Bamberg-Style Bock Rauchbier": "Rauchbier",
    "Traditional German-Style Bock": "Doppelbock",
    "German-Style Heller Bock/Maibock": "Doppelbock",
    "German-Style Doppelbock": "Doppelbock",
    "German-Style Eisbock": "Eisbock",
    "Baltic-Style Porter": "Baltic Porter",

    # ---- American lagers ----
    "American-Style Lager": "American Lager",
    "American-Style Light Lager": "American Light Lager",
    "American-Style Low-Carb Light Lager": "American Light Lager",
    "American-Style Amber Lager": "American Amber Lager",
    "American-Style Premium Lager": "American Lager",
    "American-Style Pilsener": "German Pilsner",
    "American-Style Ice Lager": "American Lager",
    "American-Style Malt Liquor": "American Lager",
    "American-Style Marzen/Oktoberfest": "Märzen",
    "American-Style Dark Lager": "Munich Dunkel",
    "American-Style Cream Ale or Lager": "Cream Ale",
    "California Common Beer": "American Amber Lager",

    # ---- International light lagers ----
    "Australasian-Style Light Lager": "International Pale Lager",
    "Latin American-Style Light Lager": "International Pale Lager",
    "Tropical-Style Light Lager": "International Pale Lager",
    "International-Style Pilsener": "International Pale Lager",
    "Dry Lager": "American Lager",

    # ---- Session / specialty ----
    "Session Beer": "Session IPA",

    # ---- Wheat & rye ----
    "Light American Wheat Ale or Lager": "American Wheat",
    "Dark American Wheat Ale or Lager": "American Wheat",
    "Fruit Wheat Ale or Lager": "Fruit Beer",
    "American Rye Ale or Lager": "American Pale Ale",

    # ---- Flavored specialty ----
    "Fruit Beer": "Fruit Beer",
    "Field Beer": "Fruit Beer",
    "Pumpkin Beer": "Fruit Beer",
    "Chocolate/Cocoa-Flavored Beer": "American Stout",
    "Coffee-Flavored Beer": "American Stout",
    "Herb and Spice Beer": "Christmas/Winter Ale",
    "Smoke Beer": "Rauchbier",
    "Winter Warmer": "Christmas/Winter Ale",

    # ---- Wood-aged ----
    "Wood- and Barrel-Aged Beer": "Wood-Aged Ale",
    "Wood- and Barrel-Aged Pale to Amber Beer": "Wood-Aged Ale",
    "Wood- and Barrel-Aged Dark Beer": "Wood-Aged Ale",
    "Wood- and Barrel-Aged Strong Beer": "Wood-Aged Ale",
    "Wood- and Barrel-Aged Sour Beer": "American Wild Ale",
    "Aged Beer": "Old Ale",
    "Other Strong Ale or Lager": "American Strong Ale",

    # Intentionally NOT mapped (no reasonable BJCP equivalent):
    # - "Specialty Beer", "Specialty Honey Lager or Ale"
    # - "Gluten-Free Beer", "Non-Alcoholic Beer"
    # - "Experimental Beer", "Out of Category"
    # - "Japanese Sake-Yeast Beer"
    # - "German-Style Rye Ale" (no rye style in BJCP keys)
    # - "Kellerbier - Ale", "Kellerbier - Lager" (unfiltered variants without a clean match)
    # Rows with these styles are dropped during sampling.
}


def to_bjcp(obdb_style: str) -> str | None:
    """Return the BJCP key for an OBDB style, or None if unmapped."""
    return OBDB_TO_BJCP.get(obdb_style)
