# Supabase user profiles & beer ratings — design

**Date:** 2026-05-23
**Status:** Draft for review

## Goal

Add per-user accounts to the Beer Predictor so signed-in users can log
beers they've had (catalog beers only) with a 1–5 star rating
(half-stars allowed), and have those ratings seed the recommender's
slider defaults the next time they visit. The recommender experience
for anonymous visitors is unchanged.

## Decisions locked in during brainstorming

| Question | Decision |
|---|---|
| What do ratings do? | Personalize the recommender (not just journal). |
| Which beers can be rated? | Catalog only (`data/processed/beers.parquet`). |
| Rating scale? | 5-star with half-stars (0.5–5.0 in 0.5 steps). No free-text notes for v1. |
| Where does it run? | Localhost now; designed to deploy publicly later. |
| Auth method? | Email + password (confirm-email on). |
| Access model? | Open + optional sign-in. Anonymous use still works. |
| Profile fields? | Display name + auto-derived default sliders. No favorite styles, no avatar. |
| Personalization shape? | Sign-in seeds slider defaults from average taste vector of beers rated ≥4★. Recommender math itself is unchanged. |

## Architecture

The existing `dashboard/app.py` already exposes `server = app.server`
(the Flask app underneath Dash). We mount Supabase integration and auth
routes on the same Flask process — no new framework, no second service.

```
Flask app (dashboard/app.py: server = app.server)
├── Dash app  (Dash UI: /, /profile)
│       reads user from Flask session, calls supabase-py
└── Flask routes (auth)  (/auth/login, /auth/signup, /auth/logout,
                           /auth/forgot, /auth/reset, /auth/callback)

src/auth.py    — login/signup/session API (thin wrappers on supabase-py)
src/db.py      — supabase client factory (anon, or bound to a user JWT)
src/personalization.py — personalized_defaults()
                          │
                          ▼  HTTPS
                  Supabase project
                  • auth.users (managed)
                  • public.profiles
                  • public.user_beers
                  (RLS policies on both public tables)
```

**Key shape choices:**

- The catalog stays in `data/processed/beers.parquet`. It is static,
  version-controlled, deterministic, and putting it in Postgres adds a
  network hop without benefit. `user_beers` references catalog rows by
  a stable `beer_id` slug — integrity is enforced application-side.
- Session state lives in a signed Flask session cookie (itsdangerous).
  Three values: `access_token`, `refresh_token`, `user_id`. Cookie is
  `HttpOnly`, `SameSite=Lax`, `Secure=True` outside debug mode.
- Per-request user resolution goes through `src/db.py::user_client()`.
  Anonymous Dash callbacks just don't call it and never touch
  protected tables.
- `src/recommender.py` is **not** modified. Personalization is a
  separate function that returns a starting taste-profile dict; the
  recommender consumes the dict like any other.

## Database schema

### Catalog change (precedes the Supabase work)

Add a `beer_id` column to `data/processed/beers.parquet`. Format:
`{slug(brewery)}__{slug(name)}` — deterministic, stable across catalog
rebuilds, human-readable when debugging. Generated in
`scripts/build_catalog.py` with a uniqueness assertion. Tested in a new
`tests/test_build_catalog_slugs.py`.

### `public.profiles` — 1:1 with `auth.users`

```sql
CREATE TABLE public.profiles (
  id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL CHECK (char_length(display_name) BETWEEN 1 AND 50),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

We do **not** store `default_taste_profile`. It's computed on demand
from `user_beers` — single source of truth, no cache-invalidation
hazard, math is cheap for hundreds of ratings.

### `public.user_beers` — one row per (user, beer)

```sql
CREATE TABLE public.user_beers (
  id        BIGSERIAL PRIMARY KEY,
  user_id   UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  beer_id   TEXT NOT NULL,
  rating    NUMERIC(2,1) NOT NULL
             CHECK (rating IN (0.5,1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0)),
  rated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, beer_id)
);
CREATE INDEX user_beers_user_idx ON public.user_beers (user_id);
```

Re-rating a beer updates the existing row (`upsert` on
`(user_id, beer_id)`).

### Profile-create trigger (in `private` schema, per security checklist)

```sql
CREATE SCHEMA IF NOT EXISTS private;

