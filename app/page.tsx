"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Masthead } from "@/components/Masthead";
import { TastingSidebar } from "@/components/TastingSidebar";
import { RadarChart } from "@/components/RadarChart";
import { Ledger } from "@/components/Ledger";
import { useAuth } from "@/contexts/AuthContext";
import { loadCatalog, getStyles, getCountries } from "@/lib/catalog";
import { recommend, explain, TASTE_COLS } from "@/lib/recommender";
import { personalizedDefaults } from "@/lib/personalization";
import type { Beer, Filters, Recommendation, TasteProfile, UserRating } from "@/lib/types";

const DEFAULT_PROFILE: TasteProfile = {
  bitterness: 5,
  sweetness: 5,
  maltiness: 5,
  hoppiness: 5,
  body: 5,
  sourness: 5,
  abv_preference: 5,
};

const RADAR_AXES = [
  { key: "bitterness", label: "Bitter" },
  { key: "sweetness", label: "Sweet" },
  { key: "maltiness", label: "Malty" },
  { key: "hoppiness", label: "Hoppy" },
  { key: "body", label: "Body" },
  { key: "sourness", label: "Sour" },
  { key: "abv_preference", label: "Strength" },
];

const TASTE_COL_FOR_AXIS: Record<string, string> = {
  bitterness: "bitterness",
  sweetness: "sweetness",
  maltiness: "maltiness",
  hoppiness: "hoppiness",
  body: "body",
  sourness: "sourness",
  abv_preference: "abv_normalized",
};

export default function Home() {
  const { user, supabase } = useAuth();
  const [catalog, setCatalog] = useState<Beer[]>([]);
  const [profile, setProfile] = useState<TasteProfile>(DEFAULT_PROFILE);
  const [filters, setFilters] = useState<Filters>({});
  const [topK, setTopK] = useState(10);
  const [ratings, setRatings] = useState<Map<string, number>>(new Map());
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadCatalog().then((data) => {
      setCatalog(data);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!user || !supabase) return;
    supabase
      .from("user_beers")
      .select("beer_id, rating")
      .then(({ data }) => {
        if (data) {
          setRatings(new Map(data.map((r: UserRating) => [r.beer_id, r.rating])));
          const defaults = personalizedDefaults(
            data as UserRating[],
            catalog
          );
          if (defaults) setProfile(defaults);
        }
      });
  }, [user, supabase, catalog]);

  const styles = useMemo(() => getStyles(catalog), [catalog]);
  const countries = useMemo(() => getCountries(catalog), [catalog]);

  const recommendations = useMemo(
    () => (catalog.length ? recommend(catalog, profile, topK, filters) : []),
    [catalog, profile, topK, filters]
  );

  const displayedResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return recommendations;
    const matched = catalog.filter(
      (b) =>
        b.name.toLowerCase().includes(q) ||
        b.brewery.toLowerCase().includes(q)
    );
    if (matched.length === 0) return [];
    return recommend(matched, profile, matched.length, filters);
  }, [searchQuery, catalog, profile, filters, recommendations]);

  const profileRadarData = useMemo(
    () =>
      RADAR_AXES.map((a) => ({
        axis: a.label,
        You: profile[a.key as keyof TasteProfile],
      })),
    [profile]
  );

  const comparisonRadarData = useMemo(() => {
    const top3 = recommendations.slice(0, 3);
    return RADAR_AXES.map((a) => {
      const col = TASTE_COL_FOR_AXIS[a.key];
      const point: Record<string, number | string> = {
        axis: a.label,
        You: profile[a.key as keyof TasteProfile],
      };
      top3.forEach((beer, i) => {
        point[beer.name.slice(0, 28)] = beer[col as keyof Beer] as number;
      });
      return point;
    });
  }, [profile, recommendations]);

  const comparisonTraces = useMemo(() => {
    const colors = ["#B0651E", "#6B1F1F", "#4A382A"];
    const top3 = recommendations.slice(0, 3);
    return [
      { key: "You", name: "You", color: "#1A1410", fill: "rgba(26,20,16,0.06)", dash: true },
      ...top3.map((beer, i) => ({
        key: beer.name.slice(0, 28),
        name: beer.name.slice(0, 28),
        color: colors[i % colors.length],
      })),
    ];
  }, [recommendations]);

  const handleRate = useCallback(
    async (beerId: string, rating: number | null) => {
      if (!user || !supabase) return;
      const uid = user.id;
      if (rating === null) {
        await supabase
          .from("user_beers")
          .delete()
          .eq("user_id", uid)
          .eq("beer_id", beerId);
        setRatings((prev) => {
          const next = new Map(prev);
          next.delete(beerId);
          return next;
        });
      } else {
        await supabase.from("user_beers").upsert(
          { user_id: uid, beer_id: beerId, rating },
          { onConflict: "user_id,beer_id" }
        );
        setRatings((prev) => new Map(prev).set(beerId, rating));
      }
    },
    [user, supabase]
  );

  const handleReset = useCallback(() => setProfile(DEFAULT_PROFILE), []);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-copper)" }}>
          Loading catalogue...
        </span>
      </div>
    );
  }

  return (
    <>
      <Masthead />
      <div className="spread">
        <TastingSidebar
          profile={profile}
          onProfileChange={setProfile}
          filters={filters}
          onFiltersChange={setFilters}
          topK={topK}
          onTopKChange={setTopK}
          styles={styles}
          countries={countries}
          onReset={handleReset}
        />
        <main className="feature">
          <div className="feature-header">
            <div className="article-no">No. 01 — Tonight&apos;s Pour</div>
            <h2>A glass, suggested.</h2>
            <p className="dek">
              Beers ranked by Euclidean distance over a seven-axis taste vector.
              Match score is 100 &times; (1 / (1 + distance)) — closer to your profile,
              higher the score.
            </p>
          </div>

          <div className="charts-row">
            <div className="chart-card">
              <div className="chart-caption">
                <span>Fig. I</span>
                <span>Your profile</span>
              </div>
              <div className="radar-graph">
                <RadarChart
                  data={profileRadarData}
                  traces={[
                    {
                      key: "You",
                      name: "You",
                      color: "#B0651E",
                      fill: "rgba(176,101,30,0.22)",
                    },
                  ]}
                />
              </div>
            </div>
            <div className="chart-card">
              <div className="chart-caption">
                <span>Fig. II</span>
                <span>You vs. top 3</span>
              </div>
              <div className="radar-graph">
                <RadarChart
                  data={comparisonRadarData}
                  traces={comparisonTraces}
                  showLegend
                />
              </div>
            </div>
          </div>

          <div className="ledger-search">
            <input
              type="text"
              placeholder="Search by name or brewery..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                className="ledger-search__clear"
                onClick={() => setSearchQuery("")}
                aria-label="Clear search"
              >
                clear
              </button>
            )}
          </div>

          <Ledger
            recommendations={displayedResults}
            profile={profile}
            ratings={ratings}
            signedIn={!!user}
            onRate={handleRate}
          />
        </main>
      </div>
      <div className="colophon">
        <span>Set in Fraunces, Newsreader &amp; IBM Plex Mono</span>
        <span>Printed on cream, in copper ink</span>
      </div>
    </>
  );
}
