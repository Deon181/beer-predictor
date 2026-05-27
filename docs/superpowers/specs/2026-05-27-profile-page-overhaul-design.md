# Profile Page Overhaul — Design Spec

**Date:** 2026-05-27
**Status:** Approved

## Summary

Complete rewrite of the profile page (`app/profile/page.tsx`) to replace the flat ratings table with curated editorial sections: display name, radar chart, top 5 favourites, worst 5, next 5 recommendations, and sign out.

## Page Structure (top to bottom)

### 1. Masthead
Existing component, unchanged.

### 2. Header
Keep the existing broadsheet header: "No. 02 — Reader's Card" / "Your profile."

### 3. Display Name
Inline edit row with save button. Keep existing behavior and styling (`.profile-name-section`, `.prof-row`, `.prof-field`, `.prof-input`, `.prof-save`, `.prof-status`).

### 4. Radar Chart — "Your taste profile"
The 7-axis radar showing the user's derived taste preferences. Uses the existing `RadarChart` component. Caption: "Fig. III · Your taste profile". When no personalized profile exists (not enough 4+ ratings), show the info hint: "Rate beers 4+ to see your profile".

### 5. Top 5 Favourites — "The Best Pours"
The 5 highest-rated beers from the user's ratings, sorted by rating descending. Ties broken alphabetically by name. Each entry displays:
- Rank (№ 01–05)
- Beer name
- Brewery (italic)
- Style + star rating on the same line

Uses a new `.profile-list` class for compact broadsheet-styled rows with bottom hairline separators. Section header styled as a `section-label` mono heading with a hairline rule.

### 6. Worst 5 — "The Drains"
The 5 lowest-rated beers from the user's ratings, sorted by rating ascending. Ties broken alphabetically by name. Same card format as Top 5.

If the user has fewer than 5 ratings, show as many as available for both top and worst lists. If the user has no ratings, show an italic message: "Rate a few beers to populate your lists."

The top and worst lists may overlap when the user has 10 or fewer ratings — that's fine.

### 7. Next 5 Recommendations — "Up Next"
5 beers the user hasn't rated yet, scored against their personalized taste profile via `recommend()` with topK=5. Each entry displays:
- Rank (№ 01–05)
- Beer name
- Brewery (italic)
- Style + match score

Only appears when the user has a personalized profile (i.e., `personalizedDefaults()` returns non-null). When hidden, no placeholder is shown.

### 8. Sign Out
Secondary button at the bottom. Keep existing behavior (form + `signOut()`). Existing styling (`.profile-signout-section`, `.ink-btn--secondary`).

### 9. Colophon
Existing footer, unchanged.

## What Gets Removed

- The full chronological ratings table ("Your ledger") and its `<table>` markup
- The `handleRemoveRating` callback and per-row "Remove" buttons
- The `sortedRatings` variable (replaced by `topRated` and `worstRated`)

## Data Flow

- **Catalog:** Static JSON via `loadCatalog()` (existing)
- **Ratings:** Supabase `user_beers` via `supabase.from("user_beers").select(...)` (existing)
- **Personalized profile:** `personalizedDefaults(ratings, catalog)` (existing)
- **Top 5:** `ratings` sorted by `rating` descending, take first 5, resolved against catalog by `beer_id`
- **Worst 5:** `ratings` sorted by `rating` ascending, take first 5, resolved against catalog by `beer_id`
- **Next 5:** Filter `catalog` to exclude beer_ids present in `ratings`, then call `recommend(unratedBeers, personalizedProfile, 5)`. Only computed when personalized profile exists.

## Files Changed

- **Modify:** `app/profile/page.tsx` — rewrite page content with curated sections
- **Modify:** `app/globals.css` — add `.profile-list` styles for the compact beer list rows

## New CSS Classes

### `.profile-list`
Container for each beer list section.

### `.profile-list__item`
Individual beer row: flex layout, bottom hairline border, padding for readability.

### `.profile-list__rank`
Rank number (№ 01): display font, copper color, matching the LedgerCard rank style.

### `.profile-list__info`
Flex column holding name, brewery, and meta line.

### `.profile-list__name`
Beer name: serif font, 1.05rem, semibold.

### `.profile-list__brewery`
Brewery: serif italic, ink-soft color.

### `.profile-list__meta`
Style + rating/score: mono font, small uppercase, ink-soft.

### `.profile-list__empty`
Empty state message: serif italic, ink-soft.
