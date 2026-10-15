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
 *
 * Only `id` is guaranteed to carry a value. `TrackSchema` declares no field
 * types, so marshmallow infers one per name and serializes a NULL as a JSON
 * `null` instead of dropping the key, and every `tracks` column except the
 * primary key is nullable in `api/models.py`. Each consumer therefore has to
 * say what it does with a null rather than assume a value is there.
 */
export interface Track {
  id: number;
  /** Chart week as an ISO `YYYY-MM-DD` date string; null when the column is null. */
  week: string | null;
  rank: number | null;
  track: string | null;
  artist: string | null;
  spotify_id: string | null;
  energy: number | null;
  danceability: number | null;
  valence: number | null;
  liveness: number | null;
  speechiness: number | null;
  acousticness: number | null;
  instrumentalness: number | null;
  loudness: number | null;
  tempo: number | null;
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
  /**
   * Mean tempo as a whole number: the weekly mean is truncated toward zero,
   * not rounded, so a mean of 120.9 arrives as 120.
   */
  avgTempo: number;
}

/** One yearly point of a feature analysis, part of the `GET /api/analysis/<feature>` payload. */
export interface AnalysisPoint {
  /** Year as a string, matching the `yearly_avg.year` column; null when the column is null. */
  year: string | null;
  value: number;
  /**
   * Five-year rolling mean.
   *
   * Never null: `get_rolling_avg` drops every row whose rolling mean is
   * undefined, so the window's first four years are absent from `data`
   * entirely rather than present with a null, and this key always carries a
   * number.
   */
  rolling: number;
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
