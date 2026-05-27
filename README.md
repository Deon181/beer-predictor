# Beer Predictor

A Dash app that recommends beers based on a 7-axis taste-profile slider:
**bitterness, sweetness, maltiness, hoppiness, body, sourness, ABV preference**.
Recommendations are content-based — Euclidean distance from your profile to
each beer's engineered taste vector, with optional filters on ABV range,
style, and country.

![placeholder — drop a screenshot here](docs/screenshot.png)

## Dataset

The catalog is a ~560-beer subset of [OpenBeerDB][obdb] (a public catalog
of ~7,700 beers across 1,400+ breweries in 50+ countries), selected by
stratified sampling for breadth across style and country. Each row carries
name, brewery, style, country, ABV, IBU, and SRM. Style baselines for the
taste-vector attributes come from the [BJCP 2021 Style Guidelines][bjcp]
(publicly available; only factual style descriptors are referenced — no
copyrighted prose is reproduced).

[obdb]: https://openbeerdb.com
[bjcp]: https://www.bjcp.org/style/2021/

The pipeline:

1. `scripts/fetch_obdb.py` downloads OBDB raw CSVs to `data/raw/obdb/`,
   pinned to a specific commit for reproducibility.
2. `scripts/build_catalog.py` joins OBDB beers/breweries/styles, drops
   rows missing required fields, maps OBDB style names to BJCP keys via
   `src/style_aliases.py`, and stratified-samples down to ~560 rows with
   per-country / per-style / per-cell caps. Writes
   `data/raw/curated_beers.csv` and a `data/raw/coverage_report.md`
   summary.
3. `notebooks/data_prep.ipynb` engineers the 7-axis taste vector and
   writes `data/processed/beers.parquet`.

**Manual supplements:** Beers that aren't in OpenBeerDB (e.g., the 25
South African beers — Castle Lager, Devil's Peak King's Blockhouse IPA,
etc.) live in `data/raw/supplemental_beers.csv`. `build_catalog.py`
always appends this file to the sampled catalog before writing
`curated_beers.csv`, so manual additions persist through every pipeline
rebuild. Adding a beer is a one-line CSV edit — the file header shows
the required columns (`name, brewery, style, country, abv, ibu, srm`),
and any unknown style fails validation loudly.

**Attribution:** Contains information from [OpenBeerDB](https://openbeerdb.com),
made available under the [Open Database License (ODbL)][odbl]. The derived
`curated_beers.csv` is a database derivative and is shared under the same
terms. See `data/raw/obdb/ATTRIBUTION.md` for the full notice.

[odbl]: https://opendatacommons.org/licenses/odbl/

## Layout

```
beer-predictor/
├─ data/
│  ├─ raw/
│  │  ├─ obdb/                       # OpenBeerDB snapshot + ATTRIBUTION
│  │  ├─ supplemental_beers.csv      # manually curated beers (e.g., SA)
│  │  ├─ curated_beers.csv           # final catalog (sample ∪ supplements)
│  │  └─ coverage_report.md          # country/style distribution
│  └─ processed/beers.parquet        # built by the data_prep notebook
├─ notebooks/
│  └─ data_prep.ipynb                # cleans + engineers the taste vector
├─ src/
│  ├─ style_attributes.py            # BJCP-derived style → taste mapping
│  ├─ style_aliases.py               # OBDB style name → BJCP key
│  └─ recommender.py                 # load_catalog, recommend, explain
├─ dashboard/
│  └─ app.py                         # Dash UI
├─ tests/
│  ├─ test_recommender.py
│  ├─ test_data_prep.py
│  ├─ test_style_aliases.py
│  └─ test_catalog.py
├─ scripts/
│  ├─ fetch_obdb.py                  # downloads OpenBeerDB raw data
│  └─ build_catalog.py               # builds data/raw/curated_beers.csv from OBDB
├─ pyproject.toml
└─ README.md
```

## Run it

Requirements: Python 3.13 and [`uv`](https://docs.astral.sh/uv/).

```bash
# 1. Install deps
uv sync

# 2. Fetch OpenBeerDB raw data + build the sampled catalog
uv run python scripts/fetch_obdb.py
uv run python scripts/build_catalog.py

# 3. Engineer the taste vector (writes data/processed/beers.parquet)
uv run jupyter nbconvert --to notebook --execute \
    --inplace notebooks/data_prep.ipynb

# 4. Launch the dashboard
uv run python dashboard/app.py
# then open http://127.0.0.1:8050
```

## Tests

```bash
uv run pytest tests/ -v
```

Covers: catalog schema, taste-vector ranges, distance symmetry, top-k
ordering, filter behaviour, the `explain()` output, the slug `beer_id`
contract, the env-driven `Settings` loader, the Supabase client
factories (mocked), the auth helpers (mocked), and `personalized_defaults`.

## Supabase (accounts, ratings, personalization)

Sign-in is optional — the recommender works fully anonymously. Signing
in unlocks beer ratings and seeds your slider defaults from beers you've
rated ≥4★.

### Configure once

Copy `.env.example` to `.env` and fill in:

- `SUPABASE_URL` — your project URL (Supabase dashboard → Project Settings → API)
- `SUPABASE_PUBLISHABLE_KEY` — your `sb_publishable_…` key
  (Project Settings → API Keys → "Publishable keys")
- `FLASK_SECRET_KEY` — `python -c "import secrets; print(secrets.token_hex(32))"`

In the Supabase dashboard:

- Authentication → Providers → Email: enabled, "Confirm email" ON
- Authentication → URL Configuration:
  - Site URL: `http://127.0.0.1:8050`
  - Additional Redirect URLs: `http://127.0.0.1:8050/auth/callback`

### Apply migrations

The schema lives in `supabase/migrations/` (two files: the initial
schema and the RLS perf optimization). Apply via the Supabase CLI
(`supabase db push`) or, if you've authorised the Supabase MCP server,
via your agent's `apply_migration` tool.

The schema is small: `public.profiles` (1:1 with `auth.users`),
`public.user_beers` (one row per `(user_id, beer_id)`), a trigger that
mirrors new auth users into `profiles`, and RLS policies scoping every
read/write to `auth.uid()`.

## How the recommender works

The taste vector engineered in `notebooks/data_prep.ipynb` puts every
attribute on a 0–10 scale:

- `bitterness` — `clip(IBU / 10, 0, 10)` (IBU 0 → 0, IBU 100 → 10).
- `sweetness`, `maltiness`, `body`, `sourness` — pulled from the BJCP
  style baseline in `src/style_attributes.py`.
- `hoppiness` — blend of style baseline and IBU-derived bitterness:
  `0.5 * style_hop + 0.5 * (IBU / 10)`.
- `abv_normalized` — `clip(ABV / 12 * 10, 0, 10)`.

`recommend(taste_profile, top_k, filters)` computes Euclidean distance
from the user's profile to every (filtered) beer's taste vector, sorts
by `match_score = 100 / (1 + distance)`, and returns the top-`k`.

`explain(beer_row, taste_profile)` returns a one-sentence summary of why
that beer matched — focusing on the axes where the user expressed the
strongest preferences (sliders far from the neutral 5.0).

## Sanity check

With *bitterness=10, hoppiness=10, sweetness=0* the top result is a
hop-forward Imperial IPA / West Coast IPA. With *bitterness=0,
sweetness=10, body=9* it's a Sweet Stout / Doppelbock / Wee Heavy. With
*sourness=10* it's a Berliner Weisse / Gueuze. (See
`tests/test_recommender.py::test_recommend_extreme_*`.)
