"use client";

import type { Recommendation } from "@/lib/types";
import { RatingControl } from "@/components/RatingControl";

interface LedgerCardProps {
  rank: number;
  beer: Recommendation;
  explanation: string;
  rating: number | null;
  signedIn: boolean;
  onRate: (rating: number | null) => void;
}

export function LedgerCard({
  rank,
  beer,
  explanation,
  rating,
  signedIn,
  onRate,
}: LedgerCardProps) {
  const rankFormatted = String(rank).padStart(2, "0");

  return (
    <article className={`ledger-card${rank === 1 ? " first" : ""}`}>
      <div className="lc-top">
        <span className="lc-rank">{"№"} {rankFormatted}</span>
        <span className="lc-match">Match &middot; {beer.match_score.toFixed(1)}</span>
      </div>
      <h4 className="lc-name">{beer.name}</h4>
      <div className="lc-brewery">{beer.brewery}</div>
      <div className="lc-meta">
        {beer.style} &middot; {beer.country} &middot; {beer.abv}% &middot; IBU{" "}
        {beer.ibu}
      </div>
      <div className="lc-why">{explanation}</div>
      <RatingControl
        beerId={beer.beer_id}
        currentRating={rating}
        signedIn={signedIn}
        onRate={onRate}
      />
    </article>
  );
}
