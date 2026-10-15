/**
 * Tests for the frontend's typed HTTP boundary: `src/api/client.ts`.
 *
 * Each case replaces axios's transport and asserts the two guarantees the
 * module exists to give: the exact path every endpoint function builds, and
 * what a caller receives when the request fails. The payload literals carry the
 * wire shapes declared in `src/types/api.ts`, so a drift between the client and
 * the API surfaces here as a compile error.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnalysisResponse, ArtistSummary, WeekResponse } from '../types/api';
import { ApiError, getAnalysis, getArtist, getArtistSummary, getTrack, getWeek } from './client';
// The shared `Track` fixture set, so the wire shape has exactly one definition
// in the suite: the compiler checks its fifteen fields against `Track` there,
// next to the literals themselves.
import { artistAppearances } from '../test/fixtures';

// The transport, mocked. The real module is kept and only `get` is replaced: a
// bare `vi.mock('axios')` would automock `isAxiosError` into a function
// returning undefined, and the client's `axios.isAxiosError(err) && err.response`
// guard would then never fire, leaving the ApiError path untestable. axios is
// named here only as a module id for these module-mock APIs, never imported
// directly, so `src/api/client.ts` stays the one module under `src` that
// imports it. `vi.hoisted` is what keeps the mock out of the temporal dead
// zone: `vi.mock` factories are hoisted above the module body, where a mock
// declared below them would not exist yet.
const mocks = vi.hoisted(() => ({ get: vi.fn() }));

vi.mock('axios', async (importOriginal) => {
  const actual = await importOriginal<typeof import('axios')>();
  return { ...actual, default: { ...actual.default, get: mocks.get } };
});

/**
 * The real axios module's `AxiosError` class, for the failure fixtures: the
 * class axios itself throws, taken through `vi.importActual` rather than by
 * importing axios directly, so that axios keeps exactly one home under `src`.
 */
async function loadAxiosError(): Promise<typeof import('axios').AxiosError> {
  const actual = await vi.importActual<typeof import('axios')>('axios');
  return actual.AxiosError;
}

/**
 * The value a promise rejected with, failing the test if it resolved instead.
 * Capturing the rejection once is what lets every assertion run against the
 * exact object the client threw.
 */
async function captureRejection(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise;
  } catch (err) {
    return err;
  }
  throw new Error('expected the request to reject');
}

/** Narrow a captured rejection to `ApiError`, failing the test when it is not one. */
function asApiError(err: unknown): ApiError {
  if (!(err instanceof ApiError)) {
    throw new Error(`expected an ApiError, received ${String(err)}`);
  }
  return err;
}

/* Payload fixtures, each checked against the interface it stands for. */

const weekPayload: WeekResponse = {
  week: '2021-11-13',
  // The shared fixture's row for that same week, so the payload's own `week` and
  // the song it carries agree; the rows themselves live in `test/fixtures.ts`.
  songs: [artistAppearances[2]],
  averages: [{ feature: 'Energy', mean: 62, full: 100 }],
  avgTempo: 120,
};

// A five-year window row: `get_rolling_avg` drops every row whose rolling mean
// is undefined, so a payload never carries a null `rolling` and the fixture
// seeds the number a surviving row does carry.
const analysisPayload: AnalysisResponse = {
  feature: 'tempo',
  data: [{ year: '2020', value: 120.5, rolling: 118.72 }],
};

const summaryPayload: ArtistSummary = {
  artist: 'Elvis Presley',
  total_weeks: 3,
  unique_tracks: 2,
  best_rank: 3,
  first_week: '2021-01-02',
  last_week: '2021-11-13',
  avg_features: { energy: 62, tempo: 120 },
};

// What the summary endpoint answers for a search that matched nothing: a
// success carrying zeros, nulls and no averages, never an error.
const noMatchSummary: ArtistSummary = {
  artist: 'Nobody At All',
  total_weeks: 0,
  unique_tracks: 0,
  best_rank: null,
  first_week: null,
  last_week: null,
  avg_features: {},
};

interface RequestCase {
  /** Case name, interpolated into the test title. */
  readonly situation: string;
  /** The path the client must hand to axios, exactly. */
  readonly url: string;
  readonly call: () => Promise<unknown>;
  readonly payload: unknown;
}

