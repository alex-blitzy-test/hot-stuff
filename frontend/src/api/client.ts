/**
 * The frontend's single typed HTTP boundary.
 *
 * Every request the browser makes to the Hot Stuff API goes through this
 * module: it is the only file under `frontend/src` that imports axios and the
 * only place a URL is built. Callers import the endpoint function they need and
 * never construct a path themselves, so the API surface stays declared in one
 * place.
 *
 * Paths are root-relative. In development Vite proxies the `/api` prefix to the
 * Flask server, and in production Flask serves both the SPA and the API from
 * the same origin, so no absolute host is ever needed.
 *
 * The module also owns the request's lifecycle, because it owns the transport:
 * one module-wide timeout bounds every call, and each function takes an
 * optional `AbortSignal` so a caller that owns a superseded view can cancel the
 * request instead of waiting for a reply it will drop.
 */

import axios from 'axios';
import type { AnalysisResponse, ArtistSummary, Track, WeekResponse } from '../types/api';

/**
 * A failed request that carried an HTTP response.
 *
 * `message` is the response's status text (`NOT FOUND`, `BAD REQUEST`), which
 * is the copy the Tracks and Trends panels have always shown for a failed load,
 * and `body` is the parsed response payload, so a caller can read a
 * server-supplied `error` field through a type guard.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

/**
 * The copy a caller shows when a request never reached the API.
 *
 * Every failure that carried a response is an {@link ApiError} carrying that
 * response's status text; a network or DNS failure carries none and has no text
 * to report, which is the one case where the wording has to come from here. It
 * is declared beside the class that detects the difference, so the callers that
 * render it — the search field, the panel and the rank-history chart — say the
 * same thing about the same failure.
 */
export const UNREACHABLE_MESSAGE = 'Unable to reach the server';

/**
 * How long any request this module issues may stay open, in milliseconds.
 *
 * Axios itself defaults to no timeout, so without a bound a stalled proxy or an
 * overloaded backend leaves a call pending for good and the state derived from
 * it never settles. It is applied once, as the module-wide default rather than
 * as a config object each call passes, because this module is the only axios
 * consumer: one default bounds all five calls and every call stays a plain
 * `get(path)`, which is the shape the recorded request rows in `client.test.ts`
 * assert. A request that exceeds the bound rejects with no response, so
 * {@link get} rethrows it unwrapped like any other response-less failure and
 * the caller's existing handling of that failure applies.
 */
const REQUEST_TIMEOUT_MS = 15000;

axios.defaults.timeout = REQUEST_TIMEOUT_MS;

/**
 * Issue a GET and resolve with the parsed payload.
 *
 * Deliberately module-private: an exported generic request helper would let a
 * caller build its own path, which is what this module exists to prevent.
 *
 * `signal` is optional and is forwarded to axios only when it is supplied, so a
 * caller that does not own a request still hands axios the path alone. A caller
 * that owns a superseded view passes the signal of an `AbortController` it
 * aborts when the view unmounts or its input changes; the abort rejects with no
 * response, so it takes the route below like any other response-less failure —
 * rethrown unwrapped, for a caller that has already moved on to drop.
 *
 * The catch tests `axios.isAxiosError(err) && err.response` rather than the
 * axios error alone, because axios rejects a network or DNS failure with
 * `response` undefined. A failure that carries no response is not an HTTP
 * failure the caller can name, so it is rethrown unwrapped for the caller to
 * interpret. Axios's default status validation is left in place, so every
 * non-2xx response rejects and arrives here as an `ApiError`.
 */
async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  try {
    const response =
      signal === undefined
        ? await axios.get<T>(path)
        : await axios.get<T>(path, { signal });
    return response.data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response) {
      const body: unknown = err.response.data;
      throw new ApiError(err.response.statusText, err.response.status, body);
    }
    throw err;
  }
}

/**
 * One week of the chart: `GET /api/week/<week>`.
 *
 * The week is a single path segment, so it is percent-encoded here exactly as
 * the artist segment is in {@link getArtist}: a value carrying `/`, `?` or `#`
 * would otherwise address a different rule, truncate the path or append a
 * query. The encoding is a no-op for the ISO dates the date picker produces.
 */
export async function getWeek(week: string, signal?: AbortSignal): Promise<WeekResponse> {
  return get<WeekResponse>(`/api/week/${encodeURIComponent(week)}`, signal);
}

/**
 * Every chart appearance by artists matching `artist`:
 * `GET /api/artist/<artist>`.
 *
 * The artist is a single path segment on the server even though names carry
 * spaces, commas and ampersands, so the segment is percent-encoded here. The
 * endpoint itself matches case-insensitively on a partial name and answers with
 * a bare array, empty when nothing matches.
 */
export async function getArtist(artist: string, signal?: AbortSignal): Promise<Track[]> {
  return get<Track[]>(`/api/artist/${encodeURIComponent(artist)}`, signal);
}

/**
 * Every chart appearance of one track: `GET /api/track/<spotify_id>`.
 *
 * The Spotify id is a single path segment, so it is percent-encoded here
 * exactly as the artist segment is in {@link getArtist} and
 * {@link getArtistSummary}: an id carrying `/`, `?` or `#` would otherwise
 * address a different rule, truncate the path or append a query. The encoding
 * is a no-op for the base-62 ids Spotify issues.
 *
 * Ordered by rank on the server, so a caller that needs chart order sorts by
 * `week` itself.
 */
export async function getTrack(spotifyId: string, signal?: AbortSignal): Promise<Track[]> {
  return get<Track[]>(`/api/track/${encodeURIComponent(spotifyId)}`, signal);
}

/**
 * One feature's yearly means and rolling average: `GET /api/analysis/<feature>`.
 *
 * The feature is a single path segment, so it is percent-encoded here exactly
 * as the artist segment is in {@link getArtist}: a value carrying `/`, `?` or
 * `#` would otherwise address a different rule, truncate the path or append a
 * query. The encoding is a no-op for the seven names the feature select offers.
 *
 * A feature outside the server's allow-list answers 400 and arrives here as an
 * `ApiError` carrying that status and body.
 */
export async function getAnalysis(
  feature: string,
  signal?: AbortSignal,
): Promise<AnalysisResponse> {
  return get<AnalysisResponse>(`/api/analysis/${encodeURIComponent(feature)}`, signal);
}

/**
 * An artist's chart history aggregated: `GET /api/artist/<artist>/summary`.
 *
 * The artist segment is encoded exactly as in {@link getArtist}. A search that
 * matched nothing is a success whose counts are zero, whose rank and week
 * fields are null and whose `avg_features` is empty.
 */
export async function getArtistSummary(
  artist: string,
  signal?: AbortSignal,
): Promise<ArtistSummary> {
  return get<ArtistSummary>(`/api/artist/${encodeURIComponent(artist)}/summary`, signal);
}
