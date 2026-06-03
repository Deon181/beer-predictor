"use client";

import type { Recommendation, TasteProfile } from "@/lib/types";
import { explain } from "@/lib/recommender";
import { LedgerCard } from "@/components/LedgerCard";
import type { AxisKey } from "@/lib/axes";

interface LedgerProps {
  recommendations: Recommendation[];
  profile: TasteProfile;
  ratings: Map<string, number>;
  signedIn: boolean;
  onRate: (beerId: string, rating: number | null) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  activeAxes: AxisKey[];
}

export function Ledger({
  recommendations,
  profile,
  ratings,
  signedIn,
  onRate,
  searchQuery,
  onSearchChange,
  activeAxes,
}: LedgerProps) {
  return (
    <section className="ledger-section">
      <div className="ledger-head">
        <h3>The Ledger</h3>
        <span className="legend">Sorted &middot; highest match first</span>
      </div>
      <div className="ledger-search">
        <input
          type="text"
          placeholder="Search by name or brewery..."
          aria-label="Search beers by name or brewery"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        {searchQuery && (
          <button
            className="ledger-search__clear"
            onClick={() => onSearchChange("")}
            aria-label="Clear search"
          >
            clear
          </button>
        )}
      </div>
      <div className="ledger-card-view">
        {recommendations.map((beer, i) => (
          <LedgerCard
            key={beer.beer_id}
            rank={i + 1}
            beer={beer}
            explanation={explain(beer, profile, activeAxes)}
            rating={ratings.get(beer.beer_id) ?? null}
            signedIn={signedIn}
            onRate={(rating) => onRate(beer.beer_id, rating)}
          />
        ))}
      </div>
    </section>
  );
}
