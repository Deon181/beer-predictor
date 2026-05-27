# Beer Predictor

A Next.js app that recommends beers based on a 7-axis taste-profile slider:
**bitterness, sweetness, maltiness, hoppiness, body, sourness, ABV preference**.
Recommendations are content-based — Euclidean distance from your profile to
each beer's engineered taste vector, with optional filters on ABV range,
style, and country.

## Stack

- **Frontend:** Next.js 15 (App Router), React, Tailwind CSS v4, Recharts
- **Auth & data:** Supabase (client-side JS SDK)
- **Hosting:** Vercel
- **Data pipeline:** Python (pandas, pyarrow) — runs locally, not deployed

## Dataset

The catalog is a ~588-beer subset of [OpenBeerDB][obdb], enriched with
South African craft beers. Each beer carries a 7-axis taste vector
engineered from IBU, ABV, and BJCP style baselines.

[obdb]: https://openbeerdb.com

The pipeline:

1. `scripts/fetch_obdb.py` — downloads OBDB raw CSVs
2. `scripts/build_catalog.py` — joins, filters, samples, appends supplements
3. `notebooks/data_prep.ipynb` — engineers the taste vector, writes parquet
4. `scripts/export_catalog.py` — converts parquet to `public/data/beers.json`

## Local development

```bash
# Install dependencies
npm install

# Set up environment
cp .env.local.example .env.local
# Fill in your Supabase URL and anon key

# Run the dev server
npm run dev
# Open http://localhost:3000
```

## Data pipeline (Python)

```bash
uv sync
uv run python scripts/fetch_obdb.py
uv run python scripts/build_catalog.py
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/data_prep.ipynb
uv run python scripts/export_catalog.py
```

## Deploy to Vercel

1. Push to GitHub
2. Import the repo in Vercel
3. Set environment variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Deploy

## Supabase setup

- Authentication → Providers → Email: enabled, "Confirm email" ON
- Authentication → URL Configuration:
  - Site URL: your Vercel domain
  - Redirect URLs: `https://your-domain.vercel.app/auth/callback`
- Apply migrations from `supabase/migrations/`

## Attribution

Contains information from [OpenBeerDB](https://openbeerdb.com),
made available under the [Open Database License (ODbL)][odbl].

[odbl]: https://opendatacommons.org/licenses/odbl/
