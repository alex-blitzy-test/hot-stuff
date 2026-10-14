/**
 * Wire shapes of the Hot Stuff JSON API.
 *
 * Source of truth: the field sets serialized by `TrackSchema.Meta.fields` in
 * `api/models.py` and the payload keys assembled by the handlers in
 * `api/routes.py`. This module declares types only — it imports nothing and
 * holds no runtime value.
 */

/**
 * One chart appearance, as serialized by `TrackSchema`.
 *
 * Returned by `GET /api/week/<week>` (inside `WeekResponse.songs`),
 * `GET /api/artist/<artist>` and `GET /api/track/<spotify_id>`.
 * Field order follows the serializer, which places `tempo` last.
 */
export interface Track {
  id: number;
  /** Chart week as an ISO `YYYY-MM-DD` date string. */
  week: string;
  rank: number;
  track: string;
  artist: string;
  spotify_id: string;
  energy: number;
  danceability: number;
  valence: number;
  liveness: number;
  speechiness: number;
  acousticness: number;
  instrumentalness: number;
  loudness: number;
  tempo: number;
}

/** One feature's weekly average, part of the `GET /api/week/<week>` payload. */
export interface FeatureAverage {
  /** Column name title-cased, e.g. "Energy", "Danceability", "Instrumentalness". */
  feature: string;
  /** Whole-number percentage, not a 0-1 fraction. */
  mean: number;
  /** Always 100. */
  full: number;
}

/** Body of `GET /api/week/<week>`. */
export interface WeekResponse {
  /** Resolved chart Saturday as an ISO `YYYY-MM-DD` date string. */
  week: string;
  songs: Track[];
  averages: FeatureAverage[];
  /** Mean tempo rounded to a whole number. */
  avgTempo: number;
}

/** One yearly point of a feature analysis, part of the `GET /api/analysis/<feature>` payload. */
export interface AnalysisPoint {
  /** Year as a string, matching the `yearly_avg.year` column. */
  year: string;
  value: number;
  /** Five-year rolling mean; null inside the first four years of the window. */
  rolling: number | null;
}

/** Body of `GET /api/analysis/<feature>`. */
export interface AnalysisResponse {
  feature: string;
  data: AnalysisPoint[];
}

/** Body of `GET /api/artist/<artist>/summary`. */
export interface ArtistSummary {
  /** The decoded search term as requested, not re-cased to a matched spelling. */
  artist: string;
  total_weeks: number;
  unique_tracks: number;
  /** Null when the search matched no appearances. */
  best_rank: number | null;
  /** Null when the search matched no appearances. */
  first_week: string | null;
  /** Null when the search matched no appearances. */
  last_week: string | null;
  /** Lowercase feature names plus "tempo"; empty when nothing matched. */
  avg_features: Record<string, number>;
}
