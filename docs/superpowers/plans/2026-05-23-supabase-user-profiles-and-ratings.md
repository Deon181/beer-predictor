# Supabase user profiles & beer ratings — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Supabase-backed accounts, beer ratings, and rating-seeded slider defaults to the existing Dash recommender, without changing the anonymous experience.

**Architecture:** Flask routes (mounted on the existing `server = app.server`) handle auth pages; `supabase-py` mediates all Supabase calls; per-request user resolution via a `user_client()` factory that binds the user's JWT so RLS does the authorization. The recommender (`src/recommender.py`) is untouched; a new `personalized_defaults()` returns the sidebar's initial slider values.

**Tech Stack:** Python 3.13, Dash, Flask, `supabase` (Python SDK), `python-dotenv`, Postgres (Supabase), Jinja2 (auth templates).

**Note on git:** This repo is not a git repository. Per-task "commit" steps are omitted; run the full test suite at each commit point instead.

**Spec:** `docs/superpowers/specs/2026-05-23-supabase-user-profiles-and-ratings-design.md`

**One spec correction discovered during planning:** The spec says "add a `beer_id` column" — that column already exists in `build_catalog.py` and `data/processed/beers.parquet`, but as an unstable integer (row-position based, line 342). The fix is the same one the spec intended (slug format), but expressed as a *replace* in Task 2 below.

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | modify | Add `supabase`, `python-dotenv` deps |
| `.env.example` | create | Placeholders for `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `FLASK_SECRET_KEY` |
| `.gitignore` | create-or-modify | Ensure `.env` is ignored if/when this becomes a git repo |
| `src/config.py` | create | Single `load_env()` that reads `.env` and exposes `SETTINGS` |
| `scripts/build_catalog.py` | modify | Replace integer `beer_id` with `{brewery-slug}__{name-slug}` |
| `tests/test_catalog_slugs.py` | create | Slug determinism / uniqueness / format tests |
| `supabase/migrations/20260523000000_initial.sql` | create | Tables, trigger, RLS, grants |
| `src/db.py` | create | `anon_client()`, `user_client()` factories |
| `src/auth.py` | create | Thin wrappers on `supabase-py` auth calls |
| `tests/test_personalization.py` | create | Pure-Python tests for `personalized_defaults()` |
| `src/personalization.py` | create | `personalized_defaults(user_client, catalog)` |
| `dashboard/templates/auth/base.html` | create | Shared Jinja layout for auth pages |
| `dashboard/templates/auth/login.html` | create | Email + password login form |
| `dashboard/templates/auth/signup.html` | create | Signup form (email, password, display_name) |
| `dashboard/templates/auth/forgot.html` | create | Forgot-password form |
| `dashboard/templates/auth/reset.html` | create | Reset-password form |
| `dashboard/templates/auth/check_email.html` | create | "Check your inbox" page |
| `dashboard/auth_routes.py` | create | `auth_bp` Flask blueprint with the six routes |
| `dashboard/components/masthead.py` | create | Renders masthead with session-aware sign-in indicator |
| `dashboard/pages/__init__.py` | create | empty (marks the pages dir for Dash Pages) |
| `dashboard/pages/recommender.py` | create | Existing recommender layout + callbacks, plus rating dropdowns |
| `dashboard/pages/profile.py` | create | Display name editor, personalized radar, ledger of rated beers |
| `dashboard/app.py` | modify | Slim to bootstrap: load env, mount blueprint, configure Dash Pages |
| `tests/test_recommender.py` | modify | Accept string `beer_id` instead of int |
| `tests/test_data_prep.py` | modify | Accept string `beer_id` |
| `tests/test_catalog.py` | modify | Accept string `beer_id` |

---

## Task 1: Project bootstrap — deps, env loader, `.env.example`

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`, `.gitignore`, `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1.1: Add deps to `pyproject.toml`**

In `pyproject.toml` `[project].dependencies`, append:

```toml
    "supabase>=2.7",
    "python-dotenv>=1.0",
```

- [ ] **Step 1.2: Sync deps**

```powershell
uv sync
```

Expected: installs `supabase` and `python-dotenv` (and their transitive deps); exit code 0.

- [ ] **Step 1.3: Create `.gitignore`** at repo root with:

```
.env
.env.local
__pycache__/
*.pyc
.pytest_cache/
```

If a `.gitignore` already exists, ensure `.env` and `.env.local` are present.

- [ ] **Step 1.4: Create `.env.example`** at repo root:

```
# Copy to .env and fill in real values.
# Get URL + publishable key from:
#   Supabase dashboard → Project Settings → API Keys → "Publishable keys" tab.
# (Publishable keys (sb_publishable_...) supersede the legacy `anon` JWT key.)
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxxxxxxxxxxxxxxx

# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
FLASK_SECRET_KEY=change-me-to-64-hex
```

- [ ] **Step 1.5: Write the failing test** at `tests/test_config.py`:

```python
"""Env-loader contract: required keys raise, optional defaults sensible."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_settings_reads_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    monkeypatch.setenv("FLASK_SECRET_KEY", "a" * 64)
    from src import config
    settings = config.load_settings()
    assert settings.supabase_url == "https://x.supabase.co"
    assert settings.supabase_publishable_key == "sb_publishable_test"
    assert settings.flask_secret_key == "a" * 64


def test_settings_missing_required_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    from src import config
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        config.load_settings()
```

- [ ] **Step 1.6: Run — confirm fails (module does not exist yet)**

```powershell
uv run pytest tests/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'`.

- [ ] **Step 1.7: Create `src/config.py`**:

```python
"""Centralised env-driven settings. Loaded once at app startup."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_publishable_key: str
    flask_secret_key: str


def load_settings(dotenv_path: Path | None = None) -> Settings:
    """Read settings from env (loading `.env` first if present).

    Raises RuntimeError if any required key is missing — fail loud at startup
    rather than mid-request.
    """
    if dotenv_path is None:
        dotenv_path = ROOT / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)

    def _require(name: str) -> str:
        v = os.environ.get(name)
        if not v:
            raise RuntimeError(
                f"{name} is required but not set. "
                f"Copy .env.example to .env and fill it in."
            )
        return v

    return Settings(
        supabase_url=_require("SUPABASE_URL"),
        supabase_publishable_key=_require("SUPABASE_PUBLISHABLE_KEY"),
        flask_secret_key=_require("FLASK_SECRET_KEY"),
    )
```

- [ ] **Step 1.8: Re-run — confirm pass**

```powershell
uv run pytest tests/test_config.py -v
```

Expected: both tests PASS.

---

## Task 2: Replace integer `beer_id` with stable slug

**Files:**
- Modify: `scripts/build_catalog.py` (line 342 area, plus a new helper near the top)
- Create: `tests/test_catalog_slugs.py`
- Modify: `tests/test_catalog.py` (`test_unique_beer_ids` stays valid; no schema change required since the column name doesn't change)
- Modify: `tests/test_data_prep.py` (string equality, see step 2.6)
- Modify: `tests/test_recommender.py` (no change — only references `beer_id` in the column-presence assertion)

- [ ] **Step 2.1: Write the failing tests** at `tests/test_catalog_slugs.py`:

```python
"""beer_id must be a stable, slug-format string suitable for use as a
foreign reference from external systems (Supabase user_beers)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_catalog import slugify_beer_id

SLUG_RE = re.compile(r"^[a-z0-9-]+__[a-z0-9-]+$")


def test_slugify_basic() -> None:
    assert slugify_beer_id("Stone Brewing", "Arrogant Bastard Ale") == (
        "stone-brewing__arrogant-bastard-ale"
    )


def test_slugify_strips_punctuation() -> None:
    assert slugify_beer_id("Devil's Peak", "King's Blockhouse IPA") == (
        "devils-peak__kings-blockhouse-ipa"
    )


def test_slugify_collapses_whitespace() -> None:
    assert slugify_beer_id("  Sierra   Nevada  ", "Pale Ale") == (
        "sierra-nevada__pale-ale"
    )


def test_slugify_handles_ampersand_and_slashes() -> None:
    assert slugify_beer_id("Brew & Co", "IPA/Pale") == "brew-co__ipa-pale"


def test_slugify_keeps_digits() -> None:
    assert slugify_beer_id("Brewery 21", "Beer #4") == "brewery-21__beer-4"


def test_slug_matches_format() -> None:
    """Every produced slug matches SLUG_RE."""
    cases = [
        ("Stone Brewing", "Arrogant Bastard"),
        ("Devil's Peak", "King's Blockhouse"),
        ("Brewery 21", "Beer #4"),
        ("Brew & Co", "IPA/Pale"),
    ]
    for brewery, name in cases:
        slug = slugify_beer_id(brewery, name)
        assert SLUG_RE.match(slug), f"bad slug: {slug}"


def test_built_catalog_slugs_are_strings_and_unique() -> None:
    """End-to-end: the generated CSV uses string slugs and they're unique."""
    csv = ROOT / "data" / "raw" / "curated_beers.csv"
    assert csv.exists(), "run scripts/build_catalog.py first"
    df = pd.read_csv(csv)
    assert df["beer_id"].dtype == object, (
        f"beer_id should be string, got {df['beer_id'].dtype}"
    )
    assert df["beer_id"].is_unique
    for slug in df["beer_id"].head(20):
        assert SLUG_RE.match(slug), f"bad slug in built catalog: {slug}"
```

- [ ] **Step 2.2: Run — confirm fails**

```powershell
uv run pytest tests/test_catalog_slugs.py -v
```

Expected: FAIL with `ImportError: cannot import name 'slugify_beer_id'`.

- [ ] **Step 2.3: Add `slugify_beer_id` to `scripts/build_catalog.py`**

Near the top of the file (after imports, before `CURATED_COLUMNS`), add:

```python
import re

_SLUG_BAD = re.compile(r"[^a-z0-9]+")


def slugify_beer_id(brewery: str, name: str) -> str:
    """Stable URL-safe identifier: `{brewery-slug}__{name-slug}`.

    Lowercase, ASCII alphanumerics + hyphen only. Apostrophes, ampersands,
    slashes, and consecutive whitespace all collapse to a single hyphen.
    Uses `__` between brewery and name so the join survives the hyphenation.
    """
    def slug(s: str) -> str:
        s = s.lower().strip()
        s = _SLUG_BAD.sub("-", s)
        s = s.strip("-")
        return s
    return f"{slug(brewery)}__{slug(name)}"
```

- [ ] **Step 2.4: Replace the integer assignment in `main()`**

Find line 342:

```python
    combined.insert(0, "beer_id", range(1, len(combined) + 1))
```

Replace with:

```python
    combined.insert(
        0,
        "beer_id",
        [slugify_beer_id(b, n) for b, n in zip(combined["brewery"], combined["name"])],
    )
    if not combined["beer_id"].is_unique:
        dups = combined.loc[combined["beer_id"].duplicated(keep=False), :]
        raise AssertionError(
            f"slugify_beer_id produced duplicates:\n{dups[['beer_id','brewery','name']]}"
        )
