# Customizable Taste Attributes — Design

**Date:** 2026-06-02
**Status:** Approved (design phase)

## Problem

The recommender scores every beer on a fixed seven-axis taste vector —
bitterness, sweetness, maltiness, hoppiness, body, sourness, and strength
(ABV) — all weighted equally. Some drinkers don't care about some of these
axes. A user who is indifferent to sourness still has sourness pulling on
their match score, which is noise to them.

We want signed-in users to choose **which attributes matter to them** and have
the recommender, sliders, and charts honor that choice. The default stays all
seven, so nothing changes for anyone who doesn't opt in.

## Decisions (from brainstorming)

- **On/off, not weighting.** A disabled axis is excluded entirely from the
  distance calculation, the sidebar, and the radar charts. (We may add true
  importance weighting later; the data model leaves room for it, but it is out
  of scope now.)
- **Signed-in users only.** The configuration lives on the account-gated
  `/profile` page and persists to Supabase. Signed-out visitors always see the
  full seven axes.
- **Approach A:** store the active set as a list of enabled axis keys on the
  user's profile and thread it through `recommend()` / `explain()`. The
  exclusion is real — a disabled axis cannot influence the score.

## Architecture

### 1. Data model & persistence

Add one column to the existing Supabase `profiles` table:

```sql
alter table profiles
  add column active_axes text[];
```

- Values are the canonical axis keys: `bitterness`, `sweetness`, `maltiness`,
  `hoppiness`, `body`, `sourness`, `abv_preference`.
- **`NULL` means "all seven"** — today's behavior. We never write all seven
  explicitly; when a user has every axis on we clear the column to `NULL`. This
  needs no backfill (existing rows are already `NULL`) and makes "reset to
  default" a single `NULL` write.
- The repo drives Supabase from the browser client and has no migration
  runner, so this SQL is run once in the Supabase dashboard. The SQL is part of
  the implementation plan's deliverables.

### 2. Shared axis definitions

The seven axes are currently redefined in four places: `SLIDERS`
(`components/TastingSidebar.tsx`), `RADAR_AXES` (`app/page.tsx` and
`app/profile/page.tsx`), and `TASTE_COLS` / `SLIDER_TO_COLUMN`
(`lib/recommender.ts`). The feature needs a single shared notion of "all axes"
and "which are active," so these collapse into one module.

**New `lib/axes.ts`** exports the canonical list. Each entry has:

- `key` — the `TasteProfile` key (e.g. `abv_preference`)
- `label` — display label (e.g. `Strength`)
- `help` — the help/description string
- `column` — the beer data column used for distance (e.g. `abv_normalized`)

The sidebar, both radar configs, and the recommender import from here. This is
a targeted consolidation in direct service of the feature, not unrelated
refactoring.

### 3. Recommender changes (`lib/recommender.ts`)

- `recommend(catalog, profile, topK, filters, activeAxes?)` — the squared-diff
  sum runs **only over the active axes' columns**. `activeAxes` undefined or
  empty falls back to all seven (safety net; see edge cases).
- `explain(beer, profile, activeAxes?)` — ranks and reports **only active
  axes**, so the "why it matched" copy never cites an attribute the user turned
  off.
- `TASTE_COLS` / `SLIDER_TO_COLUMN` are sourced from `lib/axes.ts` so there is
  one definition of the column mapping.

### 4. Configuration UI (`app/profile/page.tsx`)

A new section on the profile page, in the broadsheet voice, titled
**"What you measure"** (placed near the taste radar). It contains:

- The seven axes as labeled toggles with their help text, sourced from
  `lib/axes.ts`. Checked = active.
- A **Save** button with an inline status line, mirroring the existing display-
  name edit pattern (`nameStatus`). Saving writes the enabled keys to
  `profiles.active_axes`, or clears the column to `NULL` when all seven are on.
- **Guard: at least one axis must stay enabled.** If the user unchecks the last
  one, Save is blocked with an inline note ("Keep at least one attribute").

### 5. Home page wiring (`app/page.tsx`, `components/TastingSidebar.tsx`)

The home page already loads the user's ratings on sign-in; it loads
`active_axes` in the same effect and threads it through:

- **Sidebar** renders only the active sliders — it maps over the active subset
  of `lib/axes.ts` instead of the static `SLIDERS`. Disabled axes do not
  appear.
- **`recommend()` and `explain()`** receive the active set, so matching and
  explanations honor it.
- **Both radar charts** ("Your profile" and "You vs. top 3") build their axis
  list from the active set, dropping disabled spokes.
- Signed-out visitors and signed-in users who have not customized → all seven,
  exactly as today.

`personalizedDefaults` (seeded from ratings) still computes values for all
seven axes; the disabled ones are simply never used for matching or display.
No change needed there.

## Data flow

```
profiles.active_axes (Supabase)
        │  load on sign-in (NULL → all 7)
        ▼
   app/page.tsx state: activeAxes
        ├──► TastingSidebar  (render active sliders only)
        ├──► recommend(..., activeAxes)  (distance over active axes)
        ├──► explain(..., activeAxes)    (cite active axes only)
        └──► radar data builders         (active spokes only)

app/profile/page.tsx "What you measure"
        └──► save: write enabled keys, or NULL when all 7 → profiles.active_axes
```

## Edge cases

- **Default (NULL):** new, signed-out, or never-customized users get all seven —
  unchanged experience.
- **Reset to all seven:** clears the column to `NULL`.
- **Empty / zero axes:** the UI guard requires ≥1; the recommender's
  empty-or-undefined → all-7 fallback is a second safety net so matching never
  runs on zero axes.
- **Sparse radar:** Recharts renders fine down to a single spoke; it just looks
  sparse. Acceptable, and the ≥1 guard prevents the degenerate case.

## Verification

- **Unit check on `recommend()`:** a beer that differs from the profile *only*
  on a disabled axis ranks identically to a perfect match — proving the
  disabled axis is genuinely ignored. A second check confirms `explain()` never
  names a disabled axis.
- **Manual, signed-in:** toggle axes on `/profile`, save, reload, and confirm
  the choice persists; confirm the home sidebar shows only active sliders, the
  radars drop disabled spokes, and the ledger re-ranks.
- **Test tooling note:** the repo has no test runner configured. The
  implementation plan will either add a minimal runner (e.g. `vitest`) for the
  recommender check or fall back to a small Node smoke script — to be decided at
  planning time based on user preference.

## Out of scope

- True importance weighting (low/medium/high). The data model can grow into it
  later, but it is not built now.
- Customization for signed-out users / localStorage persistence.
- Changing the distance metric or match-score formula.
