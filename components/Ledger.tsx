"use client";

import type { Recommendation, TasteProfile } from "@/lib/types";
import { explain } from "@/lib/recommender";
import { LedgerCard } from "@/components/LedgerCard";

interface LedgerProps {
  recommendations: Recommendation[];
  profile: TasteProfile;
  ratings: Map<string, number>;
  signedIn: boolean;
  onRate: (beerId: string, rating: number | null) => void;
}

export function Ledger({
  recommendations,
  profile,
  ratings,
  signedIn,
  onRate,
}: LedgerProps) {
  return (
    <section className="ledger-section">
      <div className="ledger-head">
        <h3>The Ledger</h3>
        <span className="legend">Sorted &middot; highest match first</span>
      </div>
      <div className="ledger-card-view">
        {recommendations.map((beer, i) => (
          <LedgerCard
            key={beer.beer_id}
            rank={i + 1}
            beer={beer}
            explanation={explain(beer, profile)}
            rating={ratings.get(beer.beer_id) ?? null}
            signedIn={signedIn}
            onRate={(rating) => onRate(beer.beer_id, rating)}
          />
        ))}
      </div>
    </section>
  );
}