```

- [ ] **Step 2.5: Run slug tests — first three pass; the end-to-end one still needs a rebuild**

```powershell
uv run pytest tests/test_catalog_slugs.py -v -k "not built_catalog"
```

Expected: all PASS.

- [ ] **Step 2.6: Update existing tests that assumed int**

In `tests/test_data_prep.py`, the existing assertion `df["beer_id"].is_unique` works for strings too — leave it. Find any equality comparison that uses int (search for `beer_id == 1` etc.); none currently exist, so no change. Run the existing suite (excluding catalog-dependent tests, which we'll rebuild in Task 3):

```powershell
uv run pytest tests/ -v --ignore=tests/test_catalog.py --ignore=tests/test_catalog_slugs.py --ignore=tests/test_recommender.py --ignore=tests/test_data_prep.py
```

Expected: PASS (or whatever was passing before — no regressions).

---

## Task 3: Regenerate catalog + verify all tests pass

**Files:**
- Modify: `data/raw/curated_beers.csv` (regenerated)
- Modify: `data/processed/beers.parquet` (regenerated via notebook)

- [ ] **Step 3.1: Rebuild the curated CSV**

```powershell
uv run python scripts/build_catalog.py
```

Expected: prints "final catalog: ~560 rows", exit 0. The CSV now has slug `beer_id`s like `cervecera-jerome__rubia`.

- [ ] **Step 3.2: Quick inspect**

```powershell
uv run python -c "import pandas as pd; df = pd.read_csv('data/raw/curated_beers.csv'); print(df[['beer_id','brewery','name']].head()); print(df['beer_id'].dtype); print(df['beer_id'].is_unique)"
```

Expected: `object` dtype, `True` uniqueness, slug-format ids.

- [ ] **Step 3.3: Rerun the data_prep notebook to regenerate the parquet**

```powershell
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/data_prep.ipynb
```

Expected: notebook executes to completion; `data/processed/beers.parquet` now has slug `beer_id`s.

- [ ] **Step 3.4: Run full test suite**

```powershell
uv run pytest tests/ -v
```

Expected: all tests PASS. (The `test_unique_beer_ids` test in both `test_catalog.py` and `test_data_prep.py` works fine for strings.)

---

## Task 4: Authenticate Supabase MCP + manual project configuration

**Files:** none — this is a one-time setup task done in the Supabase dashboard + your agent's MCP auth flow.

- [ ] **Step 4.1: Authenticate the Supabase MCP**

If the MCP tools aren't already visible to your agent, run the agent's authenticate flow for the Supabase plugin and complete the OAuth in the browser. After the callback URL is submitted, the project-management MCP tools become available.

- [ ] **Step 4.2: In the Supabase dashboard, confirm or set:**

  1. **Auth → Providers → Email:** enabled; "Confirm email" stays ON.
  2. **Auth → URL Configuration:**
     - Site URL: `http://127.0.0.1:8050`
     - Additional Redirect URLs: `http://127.0.0.1:8050/auth/callback`
  3. **Project Settings → API:** copy `URL` and `anon public` key.

- [ ] **Step 4.3: Create `.env` from `.env.example`** in the project root and fill in the three values. The `FLASK_SECRET_KEY` value can be generated via:

```powershell
uv run python -c "import secrets; print(secrets.token_hex(32))"
```

- [ ] **Step 4.4: Verify env loads**

```powershell
uv run python -c "from src.config import load_settings; s = load_settings(); print('OK', s.supabase_url[:24] + '...')"
```

Expected: `OK https://<your-ref>.supabase.co`.

---

## Task 5: Write & apply the initial Supabase migration

**Files:**
- Create: `supabase/migrations/20260523000000_initial.sql`

- [ ] **Step 5.1: Create the migrations directory and migration file**

```powershell
New-Item -ItemType Directory -Force supabase\migrations | Out-Null
```

Then create `supabase/migrations/20260523000000_initial.sql`:

```sql
-- Profiles: 1:1 with auth.users, holds display_name only.
CREATE TABLE public.profiles (
  id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL CHECK (char_length(display_name) BETWEEN 1 AND 50),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- User beers: one row per (user, catalog beer slug).
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

-- Trigger: mirror new auth users into public.profiles.
-- Lives in private schema with empty search_path per Supabase security guide.
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

-- Enable RLS.
ALTER TABLE public.profiles   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_beers ENABLE ROW LEVEL SECURITY;

-- profiles policies. Wrap auth.uid() in (select ...) so it evaluates
-- once per query instead of once per row — Supabase perf best practice.
-- See https://supabase.com/docs/guides/database/postgres/row-level-security#call-functions-with-select
CREATE POLICY profiles_select_own
  ON public.profiles FOR SELECT TO authenticated
  USING (id = (select auth.uid()));

CREATE POLICY profiles_update_own
  ON public.profiles FOR UPDATE TO authenticated
  USING (id = (select auth.uid())) WITH CHECK (id = (select auth.uid()));

-- user_beers policies.
CREATE POLICY user_beers_select_own
  ON public.user_beers FOR SELECT TO authenticated
  USING (user_id = (select auth.uid()));

CREATE POLICY user_beers_insert_own
  ON public.user_beers FOR INSERT TO authenticated
  WITH CHECK (user_id = (select auth.uid()));

CREATE POLICY user_beers_update_own
  ON public.user_beers FOR UPDATE TO authenticated
  USING (user_id = (select auth.uid())) WITH CHECK (user_id = (select auth.uid()));

CREATE POLICY user_beers_delete_own
  ON public.user_beers FOR DELETE TO authenticated
  USING (user_id = (select auth.uid()));

-- Grants. anon gets nothing on these tables.
GRANT SELECT, INSERT, UPDATE, DELETE ON public.profiles    TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_beers  TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.user_beers_id_seq   TO authenticated;
```

- [ ] **Step 5.2: Apply the migration via Supabase MCP `apply_migration`**

