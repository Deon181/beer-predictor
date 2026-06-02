import { describe, it, expect } from "vitest";
import { recommend } from "./recommender";
import type { Beer, TasteProfile } from "./types";
import type { AxisKey } from "./axes";

function makeBeer(over: Partial<Beer>): Beer {
  return {
    beer_id: "x",
    name: "X",
    brewery: "B",
    style: "Test Ale",
    country: "C",
    abv: 5,
    ibu: 0,
    srm: 0,
    bitterness: 5,
    sweetness: 5,
    maltiness: 5,
    hoppiness: 5,
    body: 5,
    sourness: 5,
    abv_normalized: 5,
    ...over,
  };
}

const profile: TasteProfile = {
  bitterness: 8,
  sweetness: 2,
  maltiness: 5,
  hoppiness: 5,
  body: 5,
  sourness: 2,
  abv_preference: 5,
};

describe("recommend with active axes", () => {
  it("ignores a disabled axis when scoring", () => {
    // Perfect on the two active axes, wildly off on the disabled sourness axis.
    const beer = makeBeer({ bitterness: 8, sweetness: 2, sourness: 10 });
    const active: AxisKey[] = ["bitterness", "sweetness"];
    const [top] = recommend([beer], profile, 1, undefined, active);
    expect(top.distance).toBeCloseTo(0, 5);
    expect(top.match_score).toBeCloseTo(100, 5);
  });

  it("counts that same axis when it is active (default = all seven)", () => {
    const beer = makeBeer({ bitterness: 8, sweetness: 2, sourness: 10 });
    const [top] = recommend([beer], profile, 1);
    expect(top.distance).toBeGreaterThan(0);
  });
});
