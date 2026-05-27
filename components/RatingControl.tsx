"use client";

interface RatingControlProps {
  beerId: string;
  currentRating: number | null;
  signedIn: boolean;
  onRate: (rating: number | null) => void;
}

const RATING_OPTIONS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0];

export function RatingControl({
  beerId,
  currentRating,
  signedIn,
  onRate,
}: RatingControlProps) {
  if (!signedIn) {
    return (
      <div className="lc-rate">
        <select disabled aria-label="Rating requires an account">
          <option>account needed</option>
        </select>
      </div>
    );
  }

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value;
    if (val === "") {
      onRate(null);
    } else {
      onRate(parseFloat(val));
    }
  }

  return (
    <div className="lc-rate">
      <select
        value={currentRating != null ? String(currentRating) : ""}
        onChange={handleChange}
        aria-label={`Rate beer ${beerId}`}
      >
        <option value="">Rate&hellip;</option>
        {RATING_OPTIONS.map((v) => (
          <option key={v} value={String(v)}>
            {v.toFixed(1)} &#9733;
          </option>
        ))}
        {currentRating != null && <option value="">Clear</option>}
      </select>
    </div>
  );
}