Use the MCP tool `apply_migration` with `name="initial"` and `query` set to the SQL above. (If your agent doesn't have the MCP available, an equivalent is `supabase db push` with the file in place, but that requires `supabase link`.)

Expected: migration applied; rows present in `supabase_migrations.schema_migrations`.

- [ ] **Step 5.3: Run advisors**

Use the MCP tool `get_advisors` with `type="security"`. Fix any findings before proceeding. Then `type="performance"` — fix anything material.

Expected: no high/medium security findings; performance findings on these tiny tables should be informational only.

- [ ] **Step 5.4: Smoke-verify tables exist**

Use MCP `execute_sql`:

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('public','private')
  AND table_name IN ('profiles','user_beers')
ORDER BY table_schema, table_name;
```

Expected: two rows: `public.profiles`, `public.user_beers`.

- [ ] **Step 5.5: Verify the trigger fires (creates a profile)**

Sign up a throwaway user via the Supabase dashboard's Authentication → Users → "Add user", then:

```sql
SELECT id, display_name FROM public.profiles ORDER BY created_at DESC LIMIT 1;
```

Expected: one row matching the new user; `display_name` defaulted from the email prefix.

Then delete the test user from the dashboard.

---

## Task 6: `src/db.py` — Supabase client factories

**Files:**
- Create: `src/db.py`
- Create: `tests/test_db.py`

`anon_client()` is straightforward; `user_client()` reads tokens from the Flask session, refreshes if expired, and writes refreshed tokens back. Because it touches Flask `session`, the tests use `flask.Flask(__name__).test_request_context()`.

- [ ] **Step 6.1: Write the failing tests** at `tests/test_db.py`:

```python
"""Tests for src.db — client factories.

We mock `supabase-py`'s create_client so tests stay offline."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import flask
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def app_with_session(monkeypatch: pytest.MonkeyPatch) -> flask.Flask:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    monkeypatch.setenv("FLASK_SECRET_KEY", "k" * 64)
    app = flask.Flask(__name__)
    app.secret_key = "k" * 64
    return app


def test_anon_client_uses_url_and_publishable_key(app_with_session: flask.Flask) -> None:
    from src import db
    with patch("src.db.create_client") as mock_create:
        mock_create.return_value = MagicMock()
        db.anon_client()
    mock_create.assert_called_once_with("https://x.supabase.co", "sb_publishable_test")


def test_user_client_returns_none_when_session_empty(app_with_session: flask.Flask) -> None:
    from src import db
    with app_with_session.test_request_context():
        assert db.user_client() is None


def test_user_client_binds_tokens_from_session(app_with_session: flask.Flask) -> None:
    from src import db
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.access_token = "access-old"
    mock_session.refresh_token = "refresh-old"
    mock_client.auth.get_session.return_value = mock_session

    with patch("src.db.create_client", return_value=mock_client):
        with app_with_session.test_request_context():
            flask.session["access_token"] = "access-old"
            flask.session["refresh_token"] = "refresh-old"
            client = db.user_client()

    assert client is mock_client
    mock_client.auth.set_session.assert_called_once_with("access-old", "refresh-old")


def test_user_client_persists_refreshed_tokens(app_with_session: flask.Flask) -> None:
    from src import db
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.access_token = "access-new"   # different from session value
    mock_session.refresh_token = "refresh-new"
    mock_client.auth.get_session.return_value = mock_session

    with patch("src.db.create_client", return_value=mock_client):
        with app_with_session.test_request_context():
            flask.session["access_token"] = "access-old"
            flask.session["refresh_token"] = "refresh-old"
            db.user_client()
            assert flask.session["access_token"] == "access-new"
            assert flask.session["refresh_token"] == "refresh-new"
```

- [ ] **Step 6.2: Run — confirm fails**

```powershell
uv run pytest tests/test_db.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.db'`.

- [ ] **Step 6.3: Create `src/db.py`**:

```python
"""Supabase client factories.

`anon_client()` — unauthenticated; safe for any callable from anywhere.
`user_client()` — Flask-request-scoped; bound to the signed-in user's JWT
so RLS sees `auth.uid()` and rows are authorized correctly.
"""
from __future__ import annotations

from typing import Optional

import flask
from supabase import Client, create_client

from src.config import load_settings

_SETTINGS = None


def _settings():
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = load_settings()
    return _SETTINGS


def anon_client() -> Client:
    """Unauthenticated client — uses the `anon` Postgres role for RLS."""
    s = _settings()
    return create_client(s.supabase_url, s.supabase_publishable_key)


def user_client() -> Optional[Client]:
    """Return a Supabase client bound to the signed-in user, or None."""
    access = flask.session.get("access_token")
    refresh = flask.session.get("refresh_token")
    if not access or not refresh:
        return None

    s = _settings()
    client = create_client(s.supabase_url, s.supabase_publishable_key)
    client.auth.set_session(access, refresh)

    sess = client.auth.get_session()
    if sess is not None and (
        sess.access_token != access or sess.refresh_token != refresh
    ):
        flask.session["access_token"] = sess.access_token
        flask.session["refresh_token"] = sess.refresh_token
    return client
```

- [ ] **Step 6.4: Re-run — confirm pass**

```powershell
uv run pytest tests/test_db.py -v
```

Expected: all four tests PASS.

---

## Task 7: `src/auth.py` — auth helper wrappers

These are thin so most of the value is the interface. They exist so route handlers don't import `supabase-py` directly and tests can mock at the helper layer.

**Files:**
- Create: `src/auth.py`
- Create: `tests/test_auth_helpers.py`

- [ ] **Step 7.1: Write the failing tests** at `tests/test_auth_helpers.py`:

```python
"""Tests for src.auth — sign up / in / out helpers.

We mock the supabase client returned by anon_client() and assert the
helpers pass the right arguments through."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import flask
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> flask.Flask:
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    monkeypatch.setenv("FLASK_SECRET_KEY", "k" * 64)
    a = flask.Flask(__name__)
    a.secret_key = "k" * 64
    return a


def test_sign_up_passes_email_password_and_display_name(app: flask.Flask) -> None:
    from src import auth as A
    mock = MagicMock()
    mock.auth.sign_up.return_value.user.id = "uid-1"
    with patch("src.auth.anon_client", return_value=mock):
        with app.test_request_context():
            A.sign_up("a@b.com", "secret-pw", "Alice")
    mock.auth.sign_up.assert_called_once_with({
        "email": "a@b.com",
        "password": "secret-pw",
        "options": {
            "data": {"display_name": "Alice"},
            "email_redirect_to": "http://localhost/auth/callback",
        },
    })


def test_sign_in_writes_tokens_to_session(app: flask.Flask) -> None:
    from src import auth as A
    mock = MagicMock()
    sess = MagicMock()
    sess.access_token = "AT"
    sess.refresh_token = "RT"
    sess.user.id = "uid-1"
    mock.auth.sign_in_with_password.return_value.session = sess
    with patch("src.auth.anon_client", return_value=mock):
        with app.test_request_context():
            A.sign_in("a@b.com", "secret-pw")
            assert flask.session["access_token"] == "AT"
            assert flask.session["refresh_token"] == "RT"
            assert flask.session["user_id"] == "uid-1"


def test_sign_out_clears_session(app: flask.Flask) -> None:
    from src import auth as A
    mock = MagicMock()
    with patch("src.auth.user_client", return_value=mock):
        with app.test_request_context():
            flask.session["access_token"] = "x"
            flask.session["refresh_token"] = "y"
            flask.session["user_id"] = "z"
            A.sign_out()
            assert "access_token" not in flask.session
            assert "refresh_token" not in flask.session
            assert "user_id" not in flask.session


def test_current_user_id_reads_session(app: flask.Flask) -> None:
    from src import auth as A
    with app.test_request_context():
        assert A.current_user_id() is None
        flask.session["user_id"] = "uid-1"
        assert A.current_user_id() == "uid-1"


def test_exchange_code_writes_tokens(app: flask.Flask) -> None:
    from src import auth as A
    mock = MagicMock()
    sess = MagicMock()
    sess.access_token = "AT2"
    sess.refresh_token = "RT2"
    sess.user.id = "uid-2"
    mock.auth.exchange_code_for_session.return_value.session = sess
    with patch("src.auth.anon_client", return_value=mock):
        with app.test_request_context():
            A.exchange_code_for_session("the-code")
            assert flask.session["access_token"] == "AT2"
            assert flask.session["user_id"] == "uid-2"
```

- [ ] **Step 7.2: Run — confirm fails**

```powershell
uv run pytest tests/test_auth_helpers.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.auth'`.

- [ ] **Step 7.3: Create `src/auth.py`**:

```python
"""Thin wrappers around supabase-py auth calls.

Route handlers go through these helpers so:
  - we centralise the session-cookie writing (no scattered duplication)
  - tests can mock at this layer instead of supabase-py
  - we never reference user_metadata in authorization decisions
"""
from __future__ import annotations

from typing import Optional

import flask

from src.db import anon_client, user_client


def _callback_url() -> str:
    """Absolute URL to /auth/callback for this request's host."""
    return flask.url_for("auth.callback", _external=True)


def _write_session(sess) -> None:
    flask.session["access_token"] = sess.access_token
    flask.session["refresh_token"] = sess.refresh_token
    flask.session["user_id"] = sess.user.id


def sign_up(email: str, password: str, display_name: str) -> None:
    """Create a new auth user. Display name lives in user_metadata.

    Note: user_metadata is user-editable and MUST NOT be used in any
    authorization decision. It's purely cosmetic.
    """
    client = anon_client()
    client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "data": {"display_name": display_name},
            "email_redirect_to": _callback_url(),
        },
    })


def sign_in(email: str, password: str) -> None:
    """Sign in with email + password; persists tokens to Flask session."""
    client = anon_client()
    resp = client.auth.sign_in_with_password({"email": email, "password": password})
    _write_session(resp.session)


def sign_out() -> None:
    client = user_client()
    if client is not None:
        try:
            client.auth.sign_out()
        except Exception:
            pass  # we still clear local session even if remote revoke fails
    flask.session.pop("access_token", None)
    flask.session.pop("refresh_token", None)
    flask.session.pop("user_id", None)


def request_password_reset(email: str) -> None:
    client = anon_client()
    client.auth.reset_password_for_email(email, {"redirect_to": _callback_url()})


def update_password(new_password: str) -> None:
    client = user_client()
    if client is None:
        raise RuntimeError("Not signed in")
    client.auth.update_user({"password": new_password})


def exchange_code_for_session(code: str) -> None:
    """Used by /auth/callback for PKCE confirm-email / reset-password flows."""
    client = anon_client()
    resp = client.auth.exchange_code_for_session({"auth_code": code})
    _write_session(resp.session)


def current_user_id() -> Optional[str]:
    return flask.session.get("user_id")
```

- [ ] **Step 7.4: Re-run — confirm pass**

```powershell
uv run pytest tests/test_auth_helpers.py -v
```

Expected: all five tests PASS.

> If `test_sign_up_passes_email_password_and_display_name` fails because
> `email_redirect_to` resolves to `http://127.0.0.1:8050/auth/callback` (your
> dev) instead of `http://localhost/auth/callback` (Flask's default test
> host), update the assertion to compare *startswith* the value, or assert
> `kwargs["options"]["email_redirect_to"].endswith("/auth/callback")`.

---

## Task 8: Auth blueprint — signup route + base template + signup template

**Files:**
- Create: `dashboard/auth_routes.py`
- Create: `dashboard/templates/auth/base.html`
- Create: `dashboard/templates/auth/signup.html`
- Create: `dashboard/templates/auth/check_email.html`

- [ ] **Step 8.1: Create `dashboard/templates/auth/base.html`**:

```jinja
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{% block title %}Beer Predictor{% endblock %} — The Beer Predictor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,800;9..144,900&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    body {
      background: #F1E8D3; color: #1A1410;
      font-family: "Newsreader", Georgia, serif;
      margin: 0; padding: 4rem 1rem; display: flex; justify-content: center;
    }
    .card {
      max-width: 28rem; width: 100%; background: #F8F1DE;
      padding: 2rem 2rem 2.5rem; border: 1px solid rgba(26,20,16,0.20);
    }
    h1 { font-family: "Fraunces", Georgia, serif; font-weight: 800;
         font-size: 1.6rem; margin: 0 0 1rem 0; }
    label { display: block; font-family: "IBM Plex Mono", monospace;
            font-size: 0.7rem; letter-spacing: 0.18em; text-transform: uppercase;
            color: #4A382A; margin: 1.1rem 0 0.35rem 0; }
    input[type="email"], input[type="password"], input[type="text"] {
      width: 100%; box-sizing: border-box; padding: 0.55rem 0.7rem;
      font-family: inherit; font-size: 1rem;
      background: #F1E8D3; color: #1A1410;
      border: 1px solid rgba(26,20,16,0.30);
    }
    button {
      margin-top: 1.4rem; padding: 0.65rem 1.3rem;
      font-family: "IBM Plex Mono", monospace; font-size: 0.78rem;
      letter-spacing: 0.18em; text-transform: uppercase;
      background: #1A1410; color: #F1E8D3; border: 0; cursor: pointer;
    }
    .alert { padding: 0.7rem 0.9rem; margin-top: 1rem;
             background: #E6DABB; border-left: 3px solid #6B1F1F;
             font-size: 0.92rem; }
    .links { margin-top: 1.4rem; font-size: 0.9rem; }
    .links a { color: #B0651E; text-decoration: none; margin-right: 1rem; }
    .links a:hover { text-decoration: underline; }
    .nav-back { display: block; margin-bottom: 1rem;
                font-family: "IBM Plex Mono", monospace; font-size: 0.7rem;
                letter-spacing: 0.18em; text-transform: uppercase;
                color: #4A382A; text-decoration: none; }
  </style>
</head>
<body>
  <div class="card">
    <a class="nav-back" href="/">← The Beer Predictor</a>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, msg in messages %}
        <div class="alert">{{ msg }}</div>
      {% endfor %}
    {% endwith %}
    {% block content %}{% endblock %}
  </div>
</body>
</html>
```

- [ ] **Step 8.2: Create `dashboard/templates/auth/signup.html`**:

```jinja
{% extends "auth/base.html" %}
{% block title %}Sign up{% endblock %}
{% block content %}
<h1>Sign up</h1>
<form method="post" action="{{ url_for('auth.signup') }}">
  <label for="display_name">Display name</label>
  <input id="display_name" name="display_name" type="text" required maxlength="50" value="{{ request.form.get('display_name', '') }}">
  <label for="email">Email</label>
  <input id="email" name="email" type="email" required value="{{ request.form.get('email', '') }}">
  <label for="password">Password (min 8)</label>
  <input id="password" name="password" type="password" required minlength="8">
  <button type="submit">Create account</button>
</form>
<div class="links">
  <a href="{{ url_for('auth.login') }}">Sign in instead</a>
</div>
{% endblock %}
```

- [ ] **Step 8.3: Create `dashboard/templates/auth/check_email.html`**:

```jinja
{% extends "auth/base.html" %}
{% block title %}Check your email{% endblock %}
{% block content %}
<h1>Check your email</h1>
<p>{{ message or "We've sent you a link. Click it to continue." }}</p>
<div class="links"><a href="/">Back to the recommender</a></div>
{% endblock %}
```

- [ ] **Step 8.4: Create `dashboard/auth_routes.py` with signup-only routes**:

```python
"""Flask blueprint for auth pages."""
from __future__ import annotations

from pathlib import Path

import flask

from src import auth as A

_TEMPLATES = Path(__file__).resolve().parent / "templates"

auth_bp = flask.Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
    template_folder=str(_TEMPLATES),
)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if flask.request.method == "POST":
        email = flask.request.form.get("email", "").strip().lower()
        password = flask.request.form.get("password", "")
        display_name = flask.request.form.get("display_name", "").strip()
        if not (email and password and display_name):
            flask.flash("All fields are required.", "error")
            return flask.render_template("auth/signup.html")
        if len(password) < 8:
            flask.flash("Password must be at least 8 characters.", "error")
            return flask.render_template("auth/signup.html")
        try:
            A.sign_up(email, password, display_name)
        except Exception as e:  # noqa: BLE001
            flask.flash(f"Signup failed: {e}", "error")
            return flask.render_template("auth/signup.html")
        return flask.render_template(
            "auth/check_email.html",
            message="Check your inbox for a confirmation link.",
        )
    return flask.render_template("auth/signup.html")


# Stub routes — replaced with real implementations in Tasks 9 and 10.
# These exist now so `url_for('auth.callback', _external=True)` in
# `src/auth.py::_callback_url` resolves during this task's tests.
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    return ("Not yet wired", 501)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    return ("Not yet wired", 501)


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    return ("Not yet wired", 501)


@auth_bp.route("/reset", methods=["GET", "POST"])
def reset():
    return ("Not yet wired", 501)


@auth_bp.route("/callback")
def callback():
    return ("Not yet wired", 501)
```

- [ ] **Step 8.5: Smoke-test the blueprint mounts (no real Supabase call)**

```powershell
uv run python -c "import flask; from dashboard.auth_routes import auth_bp; app = flask.Flask(__name__); app.secret_key = 'x'*64; app.register_blueprint(auth_bp); print([r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/auth')])"
```

Expected: prints six routes — `/auth/signup`, `/auth/login`, `/auth/logout`, `/auth/forgot`, `/auth/reset`, `/auth/callback`.

---

## Task 9: Auth blueprint — login + logout

**Files:**
- Modify: `dashboard/auth_routes.py` (replace placeholders for `login`, `logout`)
- Create: `dashboard/templates/auth/login.html`

- [ ] **Step 9.1: Create `dashboard/templates/auth/login.html`**:

```jinja
{% extends "auth/base.html" %}
{% block title %}Sign in{% endblock %}
{% block content %}
<h1>Sign in</h1>
<form method="post" action="{{ url_for('auth.login') }}">
  <label for="email">Email</label>
  <input id="email" name="email" type="email" required value="{{ request.form.get('email', '') }}">
  <label for="password">Password</label>
  <input id="password" name="password" type="password" required>
  <button type="submit">Sign in</button>
</form>
<div class="links">
  <a href="{{ url_for('auth.signup') }}">Create an account</a>
  <a href="{{ url_for('auth.forgot') }}">Forgot password?</a>
</div>
{% endblock %}
```

- [ ] **Step 9.2: Replace the `login` and `logout` placeholders in `dashboard/auth_routes.py`**:

```python
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if flask.request.method == "POST":
        email = flask.request.form.get("email", "").strip().lower()
        password = flask.request.form.get("password", "")
        if not (email and password):
            flask.flash("Email and password are required.", "error")
            return flask.render_template("auth/login.html")
        try:
            A.sign_in(email, password)
        except Exception as e:  # noqa: BLE001
            flask.flash(f"Sign in failed: {e}", "error")
            return flask.render_template("auth/login.html")
        return flask.redirect("/")
    return flask.render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    A.sign_out()
    return flask.redirect("/")
```

- [ ] **Step 9.3: Smoke-test that templates render without raising**

```powershell
uv run python -c "import flask; from dashboard.auth_routes import auth_bp; app = flask.Flask(__name__); app.secret_key = 'x'*64; app.register_blueprint(auth_bp); c = app.test_client(); print(c.get('/auth/login').status_code, c.get('/auth/signup').status_code)"
```

Expected: `200 200`.

---

## Task 10: Auth blueprint — forgot / reset / callback (PKCE)

**Files:**
- Modify: `dashboard/auth_routes.py` (replace `forgot`, `reset`, `callback`)
- Create: `dashboard/templates/auth/forgot.html`
- Create: `dashboard/templates/auth/reset.html`

- [ ] **Step 10.1: Create `dashboard/templates/auth/forgot.html`**:

```jinja
{% extends "auth/base.html" %}
{% block title %}Forgot password{% endblock %}
{% block content %}
<h1>Forgot password</h1>
<form method="post" action="{{ url_for('auth.forgot') }}">
  <label for="email">Email</label>
  <input id="email" name="email" type="email" required>
  <button type="submit">Send reset link</button>
</form>
<div class="links"><a href="{{ url_for('auth.login') }}">Back to sign in</a></div>
{% endblock %}
```

- [ ] **Step 10.2: Create `dashboard/templates/auth/reset.html`**:

```jinja
{% extends "auth/base.html" %}
{% block title %}Reset password{% endblock %}
{% block content %}
<h1>Set a new password</h1>
<form method="post" action="{{ url_for('auth.reset') }}">
  <label for="password">New password (min 8)</label>
  <input id="password" name="password" type="password" required minlength="8">
  <button type="submit">Update password</button>
</form>
{% endblock %}
```

- [ ] **Step 10.3: Replace `forgot`, `reset`, `callback` in `dashboard/auth_routes.py`**:

```python
@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if flask.request.method == "POST":
        email = flask.request.form.get("email", "").strip().lower()
        if not email:
            flask.flash("Email is required.", "error")
            return flask.render_template("auth/forgot.html")
        try:
            A.request_password_reset(email)
        except Exception as e:  # noqa: BLE001
            flask.flash(f"Could not send reset email: {e}", "error")
            return flask.render_template("auth/forgot.html")
        return flask.render_template(
            "auth/check_email.html",
            message="If that email is registered, we just sent a reset link.",
        )
    return flask.render_template("auth/forgot.html")


@auth_bp.route("/reset", methods=["GET", "POST"])
def reset():
    if not A.current_user_id():
        flask.flash("Open the reset link from your email first.", "error")
        return flask.redirect(flask.url_for("auth.forgot"))
    if flask.request.method == "POST":
        new = flask.request.form.get("password", "")
        if len(new) < 8:
            flask.flash("Password must be at least 8 characters.", "error")
            return flask.render_template("auth/reset.html")
        try:
            A.update_password(new)
        except Exception as e:  # noqa: BLE001
            flask.flash(f"Could not update password: {e}", "error")
            return flask.render_template("auth/reset.html")
        flask.flash("Password updated.", "info")
        return flask.redirect("/")
    return flask.render_template("auth/reset.html")


@auth_bp.route("/callback")
def callback():
    code = flask.request.args.get("code")
    if not code:
        flask.flash("Missing confirmation code.", "error")
        return flask.redirect(flask.url_for("auth.login"))
    try:
        A.exchange_code_for_session(code)
    except Exception as e:  # noqa: BLE001
        flask.flash(f"Could not complete sign-in: {e}", "error")
        return flask.redirect(flask.url_for("auth.login"))
    nxt = flask.request.args.get("next") or "/"
    return flask.redirect(nxt)
```

- [ ] **Step 10.4: Smoke-test all six routes return non-500**

```powershell
uv run python -c "import flask; from dashboard.auth_routes import auth_bp; app = flask.Flask(__name__); app.secret_key = 'x'*64; app.register_blueprint(auth_bp); c = app.test_client(); print({r: c.get(r).status_code for r in ['/auth/login','/auth/signup','/auth/forgot','/auth/reset','/auth/callback']})"
```

Expected: `200, 200, 200, 302 (redirects because no session), 302 (redirects because no code)`.

---

## Task 11: Wire blueprint + secret key + masthead sign-in indicator

**Files:**
- Create: `dashboard/components/masthead.py`
- Modify: `dashboard/app.py` (mount blueprint, set secret_key, route the masthead through the new component)

- [ ] **Step 11.1: Move the masthead into its own component** at `dashboard/components/masthead.py`:

```python
"""Masthead with session-aware sign-in indicator. Read Flask session
at layout-build time (not in a callback) to avoid first-paint flicker."""
from __future__ import annotations

import flask
from dash import html

from src import auth as A
from src.db import user_client


def _signed_in_links(display_name: str) -> html.Span:
    return html.Span([
        html.Span(display_name, className="me-name"),
        html.Span(" · "),
        html.A("Profile", href="/profile"),
        html.Span(" · "),
        html.Form(
            html.Button("Sign out", type="submit", className="linkish"),
            action="/auth/logout", method="post",
            style={"display": "inline"},
        ),
    ], className="me-strip")


def _anon_links() -> html.Span:
    return html.Span([
        html.A("Sign in", href="/auth/login"),
        html.Span(" · "),
        html.A("Sign up", href="/auth/signup"),
    ], className="me-strip")


def _fetch_display_name() -> str | None:
    uid = A.current_user_id()
    if not uid:
        return None
    client = user_client()
    if client is None:
        return None
    try:
        resp = client.table("profiles").select("display_name").eq("id", uid).single().execute()
        return (resp.data or {}).get("display_name")
    except Exception:
        return None


def masthead() -> html.Header:
    name = _fetch_display_name()
    me = _signed_in_links(name) if name else _anon_links()
    return html.Header(
        [
            html.Div(
                [
                    html.Span("Vol. I · Established mmxxvi"),
                    html.Span("A taste-profile broadsheet"),
                    me,
                ],
                className="vol",
            ),
            html.H1([
                "The Beer ",
                html.Span("&", className="amp"),
                " Predictor",
            ]),
            html.P(
                "Seven sliders, an honest catalogue, and the patience to read a chart.",
                className="kicker",
            ),
            html.Hr(className="doublerule"),
        ],
        className="masthead",
    )
```

- [ ] **Step 11.2: Modify `dashboard/app.py`** to:
  1. Load env at startup (raises if missing).
  2. Set Flask `secret_key` and secure-cookie config.
  3. Register the auth blueprint.
  4. Replace the `_masthead()` function with a call to the new component.

Add near the top, after the existing imports and before `app = dash.Dash(...)`:

```python
from src.config import load_settings
from dashboard.auth_routes import auth_bp
from dashboard.components.masthead import masthead as _masthead

_SETTINGS = load_settings()
```

Then after `server = app.server`:

```python
server.secret_key = _SETTINGS.flask_secret_key
server.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # set True in production via env override
)
server.register_blueprint(auth_bp)
```

Remove the existing in-file `_masthead()` function and replace its call site in `app.layout`. The existing line:

```python
app.layout = html.Div([
    _masthead(),
    html.Div([_sidebar(), _main()], className="spread"),
    _colophon(),
])
```

… changes to a layout function so the masthead re-renders per request (otherwise it shows the anon links forever):

```python
def _layout():
    return html.Div([
        _masthead(),
        html.Div([_sidebar(), _main()], className="spread"),
        _colophon(),
    ])

app.layout = _layout
```

- [ ] **Step 11.3: Smoke-run the dashboard**

```powershell
uv run python dashboard/app.py
```

Expected: starts on `http://127.0.0.1:8050`; visiting `/` renders the recommender as before plus a new "Sign in · Sign up" strip in the masthead. Visiting `/auth/signup` renders the signup form. Ctrl-C when verified.

- [ ] **Step 11.4: Manual end-to-end signup test**

  1. From the masthead, click "Sign up" → fill in email, password, display_name → submit.
  2. Confirmation email arrives (Inbucket if local-stack, or real inbox if remote project).
  3. Click confirmation link → should redirect to `/` with a session cookie set.
  4. Masthead now shows `<display_name> · Profile · Sign out`.
  5. Click "Sign out" → masthead returns to anon strip.

If signup fails, re-check `.env` values and Supabase redirect URL config from Task 4.

---

## Task 12: `src/personalization.py` — personalized slider defaults

**Files:**
- Create: `tests/test_personalization.py`
- Create: `src/personalization.py`

This is a pure function — no Supabase calls. It takes already-fetched ratings + the catalog and returns the slider dict. The Dash sidebar (Task 14) will do the Supabase query and pass results in. This keeps personalization testable offline.

- [ ] **Step 12.1: Write the failing tests** at `tests/test_personalization.py`:

```python
"""Tests for src.personalization.personalized_defaults — pure function."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.personalization import (
    SLIDER_AXES_KEYS,
    personalized_defaults,
)


def _mini_catalog() -> pd.DataFrame:
    """Tiny catalog: two distinct taste-vector beers for testing."""
    rows = [
        # hop bomb
        {"beer_id": "hop__bomb", "name": "Hop Bomb", "brewery": "X", "style": "IPA",
         "country": "USA", "abv": 7.0, "ibu": 90, "srm": 6,
         "bitterness": 9.0, "sweetness": 1.0, "maltiness": 3.0, "hoppiness": 9.0,
         "body": 5.0, "sourness": 0.0, "abv_normalized": 5.8},
        # malt bomb
        {"beer_id": "malt__bomb", "name": "Malt Bomb", "brewery": "Y", "style": "Stout",
         "country": "USA", "abv": 8.0, "ibu": 35, "srm": 35,
         "bitterness": 3.0, "sweetness": 7.0, "maltiness": 9.0, "hoppiness": 2.0,
         "body": 9.0, "sourness": 0.0, "abv_normalized": 6.7},
    ]
    return pd.DataFrame(rows)


def test_returns_none_when_no_ratings() -> None:
    cat = _mini_catalog()
    assert personalized_defaults([], cat) is None


def test_returns_none_when_no_ratings_at_or_above_4() -> None:
    cat = _mini_catalog()
    ratings = [
        {"beer_id": "hop__bomb", "rating": 3.5},
        {"beer_id": "malt__bomb", "rating": 2.0},
    ]
    assert personalized_defaults(ratings, cat) is None


def test_single_5star_returns_that_beer_vector_as_sliders() -> None:
    cat = _mini_catalog()
    ratings = [{"beer_id": "hop__bomb", "rating": 5.0}]
    defaults = personalized_defaults(ratings, cat)
    assert defaults is not None
    # abv_normalized maps to abv_preference for the slider
    assert defaults["bitterness"] == 9.0
    assert defaults["hoppiness"] == 9.0
    assert defaults["abv_preference"] == 5.8
    # all returned keys are slider keys, not column keys
    assert set(defaults.keys()) == set(SLIDER_AXES_KEYS)


def test_weighted_average_5star_outweighs_4star() -> None:
    """5★ has weight 2.0, 4★ has weight 1.0 — so result leans toward 5★."""
    cat = _mini_catalog()
    ratings = [
        {"beer_id": "hop__bomb", "rating": 5.0},   # weight 2.0
        {"beer_id": "malt__bomb", "rating": 4.0},  # weight 1.0
    ]
    defaults = personalized_defaults(ratings, cat)
    assert defaults is not None
    # bitterness: (2.0*9.0 + 1.0*3.0) / 3.0 = 7.0
    assert defaults["bitterness"] == pytest_approx(7.0)
    # hoppiness:  (2.0*9.0 + 1.0*2.0) / 3.0 = 6.666...
    assert defaults["hoppiness"] == pytest_approx(20.0 / 3.0)


def test_clips_to_0_10() -> None:
    """Hypothetical out-of-range beer values still produce clipped sliders."""
    cat = pd.DataFrame([{
        "beer_id": "wild__one", "name": "X", "brewery": "Y", "style": "Z",
        "country": "USA", "abv": 5, "ibu": 0, "srm": 0,
        "bitterness": 15.0, "sweetness": -3.0, "maltiness": 5.0, "hoppiness": 5.0,
        "body": 5.0, "sourness": 5.0, "abv_normalized": 5.0,
    }])
    defaults = personalized_defaults([{"beer_id": "wild__one", "rating": 5.0}], cat)
    assert defaults is not None
    assert defaults["bitterness"] == 10.0
    assert defaults["sweetness"] == 0.0


def test_orphan_beer_id_is_skipped() -> None:
    """Ratings whose beer_id no longer exists in the catalog are dropped."""
    cat = _mini_catalog()
    ratings = [
        {"beer_id": "vanished__beer", "rating": 5.0},
        {"beer_id": "hop__bomb", "rating": 5.0},
    ]
    defaults = personalized_defaults(ratings, cat)
    assert defaults is not None
    # Should equal the hop bomb vector alone (the orphan is dropped).
    assert defaults["bitterness"] == 9.0


# pytest.approx helper imported lazily to keep imports tidy
def pytest_approx(value: float, rel: float = 1e-6):
    import pytest as _pt
    return _pt.approx(value, rel=rel)
```

- [ ] **Step 12.2: Run — confirm fails**

```powershell
uv run pytest tests/test_personalization.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 12.3: Create `src/personalization.py`**:

```python
"""Compute personalized slider defaults from a user's ratings.

Pure function — no Supabase calls. Tests run offline with fabricated data.
The caller (the recommender sidebar) is responsible for fetching the
user's ratings via user_client() and passing them in.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional

import numpy as np
import pandas as pd

from src.recommender import TASTE_COLS, SLIDER_TO_COLUMN

# Inverse of SLIDER_TO_COLUMN, for the keys we expose: column → slider key.
_COL_TO_SLIDER = {
    "bitterness": "bitterness",
    "sweetness": "sweetness",
    "maltiness": "maltiness",
    "hoppiness": "hoppiness",
    "body": "body",
    "sourness": "sourness",
    "abv_normalized": "abv_preference",
}

SLIDER_AXES_KEYS = tuple(_COL_TO_SLIDER.values())

# Only ratings >= this threshold contribute to the personalized profile.
_LIKE_THRESHOLD = 4.0


def personalized_defaults(
    ratings: Iterable[Mapping[str, object]],
    catalog: pd.DataFrame,
) -> Optional[dict[str, float]]:
    """Return slider defaults from a user's likes, or None if no likes.

    Parameters
    ----------
    ratings
        Iterable of mappings with at least `beer_id` (str) and `rating` (float).
    catalog
        The processed beer catalog (one row per beer; must include
        `beer_id` and every column in TASTE_COLS).

    Returns
    -------
    dict[str, float] or None
        Slider-key dict (bitterness, sweetness, …, abv_preference) clipped
        to [0, 10]. Returns None if the user has no ratings >= 4★ (or all
        their liked beers are orphaned).
    """
    if catalog is None or catalog.empty:
        return None

    liked = [
        r for r in ratings
        if float(r.get("rating", 0.0)) >= _LIKE_THRESHOLD
    ]
    if not liked:
        return None

    # Index the catalog by beer_id for fast lookup.
    cat_by_id = catalog.set_index("beer_id")
    accum = np.zeros(len(TASTE_COLS), dtype=float)
    total_weight = 0.0

    for r in liked:
        beer_id = r["beer_id"]
        if beer_id not in cat_by_id.index:
            continue  # orphan — beer no longer in catalog
        rating = float(r["rating"])
        weight = rating - 3.0  # 4★→1.0, 4.5★→1.5, 5★→2.0
        row = cat_by_id.loc[beer_id, list(TASTE_COLS)].to_numpy(dtype=float)
        accum += weight * row
        total_weight += weight

    if total_weight == 0.0:
        return None

    vector = np.clip(accum / total_weight, 0.0, 10.0)
    out: dict[str, float] = {}
    for col, val in zip(TASTE_COLS, vector):
        slider_key = _COL_TO_SLIDER[col]
        out[slider_key] = float(val)
    return out
```

- [ ] **Step 12.4: Re-run — confirm pass**

```powershell
uv run pytest tests/test_personalization.py -v
```

Expected: all six tests PASS.

---

## Task 13: Refactor dashboard to Dash Pages — move recommender layout to `pages/recommender.py`

This task is *mechanical* — move existing code into a Dash Pages module. The sidebar still defaults to `5.0` here; Task 14 swaps in the personalized defaults.

**Files:**
- Create: `dashboard/pages/__init__.py` (empty)
- Create: `dashboard/pages/recommender.py`
- Modify: `dashboard/app.py` (remove `_sidebar`, `_main`, `_colophon`, `_update`, `_reset`, `_toggle_sidebar`, layout — they all move)

- [ ] **Step 13.1: Create the empty marker file**

```powershell
New-Item -ItemType Directory -Force dashboard\pages | Out-Null
New-Item -ItemType File dashboard\pages\__init__.py | Out-Null
```

- [ ] **Step 13.2: Create `dashboard/pages/recommender.py`** with the page registration and *all* moved code:

```python
"""The recommender (and home) page: /. The bulk of the existing layout
lives here so Dash Pages can register it cleanly."""
from __future__ import annotations

import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, dash_table, dcc, html

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.recommender import TASTE_COLS, explain, load_catalog, recommend  # noqa: E402
from dashboard.components.masthead import masthead  # noqa: E402

dash.register_page(__name__, path="/", title="The Beer Predictor")

CATALOG = load_catalog()
STYLES = sorted(CATALOG["style"].dropna().unique().tolist())
COUNTRIES = sorted(CATALOG["country"].dropna().unique().tolist())
ABV_MIN = float(CATALOG["abv"].min())
ABV_MAX = float(CATALOG["abv"].max())

SLIDER_AXES = [
    ("bitterness", "Bitter", "How sharp / hop-bitter you want it"),
    ("sweetness", "Sweet", "Caramel, residual sugar, malt sweetness"),
    ("maltiness", "Malty", "Bread, biscuit, toast, dark crystal"),
    ("hoppiness", "Hoppy", "Hop aroma + flavour intensity"),
    ("body", "Body", "Mouthfeel from light/crisp to thick/chewy"),
    ("sourness", "Sour", "Tart / acidic / Brettanomyces character"),
    ("abv_preference", "Strength", "Session beer (0) → barleywine (10)"),
]

# Palette (kept identical to the prior single-file app).
PAPER, PAPER_DEEP = "#F1E8D3", "#E6DABB"
INK, INK_SOFT = "#1A1410", "#4A382A"
COPPER, COPPER_DIM = "#B0651E", "#8A4E16"
OXBLOOD = "#6B1F1F"
HAIRLINE = "rgba(26,20,16,0.20)"
SERIF_STACK = '"Newsreader", "Fraunces", Georgia, "Times New Roman", serif'
MONO_STACK = '"IBM Plex Mono", "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace'


# --- copied verbatim from the prior dashboard/app.py ---

def _slider(key: str, label: str, tooltip: str, initial: float = 5.0) -> html.Div:
    return html.Div(
        [
            html.Div(
                [html.Span(label), html.Span("info", id=f"tt-{key}", className="tip")],
                className="axis-label",
            ),
            dbc.Tooltip(tooltip, target=f"tt-{key}", placement="right"),
            dcc.Slider(
                id=f"slider-{key}",
                min=0, max=10, step=0.5, value=initial,
                marks={0: "0", 5: "5", 10: "10"},
                tooltip={"placement": "bottom", "always_visible": False},
            ),
        ],
        className="axis-row",
    )


def _sidebar(initial_values: dict | None = None) -> html.Div:
    iv = initial_values or {}
    sliders = [_slider(k, lab, tip, iv.get(k, 5.0)) for (k, lab, tip) in SLIDER_AXES]
    body = html.Div(
        [
            html.Div("Profile / vii axes", className="section-label"),
            html.Div(sliders, className="stagger"),
            html.Div("Filters", className="section-label"),
            html.Div(
                [
                    html.Div([html.Span("ABV range"), html.Span("% v/v", className="tip")], className="axis-label"),
                    dcc.RangeSlider(
                        id="flt-abv", min=0, max=14, step=0.5, value=[0, 14],
                        marks={0: "0", 5: "5", 10: "10", 14: "14"},
                        tooltip={"placement": "bottom"},
                    ),
                ],
                className="axis-row",
            ),
            html.Div(
                [
                    html.Div([html.Span("Styles"), html.Span("multi", className="tip")], className="axis-label"),
                    dcc.Dropdown(
                        id="flt-styles",
                        options=[{"label": s, "value": s} for s in STYLES],
                        value=[], multi=True, clearable=True, placeholder="any style",
                    ),
                ],
                className="axis-row",
            ),
            html.Div(
                [
                    html.Div([html.Span("Countries"), html.Span("multi", className="tip")], className="axis-label"),
                    dcc.Dropdown(
                        id="flt-countries",
                        options=[{"label": c, "value": c} for c in COUNTRIES],
                        value=[], multi=True, clearable=True, placeholder="any country",
                    ),
                ],
                className="axis-row",
            ),
            html.Div(
                [
                    html.Div([html.Span("Results"), html.Span("3 – 20", className="tip")], className="axis-label"),
                    dcc.Slider(
                        id="flt-topk", min=3, max=20, step=1, value=10,
                        marks={3: "3", 10: "10", 20: "20"},
                        tooltip={"placement": "bottom"},
                    ),
                ],
                className="axis-row",
            ),
            html.Div(style={"height": "1.4rem"}),
            html.Button("Reset profile", id="btn-reset", n_clicks=0, className="ink-btn"),
        ],
        id="sidebar-body",
        className="sidebar-body",
    )
    toggle = html.Button(
        [
            html.Span("Profile · tap to adjust", className="sidebar-summary"),
            html.Span("▾", className="sidebar-chevron"),
        ],
        id="btn-toggle-sidebar", n_clicks=0, className="sidebar-toggle",
    )
    return html.Aside([toggle, body], id="tasting-card", className="tasting-card")


def _main() -> html.Div:
    return html.Main(
        [
            html.Div(
                [
                    html.Div("No. 01 — Tonight's Pour", className="article-no"),
                    html.H2("A glass, suggested."),
                    html.P(
                        "Beers ranked by Euclidean distance over a seven-axis "
                        "taste vector. Match score is 100 × (1 / (1 + distance)) "
                        "— closer to your profile, higher the score.",
                        className="dek",
                    ),
                ],
                className="feature-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div([html.Span("Fig. I"), html.Span("Your profile")], className="chart-caption"),
                            dcc.Loading(
                                dcc.Graph(id="profile-radar",
                                          config={"displayModeBar": False, "responsive": True},
                                          style={"height": "360px"},
                                          className="radar-graph"),
                                color=COPPER, type="default",
                            ),
                        ],
                        className="chart-card",
                    ),
                    html.Div(
                        [
                            html.Div([html.Span("Fig. II"), html.Span("You vs. top 3")], className="chart-caption"),
                            dcc.Loading(
                                dcc.Graph(id="comparison-radar",
                                          config={"displayModeBar": False, "responsive": True},
                                          style={"height": "360px"},
                                          className="radar-graph"),
                                color=COPPER, type="default",
                            ),
                        ],
                        className="chart-card",
                    ),
                ],
                className="charts-row",
            ),
            html.Section(
                [
                    html.Div(
                        [
                            html.H3("The Ledger"),
                            html.Span("Sorted · highest match first", className="legend"),
                        ],
                        className="ledger-head",
                    ),
                    dcc.Loading(
                        html.Div(id="reco-table-container", className="ledger"),
                        color=COPPER, type="default",
                    ),
                ],
                className="ledger-section",
            ),
        ],
        className="feature",
    )


def _colophon() -> html.Div:
    return html.Div(
        [
            html.Span("Set in Fraunces, Newsreader & IBM Plex Mono"),
            html.Span("Printed on cream, in copper ink"),
        ],
        className="colophon",
    )


def layout(**_kwargs):
    return html.Div([
        masthead(),
        html.Div([_sidebar(), _main()], className="spread"),
        _colophon(),
    ])


# --- callbacks (copied verbatim) ---
SLIDER_IDS = [f"slider-{k}" for k, _, _ in SLIDER_AXES]


@callback(
    Output("profile-radar", "figure"),
    Output("comparison-radar", "figure"),
    Output("reco-table-container", "children"),
    [Input(s_id, "value") for s_id in SLIDER_IDS]
    + [Input("flt-abv", "value"), Input("flt-styles", "value"),
       Input("flt-countries", "value"), Input("flt-topk", "value")],
)
def _update(*values):
    *slider_values, abv_range, styles, countries, top_k = values
    profile = {k: float(v) for (k, _, _), v in zip(SLIDER_AXES, slider_values)}
    filters: dict[str, object] = {"min_abv": abv_range[0], "max_abv": abv_range[1]}
    if styles:
        filters["styles"] = styles
    if countries:
        filters["countries"] = countries
    recos = recommend(profile, top_k=int(top_k or 10), filters=filters)
    return _profile_radar(profile), _comparison_radar(profile, recos), _reco_table(recos, profile)


def _radar_layout(_title_text: str, *, legend: bool = False) -> dict:
    return dict(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 10], showticklabels=True, tickvals=[2,4,6,8,10],
                            tickfont=dict(family=MONO_STACK, size=9, color=INK_SOFT),
                            gridcolor=HAIRLINE, gridwidth=1,
                            linecolor="rgba(0,0,0,0)", tickangle=45),
            angularaxis=dict(tickfont=dict(family=MONO_STACK, size=10, color=INK),
                             gridcolor=HAIRLINE, linecolor=INK, linewidth=1,
                             rotation=90, direction="clockwise"),
        ),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18,
                    xanchor="center", x=0.5,
                    font=dict(family=SERIF_STACK, size=11, color=INK),
                    bgcolor="rgba(0,0,0,0)"),
        title=dict(text="", font=dict(size=1)),
        margin=dict(l=25, r=25, t=20, b=55 if legend else 25),
        autosize=True, font=dict(family=SERIF_STACK, color=INK),
    )


def _profile_radar(profile: dict) -> go.Figure:
    cats = ["Bitter","Sweet","Malty","Hoppy","Body","Sour","Strength"]
    keys = ["bitterness","sweetness","maltiness","hoppiness","body","sourness","abv_preference"]
    vals = [profile.get(k, 5.0) for k in keys]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]], fill="toself", name="You",
        line=dict(color=COPPER, width=2.5),
        fillcolor="rgba(176,101,30,0.22)",
        marker=dict(size=6, color=COPPER, line=dict(color=INK, width=1)),
        hovertemplate="<b>%{theta}</b>  %{r:.1f}<extra></extra>",
    ))
    fig.update_layout(**_radar_layout("Your profile", legend=False))
    return fig


def _comparison_radar(profile: dict, recos: pd.DataFrame) -> go.Figure:
    cats = ["Bitter","Sweet","Malty","Hoppy","Body","Sour","Strength"]
    keys = ["bitterness","sweetness","maltiness","hoppiness","body","sourness","abv_preference"]
    profile_vals = [profile.get(k, 5.0) for k in keys]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=profile_vals + [profile_vals[0]], theta=cats + [cats[0]], fill="toself",
        name="You", line=dict(color=INK, width=1.5, dash="dot"),
        fillcolor="rgba(26,20,16,0.06)",
        hovertemplate="<b>You · %{theta}</b>  %{r:.1f}<extra></extra>",
    ))
    palette = [COPPER, OXBLOOD, INK_SOFT]
    for i, (_, r) in enumerate(recos.head(3).iterrows()):
        beer_vals = [
            float(r["bitterness"]), float(r["sweetness"]), float(r["maltiness"]),
            float(r["hoppiness"]), float(r["body"]), float(r["sourness"]),
            float(r["abv_normalized"]),
        ]
        name = str(r["name"])[:28]
        fig.add_trace(go.Scatterpolar(
            r=beer_vals + [beer_vals[0]], theta=cats + [cats[0]], name=name,
            line=dict(color=palette[i % len(palette)], width=2),
            marker=dict(size=4, color=palette[i % len(palette)]),
            hovertemplate=f"<b>{name} · %{{theta}}</b>  %{{r:.1f}}<extra></extra>",
        ))
    fig.update_layout(**_radar_layout("You vs. top 3", legend=True))
    return fig


def _reco_table(recos: pd.DataFrame, profile: dict) -> html.Div:
    if recos.empty:
        return dbc.Alert(
            "No beers in the cellar match those filters. Loosen the ABV range, or strike a style.",
            color="warning",
        )
    rows, cards = [], []
    for rank, (_, r) in enumerate(recos.iterrows(), start=1):
        rank_str = f"{rank:02d}"
        name = r["name"]; brewery = r["brewery"]; style = r["style"]; country = r["country"]
        abv = f"{float(r['abv']):.1f}%"
        ibu = f"{int(round(float(r['ibu'])))}"
        match = f"{float(r['match_score']):.1f}"
        why = explain(r, profile)
        rows.append({
            "Rank": rank_str, "Beer": name, "Brewery": brewery, "Style": style,
            "Country": country, "ABV": abv,
            "IBU": f"{int(round(float(r['ibu']))):>3d}",
            "Match": match, "Why": why,
        })
        cards.append(html.Article(
            [
                html.Div([html.Span(f"№ {rank_str}", className="lc-rank"),
                          html.Span(f"Match · {match}", className="lc-match")],
                         className="lc-top"),
                html.H4(name, className="lc-name"),
                html.Div(brewery, className="lc-brewery"),
                html.Div(f"{style} · {country} · {abv} · IBU {ibu}", className="lc-meta"),
                html.Div(why, className="lc-why"),
            ],
            className="ledger-card" + (" first" if rank == 1 else ""),
        ))
    table = dash_table.DataTable(
        data=rows,
        columns=[
            {"name": "№", "id": "Rank"}, {"name": "Beer", "id": "Beer"},
            {"name": "Brewery", "id": "Brewery"}, {"name": "Style", "id": "Style"},
            {"name": "Country", "id": "Country"}, {"name": "ABV", "id": "ABV"},
            {"name": "IBU", "id": "IBU"}, {"name": "Match", "id": "Match"},
            {"name": "Notes", "id": "Why"},
        ],
        sort_action="native", page_action="none",
        style_table={"overflowX": "auto", "border": "0"},
        style_as_list_view=True,
        style_cell={"fontFamily": SERIF_STACK, "fontSize": "0.95rem",
                    "textAlign": "left", "padding": "0.55rem 0.6rem",
                    "whiteSpace": "normal", "height": "auto",
                    "backgroundColor": "transparent", "color": INK, "border": "0"},
        style_header={"backgroundColor": "transparent", "fontWeight": 600,
                      "color": INK, "fontFamily": MONO_STACK,
                      "fontSize": "0.66rem", "letterSpacing": "0.2em",
                      "textTransform": "uppercase",
                      "borderTop": f"1px solid {INK}",
                      "borderBottom": f"1px solid {INK}"},
        style_cell_conditional=[
            {"if": {"column_id": "Rank"},
             "fontFamily": '"Fraunces", Georgia, serif', "fontSize": "1.4rem",
             "fontWeight": 800, "color": COPPER, "width": "3rem",
             "textAlign": "left",
             "fontVariantNumeric": "lining-nums tabular-nums"},
            {"if": {"column_id": "Beer"}, "fontWeight": 600, "fontSize": "1.02rem"},
            {"if": {"column_id": "Brewery"}, "fontStyle": "italic", "color": INK_SOFT},
            {"if": {"column_id": "Style"}, "fontFamily": MONO_STACK,
             "fontSize": "0.78rem", "textTransform": "uppercase",
             "letterSpacing": "0.08em", "color": INK_SOFT},
            {"if": {"column_id": "Country"}, "fontFamily": MONO_STACK,
             "fontSize": "0.78rem", "color": INK_SOFT},
            {"if": {"column_id": "ABV"}, "fontFamily": MONO_STACK,
             "fontSize": "0.85rem", "fontVariantNumeric": "tabular-nums",
             "color": INK, "width": "4rem"},
            {"if": {"column_id": "IBU"}, "fontFamily": MONO_STACK,
             "fontSize": "0.85rem", "fontVariantNumeric": "tabular-nums",
             "color": INK_SOFT, "width": "3.5rem"},
            {"if": {"column_id": "Match"}, "fontFamily": MONO_STACK,
             "fontSize": "0.95rem", "fontWeight": 600,
             "fontVariantNumeric": "tabular-nums", "color": COPPER, "width": "4.5rem"},
            {"if": {"column_id": "Why"}, "fontStyle": "italic",
             "color": INK_SOFT, "fontSize": "0.88rem", "maxWidth": "32rem"},
        ],
        style_data_conditional=[
            {"if": {"row_index": 0}, "backgroundColor": "rgba(176,101,30,0.06)"},
        ],
    )
    return html.Div([
        html.Div(table, className="ledger-table-view"),
        html.Div(cards, className="ledger-card-view"),
    ])


@callback(
    [Output(s_id, "value") for s_id in SLIDER_IDS],
    Input("btn-reset", "n_clicks"),
    prevent_initial_call=True,
)
def _reset(_n):
    return [5.0] * len(SLIDER_IDS)


@callback(
    Output("tasting-card", "className"),
    Input("btn-toggle-sidebar", "n_clicks"),
    prevent_initial_call=True,
)
def _toggle_sidebar(n_clicks):
    if n_clicks and n_clicks % 2 == 1:
        return "tasting-card collapsed"
    return "tasting-card"
```

- [ ] **Step 13.3: Slim down `dashboard/app.py`** to bootstrap only:

```python
"""Beer Predictor — Dash dashboard bootstrap.

Run with:
    python dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import dash
import dash_bootstrap_components as dbc

_DIR = Path(__file__).resolve().parent
ROOT = _DIR.parent
for p in (str(ROOT), str(_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.config import load_settings  # noqa: E402
from dashboard.auth_routes import auth_bp  # noqa: E402

_SETTINGS = load_settings()

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="The Beer Predictor — A Taste-Profile Broadsheet",
    meta_tags=[
        {"name": "viewport",
         "content": "width=device-width, initial-scale=1, viewport-fit=cover"},
    ],
)
server = app.server
server.secret_key = _SETTINGS.flask_secret_key
server.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
)
server.register_blueprint(auth_bp)

app.index_string = """<!DOCTYPE html>
<html lang="en">
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,800;9..144,900&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    {%css%}
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>"""

# With use_pages=True, app.layout is implicitly the page container.
# A `dash.page_container` shows the active page's layout.
from dash import html  # noqa: E402
app.layout = html.Div([dash.page_container])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)
```

- [ ] **Step 13.4: Smoke-run the dashboard**

```powershell
uv run python dashboard/app.py
```

Expected: opens on `:8050`; `/` renders the recommender exactly as before; auth links still work. Ctrl-C when verified.

- [ ] **Step 13.5: Re-run all tests**

```powershell
uv run pytest tests/ -v
```

Expected: still green.

---

## Task 14: Personalized slider defaults on load

Wire `personalized_defaults()` into `_sidebar()` so signed-in users see their personalized starting position.

**Files:**
- Modify: `dashboard/pages/recommender.py`

- [ ] **Step 14.1: Add a `_fetch_my_ratings()` helper and update `layout()`** in `dashboard/pages/recommender.py`.

Near the top imports, add:

```python
from src.db import user_client
from src import auth as A
from src.personalization import personalized_defaults
```

Just below the existing palette constants, add:

```python
def _fetch_my_ratings() -> list[dict]:
    """Return the signed-in user's rated beers, or [] if anon / error."""
    if not A.current_user_id():
        return []
    client = user_client()
    if client is None:
        return []
    try:
        resp = client.table("user_beers").select("beer_id, rating").execute()
        return list(resp.data or [])
    except Exception:
        return []


