# Profile Page Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the profile page with curated editorial sections: display name, radar chart, top 5 favourites, worst 5, next 5 recommendations, and sign out.

**Architecture:** The page keeps its existing data fetching (catalog, ratings, profile) and adds computed memos for top/worst/next beer lists. The old ratings table is replaced with `.profile-list` styled sections. The `recommend()` function from `lib/recommender.ts` is reused for the "Up Next" section. No new components — the lists are simple enough to render inline.

**Tech Stack:** React (useMemo), existing `recommend()` and `personalizedDefaults()`, CSS custom properties

---

## File Map

- **Modify:** `app/globals.css` — replace `.profile-ledger` table styles with `.profile-list` styles
- **Modify:** `app/profile/page.tsx` — rewrite page content

---

### Task 1: Add profile list CSS

**Files:**
- Modify: `app/globals.css`

- [ ] **Step 1: Replace `.profile-ledger` styles with `.profile-list` styles**

In `app/globals.css`, find the `/* ───── Profile ledger (table on profile page) */` section (around line 929) and replace the entire block (`.profile-ledger table`, `.profile-ledger th`, `.profile-ledger td`, `.profile-ledger tr:hover td`) with:

```css
/* ───── Profile beer lists ───────────────────────────────────────── */
.profile-list {
    margin-top: 0.4rem;
}
.profile-list__item {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.7rem 0;
    border-bottom: 1px solid var(--color-hairline-soft);
}
.profile-list__item:last-child {
    border-bottom: 0;
}
.profile-list__rank {
    font-family: var(--font-display);
    font-size: 1.1rem;
    font-weight: 800;
    color: var(--color-copper);
    font-variant-numeric: lining-nums tabular-nums;
    flex-shrink: 0;
    min-width: 2.2rem;
}
.profile-list__info {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
}
.profile-list__name {
    font-family: var(--font-serif);
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--color-ink);
    line-height: 1.25;
}
.profile-list__brewery {
    font-family: var(--font-serif);
    font-style: italic;
    color: var(--color-ink-soft);
    font-size: 0.9rem;
}
.profile-list__meta {
    font-family: var(--font-mono);
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--color-ink-soft);
    margin-top: 0.15rem;
}
.profile-list__empty {
    font-family: var(--font-serif);
    font-style: italic;
    color: var(--color-ink-soft);
    padding: 0.7rem 0;
}
```

- [ ] **Step 2: Commit**

```bash
git add app/globals.css
git commit -m "feat: add profile beer list styles, remove old table styles"
```

---

### Task 2: Rewrite profile page

**Files:**
- Modify: `app/profile/page.tsx`

- [ ] **Step 1: Replace the entire file content**

Replace the full content of `app/profile/page.tsx` with:

