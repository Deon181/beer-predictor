import type { Beer, Filters, Recommendation, TasteProfile } from "./types";
import { AXES, normalizeActiveAxes, type AxisKey } from "./axes";

/** Beer columns used for the taste vector, in canonical order. */
export const TASTE_COLS = AXES.map((a) => a.column) as Array<
  "bitterness" | "sweetness" | "maltiness" | "hoppiness" | "body" | "sourness" | "abv_normalized"
>;

function clamp(v: number): number {
  return Math.max(0, Math.min(10, v));
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
  filters?: Filters,
  activeAxes?: AxisKey[]
): Recommendation[] {
  const filtered = applyFilters(catalog, filters);
  if (filtered.length === 0) return [];

  const active = normalizeActiveAxes(activeAxes ?? null);
  const axisDefs = AXES.filter((a) => active.includes(a.key));

  const scored = filtered.map((beer) => {
    let sumSq = 0;
    for (const a of axisDefs) {
      const diff = (beer[a.column] as number) - clamp(profile[a.key]);
      sumSq += diff * diff;
    }
    const distance = Math.sqrt(sumSq);
    const match_score = 100 / (1 + distance);
    return { ...beer, distance, match_score };
  });

  scored.sort((a, b) => b.match_score - a.match_score);
  return scored.slice(0, Math.max(1, Math.min(topK, scored.length)));
}

const LABELS: Record<string, [string, string]> = {
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

export function explain(
  beer: Beer,
  profile: TasteProfile,
  activeAxes?: AxisKey[]
): string {
  const active = normalizeActiveAxes(activeAxes ?? null);
  const axisDefs = AXES.filter((a) => active.includes(a.key));

  const rows = axisDefs.map((a) => {
    const target = clamp(profile[a.key]);
    const beerVal = beer[a.column] as number;
    const diff = beerVal - target;
    return {
      col: a.column as string,
      diff,
      absDiff: Math.abs(diff),
      intensity: Math.abs(target - 5.0),
    };
  });

  const ranked = rows
    .map((r, i) => ({ r, i }))
    .sort((a, b) => b.r.intensity - a.r.intensity)
    .map((x) => x.i);

  const matches: string[] = [];
  const misses: [string, number][] = [];

  for (const idx of ranked) {
    if (rows[idx].intensity < 1.5) break;
    if (rows[idx].absDiff <= 1.5) matches.push(rows[idx].col);
    else misses.push([rows[idx].col, rows[idx].diff]);
  }

  const parts: string[] = [];
  if (matches.length > 0) {
    parts.push(`Strong match on ${matches.slice(0, 2).map(readable).join(", ")}`);
  } else {
    const overall = [...rows]
      .sort((a, b) => a.absDiff - b.absDiff)
      .slice(0, 2)
      .map((r) => readable(r.col));
    parts.push(`Balanced match across ${overall.join(", ")}`);
  }

  if (misses.length > 0) {
    const [col, diff] = misses[0];
    const [pos, neg] = LABELS[col];
    const descriptor = diff > 0 ? pos : neg;
    parts.push(
      `slightly ${descriptor} you asked (${readable(col)} off by ${Math.abs(diff).toFixed(1)})`
    );
  }

  const style = beer.style ? ` — a ${beer.style}` : "";
  return `${beer.name}${style}. ${parts.join("; ")}.`;
}
