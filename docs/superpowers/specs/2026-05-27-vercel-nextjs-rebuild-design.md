# Beer Predictor — Next.js Rebuild for Vercel

**Date:** 2026-05-27
**Status:** Approved
**Motivation:** Free/cheap hosting on Vercel's free tier

## Summary

Rebuild the Beer Predictor frontend from Python Dash to Next.js (App Router) with React, Tailwind CSS, and Recharts. The recommender runs entirely client-side in the browser. Auth and ratings use the Supabase JS SDK directly (no Flask/Python server). The existing Python data pipeline stays for catalog generation; a new export script produces a static JSON file the web app consumes.

## Architecture

```
Browser (Next.js React app)
  ├── loads public/data/beers.json (static, CDN-cached)
  ├── recommender logic runs in-browser (TS port)
  ├── Supabase JS SDK for auth + ratings (direct to Supabase)
  └── Recharts for radar visualizations

Vercel
  ├── serves static assets + SSR pages
  └── /auth/callback route handler (code exchange)

Supabase (unchanged)
  ├── Auth (email/password, PKCE)
  ├── profiles table
  ├── user_beers table (ratings)
  └── RLS policies (same schema, same migrations)

Python pipeline (local/CI only, not deployed)
  ├── scripts/fetch_obdb.py
  ├── scripts/build_catalog.py
  ├── notebooks/data_prep.ipynb
  └── scripts/export_catalog.py → public/data/beers.json
```

## Project Structure

```
beer-predictor/
├── app/
│   ├── layout.tsx                # Root layout, fonts, metadata, AuthProvider
│   ├── globals.css               # Tailwind directives + broadsheet tokens + custom CSS
│   ├── page.tsx                  # Home — recommender page
│   ├── profile/
│   │   └── page.tsx              # User profile
│   └── auth/
│       ├── login/page.tsx
│       ├── signup/page.tsx
│       ├── forgot/page.tsx
│       ├── reset/page.tsx
│       └── callback/route.ts     # GET handler: exchange code, redirect
├── components/
│   ├── Masthead.tsx
│   ├── TastingSidebar.tsx
│   ├── RadarChart.tsx
│   ├── Ledger.tsx
│   ├── LedgerCard.tsx
│   ├── RatingControl.tsx
│   └── auth/
│       ├── LoginForm.tsx
│       ├── SignupForm.tsx
│       ├── ForgotForm.tsx
│       └── ResetForm.tsx
├── lib/
│   ├── recommender.ts
│   ├── supabase-browser.ts
│   ├── types.ts
│   ├── personalization.ts
│   └── catalog.ts               # fetch + cache beers.json
├── contexts/
│   └── AuthContext.tsx
├── public/
│   └── data/
│       └── beers.json
├── scripts/
│   ├── fetch_obdb.py
│   ├── build_catalog.py
│   └── export_catalog.py
├── data/                         # Unchanged
├── supabase/                     # Unchanged
├── tailwind.config.ts
├── next.config.ts
├── package.json
├── tsconfig.json
├── postcss.config.mjs
├── pyproject.toml                # Kept for data pipeline
└── .env.local.example
```

## Data Pipeline

The existing Python pipeline is untouched. A new `scripts/export_catalog.py`:

1. Reads `data/processed/beers.parquet`
2. Selects columns: `beer_id, name, brewery, style, country, abv, ibu, srm, bitterness, sweetness, maltiness, hoppiness, body, sourness, abv_normalized`
3. Rounds floats to 2 decimal places
4. Writes `public/data/beers.json` as a JSON array

Expected size: ~560 rows, ~50-80KB uncompressed, ~15-20KB gzipped.

## Recommender (TypeScript Port)

Direct port of `src/recommender.py`:

- **Types:** `Beer` (catalog row), `TasteProfile` (7-axis slider values), `Recommendation` (Beer + distance + match_score)
- **`TASTE_COLS`:** `["bitterness", "sweetness", "maltiness", "hoppiness", "body", "sourness", "abv_normalized"]`
- **`loadCatalog()`:** Fetches `/data/beers.json`, caches in module variable
- **`recommend(profile, topK, filters)`:** Euclidean distance, `score = 100 / (1 + distance)`, sort descending, return top-k
- **`explain(beer, profile)`:** Same logic — ranks axes by user intensity, reports matches/misses
- **Filters:** `minAbv`, `maxAbv`, `styles[]`, `countries[]`

## Styling

Tailwind CSS with a custom theme:

