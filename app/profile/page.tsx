"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
  const router = useRouter();
  const { user, supabase, signOut, loading: authLoading } = useAuth();
  const [catalog, setCatalog] = useState<Beer[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [nameStatus, setNameStatus] = useState("");
  const [editing, setEditing] = useState(false);
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

        <section className="profile-card">
          <div className="profile-card__monogram">
            {(displayName || "?")[0].toUpperCase()}
          </div>
          <div className="profile-card__body">
            {!editing ? (
              <>
                <h3 className="profile-card__name">
                  {displayName || "Anonymous"}
                </h3>
                <button
                  className="profile-card__edit-toggle"
                  onClick={() => setEditing(true)}
                >
                  Edit name
                </button>
              </>
            ) : (
              <>
                <div className="profile-card__edit-row">
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    maxLength={50}
                    placeholder="Enter a display name"
                    autoFocus
                  />
                  <button
                    className="profile-card__save"
                    onClick={async () => {
                      await handleSaveName();
                      setEditing(false);
                    }}
                  >
                    Save
                  </button>
                  <button
                    className="profile-card__edit-toggle"
                    onClick={() => setEditing(false)}
                  >
                    Cancel
                  </button>
                </div>
                {nameStatus && (
                  <div className="profile-card__status">{nameStatus}</div>
                )}
              </>
            )}
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
              signOut().then(() => router.push("/"));
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
