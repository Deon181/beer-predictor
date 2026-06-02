import { describe, it, expect } from "vitest";
import {
  AXES,
  ALL_AXIS_KEYS,
  normalizeActiveAxes,
  axesToPersist,
} from "./axes";

describe("axes definitions", () => {
  it("defines the seven axes with profile keys and beer columns", () => {
    expect(AXES).toHaveLength(7);
    expect(ALL_AXIS_KEYS).toEqual([
      "bitterness",
      "sweetness",
      "maltiness",
      "hoppiness",
      "body",
      "sourness",
      "abv_preference",
    ]);
    const strength = AXES.find((a) => a.key === "abv_preference");
    expect(strength?.column).toBe("abv_normalized");
  });
});

describe("normalizeActiveAxes", () => {
  it("treats null, empty, and all-invalid as all seven", () => {
    expect(normalizeActiveAxes(null)).toEqual(ALL_AXIS_KEYS);
    expect(normalizeActiveAxes([])).toEqual(ALL_AXIS_KEYS);
    expect(normalizeActiveAxes(["nonsense"])).toEqual(ALL_AXIS_KEYS);
  });

  it("keeps only valid saved keys, in canonical order", () => {
    expect(normalizeActiveAxes(["sweetness", "bitterness", "bogus"])).toEqual([
      "bitterness",
      "sweetness",
    ]);
  });
});

describe("axesToPersist", () => {
  it("returns null when all seven are active", () => {
    expect(axesToPersist(ALL_AXIS_KEYS)).toBeNull();
  });

  it("returns the enabled subset in canonical order otherwise", () => {
    expect(axesToPersist(["sweetness", "bitterness"])).toEqual([
      "bitterness",
      "sweetness",
    ]);
  });
});
