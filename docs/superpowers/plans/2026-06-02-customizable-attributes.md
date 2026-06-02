# Customizable Taste Attributes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let signed-in users choose which taste attributes matter to them, so the recommender, sliders, and radar charts only consider their chosen axes.

**Architecture:** A canonical axis list (`lib/axes.ts`) becomes the single source of truth for the seven taste axes. The recommender and `explain()` gain an optional `activeAxes` argument and score only over those axes. The active set persists as a `text[]` column on the Supabase `profiles` table (`NULL` = all seven). The `/profile` page gets a toggle UI; the home page loads the set and threads it into the sidebar, recommender, and charts.

**Tech Stack:** Next.js 15 (App Router, client components), React 19, TypeScript, Supabase JS client, Recharts, Tailwind v4. Tests via Vitest (added in Task 1).

---

## File structure

| File | Responsibility | Action |
| --- | --- | --- |
| `vitest.config.ts` | Vitest config (node env) | Create |
| `package.json` | Add `vitest` devDep + `test` script | Modify |
| `lib/axes.ts` | Canonical axis list + active-set helpers | Create |
| `lib/axes.test.ts` | Unit tests for axes helpers | Create |
| `lib/recommender.ts` | Source axes from `lib/axes.ts`; add `activeAxes` to `recommend()` and `explain()` | Modify |
| `lib/recommender.test.ts` | Unit tests for active-axis scoring/explain | Create |
| `db/2026-06-02_add_active_axes.sql` | Migration SQL (run in Supabase dashboard) | Create |
| `app/profile/page.tsx` | "What you measure" toggle UI + save | Modify |
| `app/page.tsx` | Load `active_axes`; thread into sidebar/recommend/explain/radars | Modify |
| `components/TastingSidebar.tsx` | Render only active sliders | Modify |
| `app/globals.css` | Styles for the axis toggle grid | Modify |

---

## Task 1: Add Vitest tooling

**Files:**
- Create: `vitest.config.ts`
- Modify: `package.json`

- [ ] **Step 1: Add vitest devDependency**

Run:
```bash
npm install -D vitest@^2
```
Expected: `vitest` appears under `devDependencies` in `package.json`.

- [ ] **Step 2: Add the test script**

In `package.json`, add a `test` entry to the `scripts` object so it reads:

```json
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run"
  },
```

- [ ] **Step 3: Create the vitest config**

Create `vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
  },
});
```

- [ ] **Step 4: Add a throwaway smoke test to prove the runner works**

Create `lib/smoke.test.ts`:

```ts
import { describe, it, expect } from "vitest";

describe("vitest runner", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 5: Run the test suite**

Run: `npm test`
Expected: PASS — 1 passed (`lib/smoke.test.ts`).

- [ ] **Step 6: Remove the smoke test and commit**

```bash
rm lib/smoke.test.ts
git add package.json package-lock.json vitest.config.ts
git commit -m "chore: add vitest test runner"
```

---

## Task 2: Canonical axis list + active-set helpers

**Files:**
- Create: `lib/axes.ts`
- Test: `lib/axes.test.ts`

- [ ] **Step 1: Write the failing test**

Create `lib/axes.test.ts`:

```ts
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test`
Expected: FAIL — cannot resolve `./axes` / exports not found.

- [ ] **Step 3: Create `lib/axes.ts`**

```ts
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test`
Expected: PASS — all `lib/axes.test.ts` cases green.

- [ ] **Step 5: Commit**

```bash
git add lib/axes.ts lib/axes.test.ts
git commit -m "feat: add canonical axis list and active-set helpers"
```

---

## Task 3: Thread `activeAxes` through `recommend()`

**Files:**
- Modify: `lib/recommender.ts`
- Test: `lib/recommender.test.ts`

- [ ] **Step 1: Write the failing test**

Create `lib/recommender.test.ts`:

```ts
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test`
Expected: FAIL — `recommend` ignores the 5th argument, so the first case has a non-zero distance (sourness counted).

- [ ] **Step 3: Rewrite `lib/recommender.ts`**

Replace the entire contents of `lib/recommender.ts` with:

```ts
import type { Beer, Filters, Recommendation, TasteProfile } from "./types";
import { AXES, normalizeActiveAxes, type AxisKey } from "./axes";

