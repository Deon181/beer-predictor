# Ledger Search — Design Spec

**Date:** 2026-05-27
**Status:** Approved

## Summary

Add a full-catalog text search bar above the Ledger on the home page. Users can look up any beer by name or brewery, with results displayed as standard LedgerCards scored against the current taste profile.

## Behavior

- **Empty query:** Normal recommendation mode (current behavior). The Ledger shows top-K beers ranked by taste-profile match.
- **Non-empty query:** Search mode. The catalog is filtered by case-insensitive substring match on `name` and `brewery` fields. Matched beers are scored through the existing `recommend()` function to compute match scores and explanations. The `topK` limit does not apply — all matching beers are shown. Sidebar filters (style, country, ABV) still apply on top of the search.
- **Clear:** A "x" button on the search input resets the query and returns to recommendation mode.
- **Debounce:** None needed. The catalog is ~588 beers in memory; substring filtering and scoring is fast enough to run on every keystroke.

## UI Placement

The search input sits between the charts row and the Ledger section header, inside `<main className="feature">`. It is a single text input styled in the broadsheet aesthetic.

## Styling

- Serif font input (`var(--font-serif)`), bottom-border only, no background
- Copper accent on focus (`border-bottom-color: var(--color-copper)`)
- Mono-font placeholder text: "Search by name or brewery..."
- Clear button styled as a small text button in `var(--font-mono)`
- Class name: `.ledger-search` for the wrapper, standard input styling consistent with `.auth-field input` and `.prof-input input`

## Component Changes

### `app/page.tsx`

1. Add `searchQuery` string state (default: `""`)
2. Compute search results in a `useMemo`:
   - If `searchQuery` is empty, use existing `recommendations` (unchanged)
   - If non-empty, filter `catalog` to beers where `name` or `brewery` includes the lowercased query, then pass filtered set through `recommend()` with `topK` set to the filtered length (show all matches)
3. Add a search input element between the charts `<div>` and the `<Ledger>` component
4. Pass the computed results (either recommendations or search results) to `<Ledger>`

### `app/globals.css`

Add `.ledger-search` styles:
- Wrapper with top margin and bottom margin to separate from charts and ledger
- Input styled to match existing form inputs (bottom-border, serif font, copper focus)
- Clear button positioned inline

### No other files change

`Ledger.tsx`, `LedgerCard.tsx`, `recommender.ts`, and `types.ts` remain unchanged. The search input and filtering logic live entirely in `page.tsx`.

## Edge Cases

- **No matches:** The Ledger renders empty (no cards). The existing `<Ledger>` component handles an empty array gracefully.
- **Single character queries:** Allowed — substring match will return many results but scoring keeps them useful.
- **Special characters in query:** Substring match handles this naturally; no regex involved.