// One row per endpoint. `toHaveBeenCalledWith` matches the argument list
// exactly, so each row also proves the client passes the path as its only
// argument and no config object. The artist rows and the reserved-character
// track, week and feature rows are what prove a path segment is
// percent-encoded, and the summary row that the suffix is appended to that same
// encoded segment.
const requestCases: readonly RequestCase[] = [
  {
    situation: 'getWeek requests the week path and resolves with the unwrapped payload',
    url: '/api/week/2021-11-13',
    call: () => getWeek('2021-11-13'),
    payload: weekPayload,
  },
  {
    situation: 'getArtist percent-encodes the space in an artist name',
    url: '/api/artist/Elvis%20Presley',
    call: () => getArtist('Elvis Presley'),
    payload: artistAppearances,
  },
  {
    situation: 'getArtist escapes the comma, space and ampersand of an artist name',
    url: '/api/artist/Earth%2C%20Wind%20%26%20Fire',
    call: () => getArtist('Earth, Wind & Fire'),
    payload: artistAppearances,
  },
  {
    situation: 'getArtistSummary appends /summary to the encoded artist segment',
    url: '/api/artist/Elvis%20Presley/summary',
    call: () => getArtistSummary('Elvis Presley'),
    payload: summaryPayload,
  },
  {
    situation: 'getTrack leaves a base-62 Spotify id unchanged by the encoding',
    url: '/api/track/sid-a',
    call: () => getTrack('sid-a'),
    payload: artistAppearances,
  },
  {
    // The id is not a constant: it is `Track.spotify_id` as the API returned
    // it, so the encoding has to hold for any value. The row above cannot prove
    // that, because `encodeURIComponent` is a no-op for a base-62 id.
    situation: 'getTrack percent-encodes the reserved characters of a Spotify id',
    url: '/api/track/sid%2Fa%3Fb%23c',
    call: () => getTrack('sid/a?b#c'),
    payload: artistAppearances,
  },
  {
    situation: 'getAnalysis leaves a feature name unchanged by the encoding',
    url: '/api/analysis/tempo',
    call: () => getAnalysis('tempo'),
    payload: analysisPayload,
  },
  {
    // The feature is whatever `string` the caller passes, and only seven
    // literal names reach it today. The row above cannot prove the encoding for
    // the same reason as the constant track id: `encodeURIComponent` is a no-op
    // for those lowercase names.
    situation: 'getAnalysis percent-encodes the query delimiter of a feature name',
    url: '/api/analysis/tempo%3Fx',
    call: () => getAnalysis('tempo?x'),
    payload: analysisPayload,
  },
  {
    // The week is the caller's `string` too, and the date picker hands it an
    // ISO date. The constant-week row above cannot prove the encoding either:
    // `encodeURIComponent` leaves such a date unchanged.
    situation: 'getWeek percent-encodes the fragment delimiter of a week value',
    url: '/api/week/2021-11-13%23x',
    call: () => getWeek('2021-11-13#x'),
    payload: weekPayload,
  },
];

describe('client request paths', () => {
  beforeEach(() => {
    mocks.get.mockReset();
  });

  it.each(requestCases)('$situation', async ({ url, call, payload }) => {
    mocks.get.mockResolvedValue({ data: payload });

    await expect(call()).resolves.toBe(payload);
    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(mocks.get).toHaveBeenCalledWith(url);
  });

  it('getArtistSummary resolves the no-match summary rather than rejecting', async () => {
    mocks.get.mockResolvedValue({ data: noMatchSummary });

    await expect(getArtistSummary('Nobody At All')).resolves.toBe(noMatchSummary);
    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(mocks.get).toHaveBeenCalledWith('/api/artist/Nobody%20At%20All/summary');
  });
});

describe('client request configuration', () => {
  beforeEach(() => {
    mocks.get.mockReset();
  });

  it('configures one finite timeout that bounds every request the module issues', async () => {
    // Read through `vi.importActual`, as the AxiosError fixtures do, so axios
    // keeps exactly one home under `src`. The mock above replaces only `get`
    // and keeps the real `defaults` object, so this is the value a real request
    // would use; axios's own default is `0`, which to axios means no timeout at
    // all and is the state this case exists to rule out.
    const actual = await vi.importActual<typeof import('axios')>('axios');
    const { timeout } = actual.default.defaults;

    if (typeof timeout !== 'number') {
      throw new Error(
        `expected the module to configure a numeric timeout, received ${String(timeout)}`,
      );
    }
    expect(Number.isFinite(timeout)).toBe(true);
    expect(timeout).toBeGreaterThan(0);
  });

  it("forwards an explicit AbortSignal as the transport's second argument", async () => {
    const controller = new AbortController();
    mocks.get.mockResolvedValue({ data: artistAppearances });

    await expect(getArtist('Elvis Presley', controller.signal)).resolves.toBe(artistAppearances);
    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(mocks.get).toHaveBeenCalledWith('/api/artist/Elvis%20Presley', {
      signal: controller.signal,
    });
    // The signal-less request rows above are what prove a call without a signal
    // still hands the transport the path alone, with no config object.
  });
});

describe('client error handling', () => {
  beforeEach(() => {
    mocks.get.mockReset();
  });

  it('wraps a failure that carries a response in an ApiError naming the HTTP status text', async () => {
    const AxiosError = await loadAxiosError();
    const failure = Object.assign(
      new AxiosError('Request failed with status code 404'),
      {
        response: {
          status: 404,
          statusText: 'NOT FOUND',
          data: { error: 'Unknown feature: nope' },
        },
      },
    );
    mocks.get.mockRejectedValue(failure);

    const apiError = asApiError(await captureRejection(getAnalysis('not_a_feature')));

    expect(apiError).toBeInstanceOf(Error);
    expect(apiError.name).toBe('ApiError');
    // The HTTP status text, not axios's "Request failed with status code 404":
    // this message is the copy the Tracks and Trends panels show for a failed
    // load, and the body is what lets the Artists panel read the server's error.
    expect(apiError.message).toBe('NOT FOUND');
    expect(apiError.status).toBe(404);
    expect(apiError.body).toEqual({ error: 'Unknown feature: nope' });
  });

  it('rethrows an AxiosError that carries no response, unwrapped', async () => {
    const AxiosError = await loadAxiosError();
    // A network or DNS failure rejects with `response` undefined, which is why
    // the client tests the response and not the axios error alone.
    const failure = new AxiosError('Network Error', 'ERR_NETWORK');
    mocks.get.mockRejectedValue(failure);

    const rejection = await captureRejection(getWeek('2021-11-13'));

    expect(rejection).toBe(failure);
    expect(rejection).not.toBeInstanceOf(ApiError);
  });

  it('rethrows a failure that is not an axios error, unwrapped', async () => {
    const failure = new Error('Network Error');
    mocks.get.mockRejectedValue(failure);

    const rejection = await captureRejection(getArtist('Elvis Presley'));

    expect(rejection).toBe(failure);
    expect(rejection).not.toBeInstanceOf(ApiError);
  });
});