/** Beer columns used for the taste vector, in canonical order. */
export const TASTE_COLS = AXES.map((a) => a.column);

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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test`
Expected: PASS — both `recommend` cases green; `lib/axes.test.ts` still green.

- [ ] **Step 5: Verify the rest of the app still type-checks**

Run: `npx tsc --noEmit`
Expected: No errors. (`personalization.ts` imports `TASTE_COLS` from `recommender.ts`, which is still exported.)

- [ ] **Step 6: Commit**

```bash
git add lib/recommender.ts lib/recommender.test.ts
git commit -m "feat: score recommendations over only the active taste axes"
```

---

## Task 4: Restrict `explain()` to active axes (test)

**Files:**
- Test: `lib/recommender.test.ts` (append)

The implementation already landed in Task 3; this task locks the behavior with a test.

- [ ] **Step 1: Import `explain` and append the test**

First, change the top import line of `lib/recommender.test.ts` from:

```ts
import { recommend } from "./recommender";
```

to:

```ts
import { recommend, explain } from "./recommender";
```

Then add to the bottom of `lib/recommender.test.ts`:

```ts
describe("explain with active axes", () => {
  it("never names a disabled axis", () => {
    const beer = makeBeer({ bitterness: 8, sourness: 10 });
    const text = explain(beer, profile, ["bitterness"]);
    expect(text.toLowerCase()).not.toContain("sour");
    expect(text.toLowerCase()).not.toContain("abv");
  });

  it("can cite an axis when it is active", () => {
    const beer = makeBeer({ bitterness: 8, sourness: 10 });
    const text = explain(beer, profile, ["bitterness", "sourness"]);
    expect(text.toLowerCase()).toContain("sour");
  });
});
```

> Note: `explain` is already imported once at the top of the file from Task 3's test scaffolding only if you added it. If the top of the file imports `{ recommend }` alone, change that line to `import { recommend, explain } from "./recommender";` and delete the duplicate `import { explain }` line above — a module may be imported only once.

- [ ] **Step 2: Run the test**

Run: `npm test`
Expected: PASS — both new `explain` cases green.

- [ ] **Step 3: Commit**

```bash
git add lib/recommender.test.ts
git commit -m "test: explain() honors the active axis set"
```

---

## Task 5: Supabase migration for `active_axes`

**Files:**
- Create: `db/2026-06-02_add_active_axes.sql`

This is a manual deploy step — there is no migration runner in the repo. The SQL is committed for the record and run once in the Supabase SQL editor.

- [ ] **Step 1: Create the SQL file**

Create `db/2026-06-02_add_active_axes.sql`:

```sql
-- Adds the per-user active taste-axis selection.
-- NULL means "all seven axes" (the default); a non-null array lists the
-- enabled axis keys: bitterness, sweetness, maltiness, hoppiness, body,
-- sourness, abv_preference.
alter table public.profiles
  add column if not exists active_axes text[];
```

- [ ] **Step 2: Apply it in Supabase**

Open the Supabase project → SQL Editor → paste the contents of `db/2026-06-02_add_active_axes.sql` → Run.
Expected: "Success. No rows returned." Verify under Table Editor → `profiles` that an `active_axes` column of type `text[]` now exists.

> The existing RLS policy that lets a user `update` their own `profiles` row already covers this column — no policy change needed. If a separate column-level grant exists, confirm `active_axes` is writable by the row owner.

- [ ] **Step 3: Commit the SQL**

```bash
git add db/2026-06-02_add_active_axes.sql
git commit -m "feat: migration adding profiles.active_axes"
```

---

## Task 6: "What you measure" toggle UI on the profile page

**Files:**
- Modify: `app/profile/page.tsx`
- Modify: `app/globals.css`

- [ ] **Step 1: Add imports and state**

In `app/profile/page.tsx`, add to the existing imports near the top:

```tsx
import { AXES, ALL_AXIS_KEYS, normalizeActiveAxes, axesToPersist, type AxisKey } from "@/lib/axes";
```

Inside `ProfilePage`, alongside the other `useState` calls, add:

```tsx
  const [activeAxes, setActiveAxes] = useState<AxisKey[]>(ALL_AXIS_KEYS);
  const [axesStatus, setAxesStatus] = useState("");