```ts
// tailwind.config.ts theme.extend
colors: {
  paper:       { DEFAULT: "#F1E8D3", deep: "#E6DABB", edge: "#DBCDA6" },
  ink:         { DEFAULT: "#1A1410", soft: "#4A382A", faint: "#8A7560" },
  copper:      { DEFAULT: "#B0651E", dim: "#8A4E16", soft: "rgba(176,101,30,0.16)" },
  oxblood:     "#6B1F1F",
  hairline:    { DEFAULT: "rgba(26,20,16,0.20)", soft: "rgba(26,20,16,0.10)" },
},
fontFamily: {
  serif:    ["Newsreader", "Fraunces", "Georgia", "Times New Roman", "serif"],
  display:  ["Fraunces", "Newsreader", "Georgia", "serif"],
  mono:     ["IBM Plex Mono", "JetBrains Mono", "ui-monospace", "Menlo", "Consolas", "monospace"],
},
```

Fonts loaded via `next/font/google` for optimal performance.

Custom CSS in `globals.css` for:
- Paper grain SVG noise overlay (`body::before`)
- Decorative top hairline (`body::after`)
- Stagger entrance animations (`@keyframes riseIn`, `@keyframes inkBleed`)
- Slider styling overrides (if using a React slider library)
- Selection color (`::selection`)

Mobile-first layout. Single desktop breakpoint at `min-width: 1100px` (`lg` or custom `desktop` screen in Tailwind config).

## Auth

**Client:** `@supabase/supabase-js` initialized with `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` env vars.

**AuthContext:**
- Wraps the app in `layout.tsx`
- On mount: calls `supabase.auth.getSession()` and listens to `onAuthStateChange`
- Exposes: `user`, `session`, `loading`, `signIn()`, `signUp()`, `signOut()`, `resetPassword()`

**Auth pages:** React form components. On submit, call AuthContext methods. Show flash messages via local state.

**Callback route:** `app/auth/callback/route.ts`
- GET handler receives `?code=...`
- Calls `supabase.auth.exchangeCodeForSession(code)`
- Redirects to `/` or `?next=...`

**Protected routes:** Profile page checks `user` from AuthContext. If null, shows a gate message with link to login.

## Ratings & Personalization

**Ratings:** Direct Supabase calls from the browser.
- `supabase.from("user_beers").upsert(...)` on rating change
- `supabase.from("user_beers").delete()` on rating clear
- `supabase.from("user_beers").select("beer_id, rating")` to fetch user's ratings
- RLS ensures users can only access their own rows (existing policies)

**Personalization (TS port of `src/personalization.py`):**
- `personalizedDefaults(ratings, catalog)`: returns slider defaults or null
- Same algorithm: filter ratings ≥ 4★, weight by `rating - 3`, average taste vectors, clip to [0, 10]

## Charts (Recharts)

`<RadarChart>` component wrapping Recharts:
- Custom `<PolarGrid>`, `<PolarAngleAxis>`, `<PolarRadiusAxis>` styled with broadsheet colors
- Profile radar: single `<Radar>` trace (copper fill)
- Comparison radar: profile trace (ink, dotted) + up to 3 beer traces (copper, oxblood, ink-soft)
- Responsive container, transparent backgrounds
- Labels: Bitter, Sweet, Malty, Hoppy, Body, Sour, Strength

## Pages

### Home (`/`)
- Masthead (title, kicker, double rule, nav strip with account link)
- Two-column layout on desktop: TastingSidebar (left, sticky) + Main (right)
- Main: feature header, two radar charts side-by-side on desktop, Ledger below
- All state local to the page (useState for slider values, useMemo for recommendations)
- Mobile: sidebar collapses with toggle button

### Profile (`/profile`)
- Masthead (with back link)
- Display name editor (input + save button → Supabase profiles.update)
- Personalized radar chart (Fig. III)
- Rated beers ledger table with remove button
- Sign out button

### Auth pages (`/auth/*`)
- Simple centered forms matching broadsheet aesthetic
- Login, signup (email + password + display name), forgot password, reset password
- Flash messages shown above the form

## Environment Variables

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

No server-side secrets needed (all auth is client-side via Supabase JS SDK with the publishable/anon key).

## Files to Remove

- `dashboard/` (entire directory — app.py, auth_routes.py, pages/, components/, templates/, assets/)
- `src/` (Python recommender, auth, db, config, personalization — replaced by `lib/`)
- `tests/` (Python tests — new tests would be written separately if desired)
- `.env` / `.env.example` (replaced by `.env.local.example`)

## Files to Keep

- `scripts/fetch_obdb.py`, `scripts/build_catalog.py` (data pipeline)
- `scripts/export_catalog.py` (new)
- `data/` (raw + processed data)
- `supabase/` (migrations)
- `notebooks/` (data prep)
- `pyproject.toml` (for the Python pipeline, update deps to pipeline-only)
- `.gitignore` (update for Next.js)
- `README.md` (rewrite)

## Testing

Not in scope for this initial rebuild. The recommender logic can be unit-tested with Vitest later. The current Python tests are specific to the Dash app and will be removed.

## Deployment

1. Push to GitHub
2. Connect repo to Vercel
3. Set env vars in Vercel dashboard
4. Vercel auto-detects Next.js, builds, deploys
5. Update Supabase redirect URLs to the Vercel domain
