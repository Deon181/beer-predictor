-- Adds the per-user active taste-axis selection.
-- NULL means "all seven axes" (the default); a non-null array lists the
-- enabled axis keys: bitterness, sweetness, maltiness, hoppiness, body,
-- sourness, abv_preference.
alter table public.profiles
  add column if not exists active_axes text[];
