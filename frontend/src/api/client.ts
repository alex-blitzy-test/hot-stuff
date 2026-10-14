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
 * Issue a GET and resolve with the parsed payload.
 *
 * Deliberately module-private: an exported generic request helper would let a
 * caller build its own path, which is what this module exists to prevent.
 *
 * The catch tests `axios.isAxiosError(err) && err.response` rather than the
 * axios error alone, because axios rejects a network or DNS failure with
 * `response` undefined. A failure that carries no response is not an HTTP
 * failure the caller can name, so it is rethrown unwrapped for the caller to
 * interpret. Axios's default status validation is left in place, so every
 * non-2xx response rejects and arrives here as an `ApiError`.
 */
async function get<T>(path: string): Promise<T> {
  try {
    const response = await axios.get<T>(path);
    return response.data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response) {
      const body: unknown = err.response.data;
      throw new ApiError(err.response.statusText, err.response.status, body);
    }
    throw err;
  }
}

/** One week of the chart: `GET /api/week/<week>`. */
export async function getWeek(week: string): Promise<WeekResponse> {
  return get<WeekResponse>(`/api/week/${week}`);
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
export async function getArtist(artist: string): Promise<Track[]> {
  return get<Track[]>(`/api/artist/${encodeURIComponent(artist)}`);
}

/**
 * Every chart appearance of one track: `GET /api/track/<spotify_id>`.
 *
 * Ordered by rank on the server, so a caller that needs chart order sorts by
 * `week` itself.
 */
export async function getTrack(spotifyId: string): Promise<Track[]> {
  return get<Track[]>(`/api/track/${spotifyId}`);
}

/**
 * One feature's yearly means and rolling average: `GET /api/analysis/<feature>`.
 *
 * A feature outside the server's allow-list answers 400 and arrives here as an
 * `ApiError` carrying that status and body.
 */
export async function getAnalysis(feature: string): Promise<AnalysisResponse> {
  return get<AnalysisResponse>(`/api/analysis/${feature}`);
}

/**
 * An artist's chart history aggregated: `GET /api/artist/<artist>/summary`.
 *
 * The artist segment is encoded exactly as in {@link getArtist}. A search that
 * matched nothing is a success whose counts are zero, whose rank and week
 * fields are null and whose `avg_features` is empty.
 */
export async function getArtistSummary(artist: string): Promise<ArtistSummary> {
  return get<ArtistSummary>(`/api/artist/${encodeURIComponent(artist)}/summary`);
}