```tsx
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Masthead } from "@/components/Masthead";
import { RadarChart } from "@/components/RadarChart";
import { useAuth } from "@/contexts/AuthContext";
import { loadCatalog } from "@/lib/catalog";
import { recommend } from "@/lib/recommender";
import { personalizedDefaults } from "@/lib/personalization";
import type { Beer, TasteProfile, UserRating } from "@/lib/types";

const RADAR_AXES = [
  { key: "bitterness", label: "Bitter" },
  { key: "sweetness", label: "Sweet" },
  { key: "maltiness", label: "Malty" },
  { key: "hoppiness", label: "Hoppy" },
  { key: "body", label: "Body" },
  { key: "sourness", label: "Sour" },
  { key: "abv_preference", label: "Strength" },
];

export default function ProfilePage() {
  const { user, supabase, signOut, loading: authLoading } = useAuth();
  const [catalog, setCatalog] = useState<Beer[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [nameStatus, setNameStatus] = useState("");
  const [ratings, setRatings] = useState<UserRating[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadCatalog().then(setCatalog);
  }, []);

  useEffect(() => {
    if (!user || !supabase) return;
    const uid = user.id;

    Promise.all([
      supabase.from("profiles").select("display_name").eq("id", uid).single(),
      supabase.from("user_beers").select("beer_id, rating, rated_at"),
    ]).then(([profRes, ratingsRes]) => {
      if (profRes.data) setDisplayName(profRes.data.display_name || "");
      if (ratingsRes.data) setRatings(ratingsRes.data as UserRating[]);
      setLoading(false);
    });
  }, [user, supabase]);

  const catById = useMemo(() => {
    const m = new Map<string, Beer>();
    catalog.forEach((b) => m.set(b.beer_id, b));
    return m;
  }, [catalog]);

  const defaults = useMemo(
    () => personalizedDefaults(ratings, catalog),
    [ratings, catalog]
  );

  const radarData = useMemo(
    () =>
      RADAR_AXES.map((a) => ({
        axis: a.label,
        "Your taste": defaults
          ? defaults[a.key as keyof TasteProfile]
          : 5.0,
      })),
    [defaults]
  );

  const topRated = useMemo(() => {
    const resolved = ratings
      .map((r) => ({ ...r, beer: catById.get(r.beer_id) }))
      .filter((r) => r.beer);
    resolved.sort((a, b) =>
      b.rating !== a.rating
        ? b.rating - a.rating
        : a.beer!.name.localeCompare(b.beer!.name)
    );
    return resolved.slice(0, 5);
  }, [ratings, catById]);

  const worstRated = useMemo(() => {
    const resolved = ratings
      .map((r) => ({ ...r, beer: catById.get(r.beer_id) }))
      .filter((r) => r.beer);
    resolved.sort((a, b) =>
      a.rating !== b.rating
        ? a.rating - b.rating
        : a.beer!.name.localeCompare(b.beer!.name)
    );
    return resolved.slice(0, 5);
  }, [ratings, catById]);

  const nextRecommendations = useMemo(() => {
    if (!defaults || catalog.length === 0) return [];
    const ratedIds = new Set(ratings.map((r) => r.beer_id));
    const unrated = catalog.filter((b) => !ratedIds.has(b.beer_id));
    if (unrated.length === 0) return [];
    return recommend(unrated, defaults, 5);
  }, [defaults, catalog, ratings]);

  const handleSaveName = useCallback(async () => {
    const name = displayName.trim();
    if (name.length < 1 || name.length > 50) {
      setNameStatus("Name must be 1–50 chars.");
      return;
    }
    if (!user || !supabase) {
      setNameStatus("Account required.");
      return;
    }
    const { error } = await supabase
      .from("profiles")
      .update({ display_name: name })
      .eq("id", user.id);
    setNameStatus(error ? `Save failed: ${error.message}` : "Saved.");
  }, [displayName, user, supabase]);

  if (authLoading) return null;

  if (!user) {
    return (
      <>
        <Masthead />
        <main className="feature">
          <div className="profile-gate">
            <h2>Create an account to view your profile.</h2>
            <Link href="/auth/login" className="ink-btn">
              Account
            </Link>
          </div>
        </main>
        <div className="colophon">
          <span>Set in Fraunces, Newsreader &amp; IBM Plex Mono</span>
          <span>Printed on cream, in copper ink</span>
        </div>
      </>
    );
  }

  const pad = (n: number) => String(n).padStart(2, "0");

  return (
    <>
      <Masthead />
      <main className="feature">
        <div className="feature-header">
          <div className="article-no">No. 02 &mdash; Reader&apos;s Card</div>
          <h2>Your profile.</h2>
        </div>

        <section className="profile-name-section">
          <div className="prof-row">
            <span className="prof-label">Display name</span>
            <div className="prof-field">
              <div className="prof-input">
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  maxLength={50}
                  placeholder="Enter a display name"
                />
              </div>
              <button className="prof-save" onClick={handleSaveName}>
                Save
              </button>
            </div>
            <span className="prof-status">{nameStatus}</span>
          </div>
        </section>

        <section className="chart-card" style={{ marginTop: "1.5rem" }}>
          <div className="chart-caption">
            <span>Fig. III</span>
            <span>
              Your taste profile
              {!defaults && (
                <span
                  className="chart-hint"
                  data-tip="Rate beers ≥ 4★ to populate this chart"
                >
                  {" "}
                  &#9432;
                </span>
              )}
            </span>
          </div>
          <div className="radar-graph">
            <RadarChart
              data={radarData}
              traces={[
                {
                  key: "Your taste",
                  name: "Your taste",
                  color: "#B0651E",
                  fill: "rgba(176,101,30,0.22)",
                },
              ]}
            />
          </div>
        </section>

        <section style={{ marginTop: "2rem" }}>
          <div className="section-label">The Best Pours</div>
          {ratings.length === 0 ? (
            <div className="profile-list__empty">
              Rate a few beers to populate your lists.
            </div>
          ) : (
            <div className="profile-list">
              {topRated.map((r, i) => (
                <div key={r.beer_id} className="profile-list__item">
                  <span className="profile-list__rank">
                    &#8470; {pad(i + 1)}
                  </span>
                  <div className="profile-list__info">
                    <span className="profile-list__name">
                      {r.beer!.name}
                    </span>
                    <span className="profile-list__brewery">
                      {r.beer!.brewery}
                    </span>
                    <span className="profile-list__meta">
                      {r.beer!.style} &middot; &#9733; {r.rating}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section style={{ marginTop: "2rem" }}>
          <div className="section-label">The Drains</div>
          {ratings.length === 0 ? (
            <div className="profile-list__empty">
              Rate a few beers to populate your lists.
            </div>
          ) : (
            <div className="profile-list">
              {worstRated.map((r, i) => (
                <div key={r.beer_id} className="profile-list__item">
                  <span className="profile-list__rank">
                    &#8470; {pad(i + 1)}
                  </span>
                  <div className="profile-list__info">
                    <span className="profile-list__name">
                      {r.beer!.name}
                    </span>
                    <span className="profile-list__brewery">
                      {r.beer!.brewery}
                    </span>
                    <span className="profile-list__meta">
                      {r.beer!.style} &middot; &#9733; {r.rating}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {nextRecommendations.length > 0 && (
          <section style={{ marginTop: "2rem" }}>
            <div className="section-label">Up Next</div>
            <div className="profile-list">
              {nextRecommendations.map((beer, i) => (
                <div key={beer.beer_id} className="profile-list__item">
                  <span className="profile-list__rank">
                    &#8470; {pad(i + 1)}
                  </span>
                  <div className="profile-list__info">
                    <span className="profile-list__name">{beer.name}</span>
                    <span className="profile-list__brewery">
                      {beer.brewery}
                    </span>
                    <span className="profile-list__meta">
                      {beer.style} &middot; Match{" "}
                      {beer.match_score.toFixed(1)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="profile-signout-section">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              signOut();
            }}
          >
            <button type="submit" className="ink-btn ink-btn--secondary">
              Sign out
            </button>
          </form>
        </section>
      </main>
      <div className="colophon">
        <span>Set in Fraunces, Newsreader &amp; IBM Plex Mono</span>
        <span>Printed on cream, in copper ink</span>
      </div>
    </>
  );
}
```

- [ ] **Step 2: Verify in browser**

Visit `http://localhost:3000/profile` while signed in:
- Display name section should appear with inline edit
- Radar chart should show taste profile (or hint if not enough ratings)
- "The Best Pours" section should show up to 5 highest-rated beers
- "The Drains" section should show up to 5 lowest-rated beers
- "Up Next" section should show 5 recommended unrated beers (only if enough 4+ ratings exist)
- Sign out button at bottom
- If not signed in, the gate message should appear

- [ ] **Step 3: Commit**

```bash
git add app/profile/page.tsx
git commit -m "feat: overhaul profile page with curated beer lists"
```
