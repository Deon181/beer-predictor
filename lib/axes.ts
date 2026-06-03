import type { Beer, TasteProfile } from "./types";

export type AxisKey = keyof TasteProfile;

export interface Axis {
  /** Key on the TasteProfile (slider/profile value). */
  key: AxisKey;
  /** Display label. */
  label: string;
  /** Help / description text. */
  help: string;
  /** Column on Beer used for distance scoring. */
  column: keyof Beer;
}

export const AXES: Axis[] = [
  { key: "bitterness", label: "Bitter", help: "How sharp / hop-bitter you want it", column: "bitterness" },
  { key: "sweetness", label: "Sweet", help: "Caramel, residual sugar, malt sweetness", column: "sweetness" },
  { key: "maltiness", label: "Malty", help: "Bread, biscuit, toast, dark crystal", column: "maltiness" },
  { key: "hoppiness", label: "Hoppy", help: "Hop aroma + flavour intensity", column: "hoppiness" },
  { key: "body", label: "Body", help: "Mouthfeel from light/crisp to thick/chewy", column: "body" },
  { key: "sourness", label: "Sour", help: "Tart / acidic / Brettanomyces character", column: "sourness" },
  { key: "abv_preference", label: "Strength", help: "Session beer (0) → barleywine (10)", column: "abv_normalized" },
];

export const ALL_AXIS_KEYS: AxisKey[] = AXES.map((a) => a.key);

/**
 * Resolve a stored active-axis list into a clean ordered list of valid keys.
 * null / empty / all-invalid → all seven (the default).
 */
export function normalizeActiveAxes(
  saved: string[] | null | undefined
): AxisKey[] {
  if (!saved || saved.length === 0) return [...ALL_AXIS_KEYS];
  const valid = ALL_AXIS_KEYS.filter((k) => saved.includes(k));
  return valid.length ? valid : [...ALL_AXIS_KEYS];
}

/**
 * What to write to profiles.active_axes: null when all seven are on
 * (so the column stays unset), otherwise the enabled subset in canonical order.
 */
export function axesToPersist(active: AxisKey[]): string[] | null {
  const subset = ALL_AXIS_KEYS.filter((k) => active.includes(k));
  return subset.length === ALL_AXIS_KEYS.length ? null : subset;
}
