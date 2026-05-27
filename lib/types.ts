export interface Beer {
  beer_id: string;
  name: string;
  brewery: string;
  style: string;
  country: string;
  abv: number;
  ibu: number;
  srm: number;
  bitterness: number;
  sweetness: number;
  maltiness: number;
  hoppiness: number;
  body: number;
  sourness: number;
  abv_normalized: number;
}

export interface Recommendation extends Beer {
  distance: number;
  match_score: number;
}

export interface TasteProfile {
  bitterness: number;
  sweetness: number;
  maltiness: number;
  hoppiness: number;
  body: number;
  sourness: number;
  abv_preference: number;
}

export interface Filters {
  minAbv?: number;
  maxAbv?: number;
  styles?: string[];
  countries?: string[];
}

export interface UserRating {
  beer_id: string;
  rating: number;
  rated_at?: string;
}
