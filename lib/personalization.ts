import type { Beer, TasteProfile, UserRating } from "./types";
import { TASTE_COLS } from "./recommender";

const LIKE_THRESHOLD = 4.0;

const COL_TO_SLIDER: Record<string, keyof TasteProfile> = {
  bitterness: "bitterness",
  sweetness: "sweetness",
  maltiness: "maltiness",
  hoppiness: "hoppiness",
  body: "body",
  sourness: "sourness",
  abv_normalized: "abv_preference",
};

export function personalizedDefaults(
  ratings: UserRating[],
  catalog: Beer[]
): TasteProfile | null {
  if (!catalog.length) return null;

  const liked = ratings.filter((r) => r.rating >= LIKE_THRESHOLD);
  if (!liked.length) return null;

  const byId = new Map(catalog.map((b) => [b.beer_id, b]));
  const accum = new Array(TASTE_COLS.length).fill(0);
  let totalWeight = 0;

  for (const r of liked) {
    const beer = byId.get(r.beer_id);
    if (!beer) continue;
    const weight = r.rating - 3.0;
    for (let i = 0; i < TASTE_COLS.length; i++) {
      accum[i] += weight * beer[TASTE_COLS[i]];
    }
    totalWeight += weight;
  }

  if (totalWeight === 0) return null;

  const result: Partial<TasteProfile> = {};
  for (let i = 0; i < TASTE_COLS.length; i++) {
    const col = TASTE_COLS[i];
    const sliderKey = COL_TO_SLIDER[col];
    result[sliderKey] = Math.max(0, Math.min(10, accum[i] / totalWeight));
  }
  return result as TasteProfile;
}
