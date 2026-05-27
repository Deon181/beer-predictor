import type { Beer } from "./types";

let cached: Beer[] | null = null;

export async function loadCatalog(): Promise<Beer[]> {
  if (cached) return cached;
  const res = await fetch("/data/beers.json");
  cached = (await res.json()) as Beer[];
  return cached;
}

export function getStyles(catalog: Beer[]): string[] {
  return [...new Set(catalog.map((b) => b.style))].sort();
}

export function getCountries(catalog: Beer[]): string[] {
  return [...new Set(catalog.map((b) => b.country))].sort();
}

export function getAbvRange(catalog: Beer[]): [number, number] {
  const abvs = catalog.map((b) => b.abv);
  return [Math.min(...abvs), Math.max(...abvs)];
}
