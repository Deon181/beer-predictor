"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Masthead } from "@/components/Masthead";
import { RadarChart } from "@/components/RadarChart";
import { useAuth } from "@/contexts/AuthContext";
import { loadCatalog } from "@/lib/catalog";
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

  const handleRemoveRating = useCallback(
    async (beerId: string) => {
      if (!user || !supabase) return;
      await supabase
        .from("user_beers")
        .delete()
        .eq("user_id", user.id)
        .eq("beer_id", beerId);
      setRatings((prev) => prev.filter((r) => r.beer_id !== beerId));
    },
    [user, supabase]
  );

  const catById = useMemo(() => {
    const m = new Map<string, Beer>();
    catalog.forEach((b) => m.set(b.beer_id, b));
    return m;
  }, [catalog]);

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

  const sortedRatings = [...ratings].sort(
    (a, b) => (b.rated_at || "").localeCompare(a.rated_at || "")
  );

  return (
    <>
      <Masthead />
      <main className="feature">
        <div className="feature-header">
          <div className="article-no">No. 02 — Reader&apos;s Card</div>
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
              Personalized profile
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

        <section className="ledger-section">
          <h3>Your ledger</h3>
          {sortedRatings.length === 0 ? (
            <div className="lc-empty" style={{ fontStyle: "italic", color: "var(--color-ink-soft)" }}>
              Rate a few beers to populate your ledger.
            </div>
          ) : (
            <table className="profile-ledger">
              <thead>
                <tr>
                  <th>Beer</th>
                  <th>Brewery</th>
                  <th>Style</th>
                  <th>Rating</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sortedRatings.map((r) => {
                  const beer = catById.get(r.beer_id);
                  if (!beer) return null;
                  return (
                    <tr key={r.beer_id}>
                      <td>{beer.name}</td>
                      <td>{beer.brewery}</td>
                      <td>{beer.style}</td>
                      <td>★ {r.rating}</td>
                      <td>
                        <button
                          className="linkish"
                          onClick={() => handleRemoveRating(r.beer_id)}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>

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