def _initial_slider_values() -> dict:
    defaults = personalized_defaults(_fetch_my_ratings(), CATALOG)
    return defaults or {}
```

Replace the existing `layout` function:

```python
def layout(**_kwargs):
    return html.Div([
        masthead(),
        html.Div([_sidebar(_initial_slider_values()), _main()], className="spread"),
        _colophon(),
    ])
```

- [ ] **Step 14.2: Smoke-run and verify**

```powershell
uv run python dashboard/app.py
```

Expected when anon: sliders default to 5.0 (today's behavior). When signed in with no ratings yet: also 5.0. After Task 15 lands and you've rated some beers ≥4★: sliders open at the personalized vector.

---

## Task 15: Rating dropdown control in the ledger + upsert callback

We add a rating dropdown to each ledger row (both table and card views), wire a pattern-matched callback to upsert into `user_beers`, and show a small toast. For anon users, the dropdowns render disabled with a tooltip.

**Files:**
- Modify: `dashboard/pages/recommender.py` (replace `_reco_table` body; add new callback)

- [ ] **Step 15.1: Replace the `_reco_table` function**

Replace the existing `_reco_table(...)` in `dashboard/pages/recommender.py` with a version that drops the DataTable (which can't host interactive dropdowns) and uses cards only. The card view already exists below the table — we promote it to the only view.

Find the start of `def _reco_table(recos, profile)` and replace through the `return html.Div([...])` at the end with:

```python
def _rating_options() -> list[dict]:
    """Half-star scale: 0.5 → 5.0."""
    return [
        {"label": f"{v:g} ★", "value": v}
        for v in [0.5,1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0]
    ]