CREATE FUNCTION private.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  INSERT INTO public.profiles (id, display_name)
  VALUES (NEW.id,
          COALESCE(NEW.raw_user_meta_data->>'display_name',
                   split_part(NEW.email, '@', 1)));
  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION private.handle_new_user();
```

`SECURITY DEFINER` is required to write into `public.profiles` from the
trigger context; placing it in `private.` (an unexposed schema) and
forcing `search_path = ''` follows the Supabase security guidance.

### Row-level security

```sql
ALTER TABLE public.profiles   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_beers ENABLE ROW LEVEL SECURITY;

-- profiles: read/update your own row. Insert is trigger-only.
CREATE POLICY profiles_select_own
  ON public.profiles FOR SELECT TO authenticated
  USING (id = auth.uid());

CREATE POLICY profiles_update_own
  ON public.profiles FOR UPDATE TO authenticated
  USING (id = auth.uid()) WITH CHECK (id = auth.uid());

-- user_beers: full CRUD on your own rows.
CREATE POLICY user_beers_select_own
  ON public.user_beers FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY user_beers_insert_own
  ON public.user_beers FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY user_beers_update_own
  ON public.user_beers FOR UPDATE TO authenticated
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

CREATE POLICY user_beers_delete_own
  ON public.user_beers FOR DELETE TO authenticated
  USING (user_id = auth.uid());
```

UPDATE policies are paired with SELECT — without it, updates silently
return 0 rows (Supabase security checklist item).

### Grants

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON public.profiles    TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_beers  TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.user_beers_id_seq   TO authenticated;
```

`anon` is granted nothing on these tables.

## Auth flows

Six Flask routes on a `/auth` blueprint. Templates are minimal Jinja
styled to match the broadsheet aesthetic. All server-side — no JS.

| Route | Method | Behavior |
|---|---|---|
| `/auth/signup` | GET, POST | Form: email, password, display_name. POST → `supabase.auth.sign_up()` with `data.display_name` in user metadata. Trigger creates the `profiles` row. If email-confirm is on, show "check your email." |
| `/auth/login` | GET, POST | Form: email, password. POST → `sign_in_with_password()`. Success → write tokens to Flask session, redirect to `/`. |
| `/auth/logout` | POST | `sign_out()` + clear session. Redirect `/`. |
| `/auth/forgot` | GET, POST | Form: email. POST → `reset_password_for_email(email, redirect_to=".../auth/callback?next=/auth/reset")`. Show "check your email." |
| `/auth/reset` | GET, POST | After callback, user is in a recovery session. POST → `update_user({"password": new})`. |
| `/auth/callback` | GET | Single PKCE handler for both confirm-email and password-reset links. Reads `?code=`, calls `exchange_code_for_session(code)`, writes tokens to Flask session, redirects to `next` (defaults to `/`). |

### Per-request user resolution

```python
def user_client() -> Client | None:
    """Return a Supabase client bound to the current user, or None if anon."""
    access = flask.session.get("access_token")
    refresh = flask.session.get("refresh_token")
    if not access or not refresh:
        return None
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.auth.set_session(access, refresh)
    s = client.auth.get_session()
    if s and s.access_token != access:
        flask.session["access_token"] = s.access_token
        flask.session["refresh_token"] = s.refresh_token
    return client
```

All RLS-protected reads/writes go through this. Anonymous code paths
simply don't call it.

### Supabase project configuration

- **Site URL:** `http://127.0.0.1:8050`
- **Additional Redirect URLs:** `http://127.0.0.1:8050/auth/callback`
  (add public equivalents when deploying)
- **Email provider:** enabled; "Confirm email" on
- **Email templates:** defaults for v1

