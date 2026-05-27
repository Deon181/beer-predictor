import type { Beer, Filters, Recommendation, TasteProfile } from "./types";

export const TASTE_COLS = [
  "bitterness",
  "sweetness",
  "maltiness",
  "hoppiness",
  "body",
  "sourness",
  "abv_normalized",
] as const;

type TasteCol = (typeof TASTE_COLS)[number];

const SLIDER_TO_COLUMN: Record<string, TasteCol> = {
  bitterness: "bitterness",
  sweetness: "sweetness",
  maltiness: "maltiness",
  hoppiness: "hoppiness",
  body: "body",
  sourness: "sourness",
  abv_preference: "abv_normalized",
};

function resolveProfile(profile: TasteProfile): number[] {
  return TASTE_COLS.map((col) => {
    for (const [key, mapped] of Object.entries(SLIDER_TO_COLUMN)) {
      if (mapped === col && key in profile) {
        return Math.max(0, Math.min(10, profile[key as keyof TasteProfile]));
      }
    }
    return 5.0;
  });
}

function applyFilters(beers: Beer[], filters?: Filters): Beer[] {
  if (!filters) return beers;
  let out = beers;
  if (filters.minAbv != null) out = out.filter((b) => b.abv >= filters.minAbv!);
  if (filters.maxAbv != null) out = out.filter((b) => b.abv <= filters.maxAbv!);
  if (filters.styles?.length)
    out = out.filter((b) => filters.styles!.includes(b.style));
  if (filters.countries?.length)
    out = out.filter((b) => filters.countries!.includes(b.country));
  return out;
}

export function recommend(
  catalog: Beer[],
  profile: TasteProfile,
  topK: number = 10,
  filters?: Filters
): Recommendation[] {
  const filtered = applyFilters(catalog, filters);
  if (filtered.length === 0) return [];

  const vec = resolveProfile(profile);
  const scored = filtered.map((beer) => {
    let sumSq = 0;
    for (let i = 0; i < TASTE_COLS.length; i++) {
      const diff = beer[TASTE_COLS[i]] - vec[i];
      sumSq += diff * diff;
    }
    const distance = Math.sqrt(sumSq);
    const match_score = 100 / (1 + distance);
    return { ...beer, distance, match_score };
  });

  scored.sort((a, b) => b.match_score - a.match_score);
  return scored.slice(0, Math.max(1, Math.min(topK, scored.length)));
}

const LABELS: Record<TasteCol, [string, string]> = {
  bitterness: ["more bitter than", "less bitter than"],
  sweetness: ["sweeter than", "drier than"],
  maltiness: ["more malt-forward than", "less malty than"],
  hoppiness: ["more hop-forward than", "less hop-forward than"],
  body: ["fuller-bodied than", "lighter-bodied than"],
  sourness: ["more sour than", "less sour than"],
  abv_normalized: ["stronger than", "lighter in alcohol than"],
};

function readable(col: string): string {
  return col === "abv_normalized" ? "ABV" : col;
}

export function explain(beer: Beer, profile: TasteProfile): string {
  const vec = resolveProfile(profile);
  const beerVec = TASTE_COLS.map((c) => beer[c]);
  const diffs = beerVec.map((v, i) => v - vec[i]);
  const absDiffs = diffs.map(Math.abs);
  const intensity = vec.map((v) => Math.abs(v - 5.0));

  const ranked = intensity
    .map((v, i) => ({ v, i }))
    .sort((a, b) => b.v - a.v)
    .map((x) => x.i);

  const matches: string[] = [];
  const misses: [string, number][] = [];

  for (const idx of ranked) {
    if (intensity[idx] < 1.5) break;
    const col = TASTE_COLS[idx];
    if (absDiffs[idx] <= 1.5) {
      matches.push(col);
    } else {
      misses.push([col, diffs[idx]]);
    }
  }

  const parts: string[] = [];
  if (matches.length > 0) {
    const nice = matches
      .slice(0, 2)
      .map(readable)
      .join(", ");
    parts.push(`Strong match on ${nice}`);
  } else {
    const overall = absDiffs
      .map((v, i) => ({ v, i }))
      .sort((a, b) => a.v - b.v)
      .slice(0, 2)
      .map((x) => readable(TASTE_COLS[x.i]));
    parts.push(`Balanced match across ${overall.join(", ")}`);
  }

  if (misses.length > 0) {
    const [col, diff] = misses[0];
    const [pos, neg] = LABELS[col as TasteCol];
    const descriptor = diff > 0 ? pos : neg;
    parts.push(
      `slightly ${descriptor} you asked (${readable(col)} off by ${Math.abs(diff).toFixed(1)})`
    );
  }

  const style = beer.style ? ` — a ${beer.style}` : "";
  return `${beer.name}${style}. ${parts.join("; ")}.`;
}