def _rating_control(beer_id: str, current: float | None,
                    signed_in: bool) -> html.Div:
    if not signed_in:
        return html.Div(
            [
                dcc.Dropdown(
                    id={"role": "rate-disabled", "beer_id": beer_id},
                    options=_rating_options(), value=None,
                    placeholder="sign in to rate", disabled=True,
                    clearable=False, style={"width": "9rem"},
                ),
                dbc.Tooltip(
                    "Sign in to log and rate this beer.",
                    target={"role": "rate-disabled", "beer_id": beer_id},
                    placement="left",
                ),
            ],
            className="lc-rate",
        )
    return html.Div(
        [
            dcc.Dropdown(
                id={"role": "rate", "beer_id": beer_id},
                options=_rating_options(), value=current,
                placeholder="rate", clearable=True,
                style={"width": "9rem"},
            ),
            html.Span(
                "✓" if current else "",
                id={"role": "rate-tick", "beer_id": beer_id},
                className="lc-rate-tick",
            ),
        ],
        className="lc-rate",
    )


def _reco_table(recos: pd.DataFrame, profile: dict) -> html.Div:
    if recos.empty:
        return dbc.Alert(
            "No beers in the cellar match those filters. Loosen the ABV range, or strike a style.",
            color="warning",
        )
    signed_in = A.current_user_id() is not None
    my_ratings = {r["beer_id"]: float(r["rating"]) for r in _fetch_my_ratings()}

    cards = []
    for rank, (_, r) in enumerate(recos.iterrows(), start=1):
        rank_str = f"{rank:02d}"
        beer_id = r["beer_id"]
        name = r["name"]; brewery = r["brewery"]; style = r["style"]
        country = r["country"]
        abv = f"{float(r['abv']):.1f}%"
        ibu = f"{int(round(float(r['ibu'])))}"
        match = f"{float(r['match_score']):.1f}"
        why = explain(r, profile)
        cards.append(html.Article(
            [
                html.Div([html.Span(f"№ {rank_str}", className="lc-rank"),
                          html.Span(f"Match · {match}", className="lc-match")],
                         className="lc-top"),
                html.H4(name, className="lc-name"),
                html.Div(brewery, className="lc-brewery"),
                html.Div(f"{style} · {country} · {abv} · IBU {ibu}", className="lc-meta"),
                html.Div(why, className="lc-why"),
                _rating_control(beer_id, my_ratings.get(beer_id), signed_in),
            ],
            className="ledger-card" + (" first" if rank == 1 else ""),
        ))
    return html.Div(cards, className="ledger-card-view")