### Security commitments

- `SECRET_KEY` and `SUPABASE_ANON_KEY` come from env, never checked in.
- `service_role` key is **not** used anywhere in the app.
- Authorization decisions use `auth.uid()` (the JWT `sub` claim) only.
  `user_metadata` (where `display_name` lives) is user-editable and
  unsafe for authorization — never referenced in RLS.
- Session cookie is `HttpOnly` so an XSS can't read the token.

## Dash UI changes

1. **Multi-page split via Dash Pages.** Move the current single-page
   layout into `dashboard/pages/recommender.py` (`/`). Add
   `dashboard/pages/profile.py` (`/profile`). Auth pages stay as Flask
   templates outside Dash.

2. **Masthead sign-in indicator.** Top-right of the existing masthead,
   in the monospace stamp style:
   - Anonymous: `Sign in · Sign up`
   - Signed in: `{display_name} · Profile · Sign out`
   Rendered by a layout *function* that reads Flask session per
   request (no first-paint flicker from callback-driven auth UI).

3. **Rating control on each beer row** (signed-in only). A dropdown
   `½ · 1 · 1½ · 2 · 2½ · 3 · 3½ · 4 · 4½ · 5` with an "unrated"
   default, plus a tiny "✓ rated" indicator if already rated. Anon
   users see the dropdowns disabled with a "sign in to rate" tooltip.
   A pattern-matched callback upserts to `user_beers` via
   `user_client()`. Dropdown chosen over custom half-star UI to avoid
   shipping a custom React component for v1.

4. **Personalized slider defaults on load.** `_sidebar()` calls
   `personalized_defaults()` and uses the result as initial slider
   `value=`. The Dash layout is a function, so this runs on every
   page load and reflects the latest ratings without a refresh.

5. **New `/profile` page** with three sections:
   - Editable `display_name` (Save button writes to `profiles`).
   - "Fig. III" radar showing current personalized defaults. If user
     has <1 rating ≥4, show an aside: "Rate a few beers to populate
     your profile."
   - Ledger of all rated beers, sortable, with Edit / Remove actions.

### Files added or changed

| File | Change |
|---|---|
| `dashboard/app.py` | Slim to bootstrap only; layout moves to pages. |
| `dashboard/pages/recommender.py` | Existing layout + callbacks, plus rating wiring. |
| `dashboard/pages/profile.py` | New. |
| `dashboard/auth_routes.py` | New Flask blueprint for auth routes. |
| `dashboard/templates/auth/*.html` | New Jinja templates (`login`, `signup`, `forgot`, `reset`, `check_email`). |
| `dashboard/components/masthead.py` | Existing masthead, reads Flask session for sign-in indicator. |
| `src/auth.py` | New: thin wrappers on `supabase-py` auth calls. |
| `src/db.py` | New: `anon_client()`, `user_client()`. |
| `src/personalization.py` | New: `personalized_defaults()`. |
| `scripts/build_catalog.py` | Add `beer_id` slug column, assert unique. |
| `pyproject.toml` | Add `supabase` and `python-dotenv`. |
| `.env.example` | New: placeholders for env vars. |

## Personalization logic

The entire personalization story is one function:
`src/personalization.py::personalized_defaults()`. The recommender is
not modified.

### Formula

```
For each user-rated beer where rating >= 4:
    weight = rating - 3            # 4★ → 1.0, 4.5★ → 1.5, 5★ → 2.0
    weighted_sum  += weight * taste_vector(beer)
    weight_total  += weight

If weight_total == 0:              # no ratings ≥4 yet
    return None                    # falls through to slider=5.0

default_taste_vector = weighted_sum / weight_total
Clip every axis to [0, 10].
Map taste_vector columns back to slider keys (abv_normalized → abv_preference).
Return as dict.
```

Rationale:

- **Weight = rating − 3** so 5★ counts twice as much as 4★. Threshold
  and weight derive from the same number — one tunable, not two.
