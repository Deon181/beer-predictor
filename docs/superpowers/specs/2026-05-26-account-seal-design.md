# Account Seal — Masthead Top-Right Redesign

## Goal

Replace the plain dot-separated link strip in the top-right of the masthead (e.g. `Name · Profile · Sign out`) with a framed "account seal" that fits the broadsheet aesthetic. Position is unchanged; only the visual treatment changes.

## Visual Treatment

A boxed "stamp" with four stacked elements:

```
┌────────────────────┐
│ ACCOUNT            │   ← eyebrow: mono, uppercase, tracked, --copper-dim
│ D. van Heerden     │   ← name:    serif italic (Newsreader), --ink
│ ─────────────────  │   ← rule:    1px var(--hairline)
│ PROFILE · SIGN OUT │   ← actions: mono, uppercase, tracked, --ink-soft
└────────────────────┘   ← frame:   1px solid var(--ink), small copper-soft drop shadow
```

Signed-out variant uses the same frame with eyebrow `NEWSSTAND`, italic body `Pick up a copy`, and actions `SIGN IN · SIGN UP`.

## Layout

- Stays as the third child of `.masthead .vol`.
- Mobile (base): renders in normal flow, stacks below the vol/tagline lines. Constrain `max-width` so the seal doesn't span the page.
- Desktop (`@media (min-width: 1100px)`): the existing `.vol { flex-direction: row; justify-content: space-between }` rule already pushes the seal to the right edge — no extra positioning needed.

## Styling Details

- Border: `1px solid var(--ink)`, square corners (consistent with `.ink-btn`, `.Select-menu-outer`, etc.)
- Drop shadow: `3px 3px 0 var(--copper-soft)` — same "stamp" vibe as `.ink-btn:hover`'s `4px 4px 0 var(--copper)`
- Padding: ~`0.55rem 0.85rem`
- Hairline rule between name and actions: `1px solid var(--hairline)`
- Anchors and the `Sign out` submit button receive a shared action class (e.g. `.account-seal__action`) that strips button defaults and matches them visually — same font, size, color, and underline-on-hover behavior — so they sit inline as a single `PROFILE · SIGN OUT` row. (The current code applies a `linkish` class to the button that is not actually defined in the stylesheet, so the button currently renders with default browser button chrome. This redesign fixes that incidentally.)

## Files Affected

- `dashboard/components/masthead.py` — rewrite `_signed_in_links` / `_anon_links` to produce the four-element structure (eyebrow / name / rule / actions) with appropriate class names.
- `dashboard/assets/style.css` — add a `.account-seal` block. Mobile-first styles in the base section; no `@media (max-width: ...)` queries (per the project's CSS structural rule at the top of `style.css`).

## Out of Scope

- Auth flow changes — `_fetch_display_name`, blueprint routes, and Supabase calls stay as-is.
- Mobile relocation (already discussed: position stays the same on all breakpoints).
- Avatar / monogram / dropdown affordances.

## Test Considerations

The structural CSS tests in `tests/test_dashboard_css.py` forbid `@media (max-width: ...)` queries. New styles must use mobile-first defaults and override only at `@media (min-width: 1100px)` if anything desktop-specific is needed. The visual change should not require new desktop overrides; the existing flex direction on `.vol` handles desktop placement.