```

(The DataTable view is intentionally dropped; the cards already had identical content and now host the rating controls cleanly. If the user wants the table view back later, it's a follow-on enhancement. The "✓" tick mark next to the rating dropdown is the feedback that the save worked — no toast component needed.)

- [ ] **Step 15.2: Add the pattern-matched callback** at the bottom of `dashboard/pages/recommender.py`:

```python
from dash import ALL, MATCH, ctx, no_update  # noqa: E402

@callback(
    Output({"role": "rate-tick", "beer_id": MATCH}, "children"),
    Input({"role": "rate", "beer_id": MATCH}, "value"),
    prevent_initial_call=True,
)
def _save_rating(value):
    triggered = ctx.triggered_id
    if not triggered or "beer_id" not in triggered:
        return no_update
    beer_id = triggered["beer_id"]
    client = user_client()
    if client is None:
        return no_update  # silently no-op for anon; the dropdown is disabled anyway
    uid = A.current_user_id()
    if uid is None:
        return no_update
    try:
        if value is None:
            client.table("user_beers").delete().eq("user_id", uid).eq("beer_id", beer_id).execute()
            return ""
        else:
            client.table("user_beers").upsert(
                {"user_id": uid, "beer_id": beer_id, "rating": float(value)},
                on_conflict="user_id,beer_id",
            ).execute()
            return "✓"
    except Exception:
        return no_update