```

- [ ] **Step 2: Load the saved set**

In the `useEffect` that fetches the profile, change the `profiles` select to include `active_axes`, and set state from it. The Promise.all block becomes:

```tsx
    Promise.all([
      supabase.from("profiles").select("display_name, active_axes").eq("id", uid).single(),
      supabase.from("user_beers").select("beer_id, rating, rated_at"),
    ]).then(([profRes, ratingsRes]) => {
      if (profRes.data) {
        setDisplayName(profRes.data.display_name || "");
        setActiveAxes(normalizeActiveAxes(profRes.data.active_axes));
      }
      if (ratingsRes.data) setRatings(ratingsRes.data as UserRating[]);
      setLoading(false);
    });
```

- [ ] **Step 3: Add the toggle + save handlers**

Add these `useCallback`s next to `handleSaveName`:

```tsx
  const toggleAxis = useCallback((key: AxisKey) => {
    setActiveAxes((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
    setAxesStatus("");
  }, []);

  const handleSaveAxes = useCallback(async () => {
    if (activeAxes.length < 1) {
      setAxesStatus("Keep at least one attribute.");
      return;
    }
    if (!user || !supabase) {
      setAxesStatus("Account required.");
      return;
    }
    const { error } = await supabase
      .from("profiles")
      .update({ active_axes: axesToPersist(activeAxes) })
      .eq("id", user.id);
    setAxesStatus(error ? `Save failed: ${error.message}` : "Saved.");
  }, [activeAxes, user, supabase]);
```

- [ ] **Step 4: Add the section markup**

In the returned JSX, immediately after the taste-profile radar `</section>` (the one captioned "Fig. III" / "Your taste profile"), insert:

```tsx
        <section className="chart-card" style={{ marginTop: "1.5rem" }}>
          <div className="chart-caption">
            <span>Fig. IV</span>
            <span>What you measure</span>
          </div>
          <p className="axes-intro">
            Choose which attributes shape your matches. Anything you switch off
            is ignored entirely — in the ledger, the sliders, and the charts.
          </p>
          <div className="axes-grid">
            {AXES.map((a) => {
              const on = activeAxes.includes(a.key);
              return (
                <label
                  key={a.key}
                  className={`axis-toggle${on ? " axis-toggle--on" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={on}
                    onChange={() => toggleAxis(a.key)}
                  />
                  <span className="axis-toggle__label">{a.label}</span>
                  <span className="axis-toggle__help">{a.help}</span>
                </label>
              );
            })}
          </div>
          <div className="axes-actions">
            <button className="ink-btn" onClick={handleSaveAxes}>
              Save attributes
            </button>
            {axesStatus && (
              <span className="profile-card__status">{axesStatus}</span>
            )}
          </div>
        </section>
```

- [ ] **Step 5: Add styles**

Append to the end of `app/globals.css`:

```css
/* ── Customizable attributes (profile) ───────────────────────── */
.axes-intro {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  color: var(--color-copper);
  margin: 0.75rem 0 1rem;
  line-height: 1.5;
}

.axes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.5rem;
}

.axis-toggle {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  column-gap: 0.6rem;
  align-items: center;
  padding: 0.6rem 0.75rem;
  border: 1px solid rgba(26, 20, 16, 0.18);
  border-radius: 2px;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.15s ease, border-color 0.15s ease;
}

.axis-toggle--on {
  opacity: 1;
  border-color: var(--color-copper);
}

.axis-toggle input {
  grid-row: 1 / 3;
  width: 1.05rem;
  height: 1.05rem;
  accent-color: var(--color-copper);
}

.axis-toggle__label {
  font-family: var(--font-serif, serif);
  font-weight: 600;
  font-size: 0.95rem;
}

.axis-toggle__help {
  grid-column: 2;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--color-copper);
  line-height: 1.35;
}

.axes-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}
```

> If `--font-serif` is not a defined CSS variable in this project, the `serif` fallback applies — no breakage. Leave it as written.

- [ ] **Step 6: Verify type-check and build**

Run: `npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add app/profile/page.tsx app/globals.css
git commit -m "feat: add 'What you measure' attribute toggles to profile"
```

---

## Task 7: Thread the active set through the home page

**Files:**
- Modify: `app/page.tsx`
- Modify: `components/TastingSidebar.tsx`

- [ ] **Step 1: Add `activeAxes` prop to the sidebar**

In `components/TastingSidebar.tsx`, replace the local `SliderDef`/`SLIDERS` block and the props interface so the sidebar derives sliders from the shared axes filtered by the active set.

Change the imports at the top to:

```tsx
import { useState } from "react";
import type { Filters, TasteProfile } from "@/lib/types";
import { AXES, type AxisKey } from "@/lib/axes";
import { SearchableMultiSelect } from "@/components/SearchableMultiSelect";
```

Delete the `interface SliderDef { ... }` and the `const SLIDERS: SliderDef[] = [ ... ];` array entirely.

Add `activeAxes` to the props interface:

```tsx
interface TastingSidebarProps {
  profile: TasteProfile;
  onProfileChange: (profile: TasteProfile) => void;
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  topK: number;
  onTopKChange: (k: number) => void;
  styles: string[];
  countries: string[];
  onReset: () => void;
  activeAxes: AxisKey[];
}
```

Destructure `activeAxes` in the component signature (add it to the existing destructured params):

```tsx
export function TastingSidebar({
  profile,
  onProfileChange,
  filters,
  onFiltersChange,
  topK,
  onTopKChange,
  styles,
  countries,
  onReset,
  activeAxes,
}: TastingSidebarProps) {
```

- [ ] **Step 2: Render only the active sliders**

In `TastingSidebar.tsx`, replace the `{SLIDERS.map((s) => ( ... ))}` block inside `.slider-group` with a filtered map over `AXES`:

```tsx
        <div className="slider-group">
          {AXES.filter((a) => activeAxes.includes(a.key)).map((s) => (
            <label key={s.key} className="slider-label">
              <span className="slider-label__name">
                {s.label}
                <span className="slider-label__value">
                  {profile[s.key].toFixed(1)}
                </span>
              </span>
              <input
                type="range"
                min={0}
                max={10}
                step={0.5}
                value={profile[s.key]}
                onChange={(e) => handleSlider(s.key, parseFloat(e.target.value))}
                className="slider"
                title={s.help}
              />
              <span className="slider-label__help">{s.help}</span>
            </label>
          ))}
        </div>
```

(`handleSlider` already accepts `key: keyof TasteProfile`, and `AxisKey` is `keyof TasteProfile`, so no change to that handler.)

- [ ] **Step 3: Load `active_axes` on the home page**

In `app/page.tsx`, add to the imports:

```tsx
import { AXES, ALL_AXIS_KEYS, normalizeActiveAxes, type AxisKey } from "@/lib/axes";
```

Add state alongside the others:

```tsx
  const [activeAxes, setActiveAxes] = useState<AxisKey[]>(ALL_AXIS_KEYS);
```

In the sign-in `useEffect` that loads `user_beers`, also load the profile's `active_axes`. Replace that effect body with:

```tsx
  useEffect(() => {
    if (!user || !supabase) return;

    supabase
      .from("user_beers")
      .select("beer_id, rating")
      .then(({ data }) => {
        if (data) {
          setRatings(new Map(data.map((r: UserRating) => [r.beer_id, r.rating])));
          const defaults = personalizedDefaults(data as UserRating[], catalog);
          if (defaults) setProfile(defaults);
        }
      });

    supabase
      .from("profiles")
      .select("active_axes")
      .eq("id", user.id)
      .single()
      .then(({ data }) => {
        if (data) setActiveAxes(normalizeActiveAxes(data.active_axes));
      });
  }, [user, supabase, catalog]);
```

> When the user signs out, `user` becomes falsy and this effect does not run; reset the active set on sign-out by adding `setActiveAxes(ALL_AXIS_KEYS);` to the top of the effect's early-return path is unnecessary because a signed-out home view still defaults to `ALL_AXIS_KEYS` from initial state. Leave as written.

- [ ] **Step 4: Pass the active set into recommend, explain, sidebar, and radars**

In `app/page.tsx`:

(a) Update the `recommendations` memo to pass `activeAxes`:

```tsx
  const recommendations = useMemo(
    () => (catalog.length ? recommend(catalog, profile, topK, filters, activeAxes) : []),
    [catalog, profile, topK, filters, activeAxes]
  );
```

(b) Update the `displayedResults` search branch to pass `activeAxes`:

```tsx
    return recommend(matched, profile, matched.length, filters, activeAxes);
```

and add `activeAxes` to that memo's dependency array.

(c) Restrict the radar axis list to active axes. Replace the `RADAR_AXES` constant usage in the two radar memos by filtering it. First, just below `RADAR_AXES`, the existing constant stays; in `profileRadarData` and `comparisonRadarData`, replace `RADAR_AXES.map(...)` with `RADAR_AXES.filter((a) => activeAxes.includes(a.key as AxisKey)).map(...)`. Concretely:

```tsx
  const profileRadarData = useMemo(
    () =>
      RADAR_AXES.filter((a) => activeAxes.includes(a.key as AxisKey)).map((a) => ({
        axis: a.label,
        You: profile[a.key as keyof TasteProfile],
      })),
    [profile, activeAxes]
  );

  const comparisonRadarData = useMemo(() => {
    const top3 = recommendations.slice(0, 3);
    return RADAR_AXES.filter((a) => activeAxes.includes(a.key as AxisKey)).map((a) => {
      const col = TASTE_COL_FOR_AXIS[a.key];
      const point: Record<string, number | string> = {
        axis: a.label,
        You: profile[a.key as keyof TasteProfile],
      };
      top3.forEach((beer) => {
        point[beer.name.slice(0, 28)] = beer[col as keyof Beer] as number;
      });
      return point;
    });
  }, [profile, recommendations, activeAxes]);
```

(d) Pass `activeAxes` to the sidebar in the JSX:

```tsx
        <TastingSidebar
          profile={profile}
          onProfileChange={setProfile}
          filters={filters}
          onFiltersChange={setFilters}
          topK={topK}
          onTopKChange={setTopK}
          styles={styles}
          countries={countries}
          onReset={handleReset}
          activeAxes={activeAxes}
        />
```

- [ ] **Step 5: Pass `activeAxes` into the Ledger's explanations**

The `Ledger` component calls `explain(beer, profile)` per row. Open `components/Ledger.tsx` and `components/LedgerCard.tsx` to find the `explain(...)` call. Add `activeAxes` as the third argument and thread an `activeAxes: AxisKey[]` prop down from `app/page.tsx`.

In `app/page.tsx`, add `activeAxes={activeAxes}` to the `<Ledger ... />` JSX.

In `components/Ledger.tsx`:
- import the type: `import type { AxisKey } from "@/lib/axes";`
- add `activeAxes: AxisKey[];` to its props interface and destructure it.
- forward it to wherever `explain` is called or to `LedgerCard`.

If `explain` is called inside `LedgerCard.tsx`, repeat the prop addition there and change the call to `explain(beer, profile, activeAxes)`. If `explain` is called directly in `Ledger.tsx`, change the call there instead.

> Verify the exact call site by reading both files before editing — the explanation may live in either component. The change is the same: pass the active set so the prose matches the active axes.

- [ ] **Step 6: Type-check**

Run: `npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 7: Run the unit tests**

Run: `npm test`
Expected: PASS — all `lib` tests still green.

- [ ] **Step 8: Commit**

```bash
git add app/page.tsx components/TastingSidebar.tsx components/Ledger.tsx components/LedgerCard.tsx
git commit -m "feat: honor active taste axes across sidebar, recommender, charts, and ledger"
```

---

## Task 8: End-to-end manual verification

**Files:** none (verification only)

- [ ] **Step 1: Start the dev server**

Run: `npm run dev`
Expected: Ready on http://localhost:3000.

- [ ] **Step 2: Verify the migration is applied**

Confirm Task 5 was run in Supabase (the `active_axes` column exists). Without it, the save in Step 4 will error.

- [ ] **Step 3: Signed-out baseline**

Load `/` while signed out. Confirm all seven sliders show and both radars have seven spokes (unchanged behavior).

- [ ] **Step 4: Customize and save**

Sign in → go to `/profile` → in "What you measure", switch off two axes (e.g. Sour and Strength) → click "Save attributes". Expected: status reads "Saved." Reload `/profile`; the two axes remain off (persistence confirmed).

- [ ] **Step 5: Confirm the home view honors it**

Go to `/`. Expected: only the five enabled sliders show; both radars show five spokes; the ledger re-ranks (a beer that only differed on a disabled axis now scores higher), and no ledger explanation mentions a disabled axis (no "sour", no "ABV").

- [ ] **Step 6: Confirm the guard**

On `/profile`, switch off every axis and click "Save attributes". Expected: status reads "Keep at least one attribute." and nothing is saved.

- [ ] **Step 7: Confirm reset to default**

On `/profile`, switch all seven back on and save. Expected: "Saved." In Supabase, `profiles.active_axes` for this user is `NULL` (all-seven persists as null).

- [ ] **Step 8: Final commit (if any tweaks were needed)**

```bash
git add -A
git commit -m "chore: verification tweaks for customizable attributes"
```

(Skip this commit if no changes were needed during verification.)