- **Threshold at 4★** captures "actively likes" rather than "tolerates."
- **Averaging multiple liked beers** smooths over outliers (one weird
  sour they loved doesn't drag every recommendation toward sour).
- **No dislike-penalty.** Locked in during brainstorming as the
  simplest personalization option; sliders are still freely draggable
  so users can explore.

### Edge cases

| Case | Behavior |
|---|---|
| No ratings | Returns `None`; sliders default to 5.0 (today's behavior). |
| Ratings exist but none ≥4★ | Returns `None`; sliders default to 5.0. We deliberately do not fall back to ≥3★ — that would silently hide "haven't found anything I love yet" behind a misleading profile. |
| One 5★ rating | Defaults to that beer's exact taste vector. Mathematically correct; can feel like a strong jump. Acceptable for v1; revisit with neutral-blending if it feels harsh. |
| Catalog rebuilt and a rated `beer_id` no longer exists | Row in `user_beers` is orphaned; catalog join drops it silently. Log a count of orphans on startup for visibility. No deletion — a future rebuild may restore the slug. |
| User rates → reload | New defaults reflect the new rating immediately (layout function runs per request, no cache). |

### Where it's called

Exactly one place: `dashboard/pages/recommender.py::_sidebar()` at
layout-build time. The recommender's `recommend()` API consumes the
resulting dict like any other taste profile.

## Configuration and secrets

```
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=ey...           # publishable anon key
FLASK_SECRET_KEY=<random 64 hex>
```

Loaded by `python-dotenv` from `.env` (gitignored). `.env.example` is
checked in with placeholders. `service_role` key is intentionally
absent.

New deps in `pyproject.toml`: `supabase` (the Python SDK) and
`python-dotenv`. Versions chosen at implementation time, not pinned in
this spec.

## Migrations

Managed by the Supabase CLI:

```
supabase/
  config.toml
  migrations/
    20260523_initial.sql    # tables, trigger, RLS, grants
```

Per the supabase skill: iterate with MCP `execute_sql`, then commit a
clean migration via `supabase db pull --local`. Run `get_advisors`
after — fix any warnings before considering the migration done.

## Testing

### Pure-Python (run in existing CI)

- `tests/test_build_catalog_slugs.py` — slug uniqueness,
  determinism, format.
- `tests/test_personalization.py` — `personalized_defaults()` with
  fabricated rating data: empty input → `None`, ratings <4★ only →
  `None`, weight math at 4 / 4.5 / 5 stars, clipping, axis-key
  remapping.
- `tests/test_auth_helpers.py` — Flask session read/write helpers
  with Supabase calls mocked.

### Integration tests (deferred, called out, not in v1 scope)

Real-Supabase tests using `supabase start` in CI. Worth doing but
adds CI complexity. v1 covers the integration manually via the test
plan below.

### Manual test plan (run against your real Supabase project)

1. Anon: load `/` → recommendations work as today; rating dropdowns
   disabled with tooltip.
2. Sign up new user → confirm via Inbucket / real email → sign in.
3. Sign out → masthead shows anon links.
4. Sign in existing user → masthead shows display name.
5. Rate three IPAs at 4–5★ → reload `/` → sliders lean hoppy/bitter.
6. Open `/profile` → display_name editable; rated beers listed;
   Fig. III shows personalized radar.
7. Forgot password → reset email → set new password → log in with it.
8. Existing `tests/` suite still green (`uv run pytest`).

## Out of scope (deliberate)

- Social features, follow lists, public profiles
- Avatar uploads / Supabase Storage
- Custom (non-catalog) beers
- Dislike-penalty in personalization
- Deployment to a public host (designed-for, not done here)
- Local-Supabase integration tests in CI

## Open questions for implementation

None. All design choices are pinned. The implementation plan should
pick concrete versions for `supabase-py` / `python-dotenv` and verify
current method names against the Supabase Python SDK docs before
writing code (the SDK has had renames historically).