```

- [ ] **Step 15.3: Smoke-run + manual rating**

```powershell
uv run python dashboard/app.py
```

  - Anon: ledger renders; rating dropdowns visibly disabled with tooltip on hover.
  - Sign in: rating dropdowns enabled; pick 5★ on three IPAs.
  - Refresh `/`: sliders shift toward bitter / hoppy (Task 14 picks this up).
  - Re-open the page anonymously (incognito): sliders back to 5.0.

---

## Task 16: `/profile` page

**Files:**
- Create: `dashboard/pages/profile.py`

- [ ] **Step 16.1: Create `dashboard/pages/profile.py`**:

```python
"""User profile page: /profile.

Sections:
  - Editable display_name
  - Personalized radar (Fig. III) — current personalized defaults
  - Ledger of rated beers (sortable, with Remove action)
"""
from __future__ import annotations

import sys
from pathlib import Path

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, dcc, html, no_update

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.recommender import load_catalog
from src.db import user_client
from src import auth as A
from src.personalization import personalized_defaults
from dashboard.components.masthead import masthead
from dashboard.pages.recommender import (
    _colophon, _radar_layout, COPPER, INK, OXBLOOD, SERIF_STACK,
)

dash.register_page(__name__, path="/profile", title="Profile · The Beer Predictor")
CATALOG = load_catalog()


def _personalized_radar(profile: dict | None) -> go.Figure:
    cats = ["Bitter","Sweet","Malty","Hoppy","Body","Sour","Strength"]
    keys = ["bitterness","sweetness","maltiness","hoppiness","body","sourness","abv_preference"]
    vals = [profile.get(k, 5.0) for k in keys] if profile else [5.0]*7
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]], fill="toself",
        name="Your taste", line=dict(color=COPPER, width=2.5),
        fillcolor="rgba(176,101,30,0.22)",
        marker=dict(size=6, color=COPPER, line=dict(color=INK, width=1)),
        hovertemplate="<b>%{theta}</b>  %{r:.1f}<extra></extra>",
    ))
    fig.update_layout(**_radar_layout("Your taste", legend=False))
    return fig


def _fetch_profile_and_ratings():
    client = user_client()
    if client is None:
        return None, []
    uid = A.current_user_id()
    if uid is None:
        return None, []
    try:
        prof = client.table("profiles").select("display_name").eq("id", uid).single().execute().data
        ratings = client.table("user_beers").select("beer_id, rating, rated_at").execute().data or []
        return prof, ratings
    except Exception:
        return None, []


def _ledger_table(ratings: list[dict], catalog: pd.DataFrame) -> html.Div:
    if not ratings:
        return html.Div("Rate a few beers to populate your ledger.", className="lc-empty")
    cat_by_id = catalog.set_index("beer_id")
    rows = []
    for r in sorted(ratings, key=lambda x: x.get("rated_at", ""), reverse=True):
        bid = r["beer_id"]
        if bid not in cat_by_id.index:
            continue
        c = cat_by_id.loc[bid]
        rows.append(html.Tr([
            html.Td(c["name"]),
            html.Td(c["brewery"]),
            html.Td(c["style"]),
            html.Td(f"★ {float(r['rating']):g}"),
            html.Td(html.Button("Remove",
                                id={"role": "prof-remove", "beer_id": bid},
                                n_clicks=0, className="linkish")),
        ]))
    return html.Table(
        [
            html.Thead(html.Tr([html.Th("Beer"), html.Th("Brewery"),
                                html.Th("Style"), html.Th("Rating"), html.Th("")])),
            html.Tbody(rows),
        ],
        className="profile-ledger",
    )


def layout(**_kwargs):
    if not A.current_user_id():
        return html.Div([
            masthead(),
            html.Main(
                html.Div(
                    [html.H2("Sign in to view your profile."),
                     html.A("Sign in", href="/auth/login", className="ink-btn")],
                    className="profile-gate"),
                className="feature"),
            _colophon(),
        ])
    prof, ratings = _fetch_profile_and_ratings()
    display_name = (prof or {}).get("display_name", "")
    defaults = personalized_defaults(ratings, CATALOG)

    return html.Div([
        masthead(),
        html.Main(
            [
                html.Div([
                    html.Div("No. 02 — Reader's Card", className="article-no"),
                    html.H2("Your profile."),
                    html.P(
                        "Edit your display name. Watch your personalized "
                        "taste profile form as you rate.",
                        className="dek"),
                ], className="feature-header"),

                html.Section(
                    [
                        html.Label("Display name", htmlFor="prof-name"),
                        dcc.Input(id="prof-name", type="text", value=display_name,
                                  maxLength=50, className="prof-name-input"),
                        html.Button("Save", id="prof-name-save",
                                    n_clicks=0, className="ink-btn"),
                        html.Span("", id="prof-name-status", className="prof-status"),
                    ],
                    className="profile-name-section",
                ),

                html.Section(
                    [
                        html.Div([html.Span("Fig. III"),
                                  html.Span("Personalized profile")],
                                 className="chart-caption"),
                        dcc.Graph(
                            figure=_personalized_radar(defaults),
                            config={"displayModeBar": False, "responsive": True},
                            style={"height": "360px"},
                            className="radar-graph",
                        ),
                        (html.Div("Rate beers ≥ 4★ to populate this.",
                                  className="lc-aside")
                         if defaults is None else None),
                    ],
                    className="chart-card",
                ),

                html.Section(
                    [
                        html.H3("Your ledger"),
                        html.Div(_ledger_table(ratings, CATALOG), id="prof-ledger"),
                    ],
                    className="ledger-section",
                ),
            ],
            className="feature",
        ),
        _colophon(),
    ])


@callback(
    Output("prof-name-status", "children"),
    Input("prof-name-save", "n_clicks"),
    State("prof-name", "value"),
    prevent_initial_call=True,
)
def _save_display_name(_n, name):
    name = (name or "").strip()
    if not (1 <= len(name) <= 50):
        return "Name must be 1–50 chars."
    client = user_client()
    uid = A.current_user_id()
    if client is None or uid is None:
        return "Sign in first."
    try:
        client.table("profiles").update({"display_name": name}).eq("id", uid).execute()
        return "Saved."
    except Exception as e:  # noqa: BLE001
        return f"Save failed: {e}"


@callback(
    Output("prof-ledger", "children"),
    Input({"role": "prof-remove", "beer_id": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def _remove(_n_clicks_list):
    triggered = ctx.triggered_id
    if not triggered or "beer_id" not in triggered:
        return no_update
    if not any(_n_clicks_list or []):
        return no_update
    client = user_client()
    uid = A.current_user_id()
    if client is None or uid is None:
        return no_update
    try:
        client.table("user_beers").delete().eq("user_id", uid).eq("beer_id", triggered["beer_id"]).execute()
    except Exception:
        return no_update
    _, ratings = _fetch_profile_and_ratings()
    return _ledger_table(ratings, CATALOG)
```

- [ ] **Step 16.2: Smoke-run + manually verify all profile features**

```powershell
uv run python dashboard/app.py
```

Anon → `/profile` shows the gate (sign-in CTA). Signed in → display name editable + Save returns "Saved." + radar shows the personalized profile (or the aside if no ≥4★ ratings yet) + ledger lists rated beers with working Remove buttons.

---

## Task 17: Final integration + regression sweep

- [ ] **Step 17.1: Full test suite**

```powershell
uv run pytest tests/ -v
```

Expected: all green.

- [ ] **Step 17.2: Manual integration test plan**

Walk through all eight items from the spec's manual test plan, in order:

  1. Anon: load `/` → recommender works as today; rating dropdowns disabled with tooltip.
  2. Sign up new user → check Inbucket / real inbox → click confirm → land back signed in.
  3. Sign out → masthead shows anon links.
  4. Sign in existing user → masthead shows display name.
  5. Rate three IPAs at 4–5★ → reload `/` → sliders lean hoppy/bitter.
  6. Open `/profile` → display_name editable; rated beers listed; Fig. III shows personalized radar.
  7. Forgot password → reset email → set new password → log in with new password.
  8. Existing `tests/` suite still green.

- [ ] **Step 17.3: Re-run advisors on Supabase**

Via MCP `get_advisors` `type="security"` and `type="performance"`. Expected: clean. If anything regressed (e.g. policy missing), add the fix to a new migration file before considering the feature done.

- [ ] **Step 17.4: Add a "Supabase" section to the README**

Append a short section to `README.md` covering: env vars required, link to `.env.example`, how to apply migrations (`supabase/migrations/`), and a note that the recommender still works fully anonymously.

---

## Done

When all 17 tasks complete and the manual test plan passes, the feature is shippable for local use. The deploy story (env in production, HTTPS, `SESSION_COOKIE_SECURE=True`, Supabase prod redirect URLs) is the next follow-on but is intentionally out of this spec's scope.
