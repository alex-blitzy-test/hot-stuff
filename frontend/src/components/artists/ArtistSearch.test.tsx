/**
 * Tests for the Artist Explorer's debounced search input, `./ArtistSearch`.
 *
 * The component owns the text in the field, waits for a quiet period after the
 * last keystroke and then performs the artist request through the typed client,
 * reporting the outcome upward. These cases cover that debounce and the state
 * it reports, which is what the section container sequences its summary request
 * and its clearing behaviour on; the client's own path and error contracts are
 * covered by `src/api/client.test.ts`.
 *
 * The mocked boundary is the client module, not the transport that module
 * wraps: `src/api/client.ts` is the one module under `src` that performs HTTP,
 * and it is the boundary this component depends on. The real module is kept and
 * only `getArtist` replaced, because the component's catch tests
 * `err instanceof ApiError`, so a factory that dropped that class would make the
 * test throw the moment a rejection was exercised; the two failure cases below
 * enter that branch, one for each of its outcomes, so the component's failure
 * contract is asserted rather than assumed. `vi.mock` is hoisted above the
 * imports below, which is why this factory may name the module id it mocks.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ApiError, getArtist, UNREACHABLE_MESSAGE } from '../../api/client';
import { artistAppearances, emptyAppearances, singleAppearance } from '../../test/fixtures';
import ArtistSearch from './ArtistSearch';
import type { Track } from '../../types/api';

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return { ...actual, getArtist: vi.fn() };
});

const mockGetArtist = vi.mocked(getArtist);

/** The quiet period the component applies when no `delayMs` is given. */
const DEFAULT_DELAY_MS = 300;

/** A pending request the case settles by hand, instead of through the mock. */
interface DeferredRequest {
  /** The promise the mocked client returns for one call. */
  promise: Promise<Track[]>;
  /** Settles that promise with the awaited appearances. */
  resolve: (tracks: Track[]) => void;
  /** Settles that promise with a failure. */
  reject: (reason: unknown) => void;
}

/**
 * A request whose settlement the case controls, so one call can be held in
 * flight while the term moves on.
 *
 * Both handles start as no-ops and are replaced by the executor's, which runs
 * synchronously inside `new Promise`; seeding them that way keeps each handle
 * defined for the type checker without a non-null assertion or a cast.
 */
function deferred(): DeferredRequest {
  let resolve: (tracks: Track[]) => void = () => undefined;
  let reject: (reason: unknown) => void = () => undefined;
  const promise = new Promise<Track[]>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe('ArtistSearch', () => {
  beforeEach(() => {
    /*
     * `shouldAdvanceTime` is required rather than cosmetic: with the bare fake
     * timers this stack hangs on anything a test awaits, because the clock never
     * advances for the work those awaits schedule. The mock is reset as well,
     * since the number of calls is an assertion below and state must not leak
     * between cases.
     */
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockGetArtist.mockReset();
    mockGetArtist.mockResolvedValue(artistAppearances);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('issues one request after the delay, for the last typed value', async () => {
    const onChange = vi.fn();
    render(<ArtistSearch onChange={onChange} />);
    const input = screen.getByPlaceholderText('Artist');

    fireEvent.change(input, { target: { value: 'e' } });
    fireEvent.change(input, { target: { value: 'el' } });
    fireEvent.change(input, { target: { value: 'elv' } });
    fireEvent.change(input, { target: { value: 'elvis' } });

    // Nothing has been requested before the quiet period elapses.
    expect(mockGetArtist).not.toHaveBeenCalled();

    /*
     * Both edges of the default period are pinned, one millisecond apart, and
     * both assertions are synchronous. A `waitFor` here would pin neither: with
     * `shouldAdvanceTime` the fake clock also tracks wall time, so waitFor's own
     * polling would carry the clock past the quiet period, and a call made for
     * any larger period within its budget would satisfy the matcher just as
     * well. `advanceTimersByTime` moves the clock by exactly what it is given
     * and cannot drift, and the timer's callback calls the client before its
     * first `await`, so the call has already happened when the advance returns.
     */
    vi.advanceTimersByTime(DEFAULT_DELAY_MS - 1);
    expect(mockGetArtist).not.toHaveBeenCalled();

    // One request for four keystrokes, not four: every keystroke cleared the
    // timer before it, so only the last one survived — the debounce itself. The
    // second argument is the signal the component aborts when the term changes,
    // so the call is asserted with it rather than by its path alone.
    vi.advanceTimersByTime(1);
    expect(mockGetArtist).toHaveBeenCalledTimes(1);
    expect(mockGetArtist).toHaveBeenCalledWith('elvis', expect.any(AbortSignal));
  });

  it('issues no request for a blank term and reports the cleared state', async () => {
    const onChange = vi.fn();
    render(<ArtistSearch onChange={onChange} />);
    const input = screen.getByPlaceholderText('Artist');

    fireEvent.change(input, { target: { value: '   ' } });
    await vi.advanceTimersByTimeAsync(1000);

    expect(mockGetArtist).not.toHaveBeenCalled();
    // The cleared report — an empty `artist` — is the signal the container reads
    // to drop its results, selection, chart and summary card without asking for
    // a summary of its own, so it is asserted exactly.
    expect(onChange).toHaveBeenLastCalledWith({
      artist: '',
      loading: false,
      tracks: [],
      error: null,
    });
  });

  it('waits the configured delay rather than the default one', async () => {
    const onChange = vi.fn();
    const delayMs = 1000;
    render(<ArtistSearch onChange={onChange} delayMs={delayMs} />);
    const input = screen.getByPlaceholderText('Artist');

    fireEvent.change(input, { target: { value: 'elvis' } });

    // The default's 300 ms must not be the period once one is configured.
    vi.advanceTimersByTime(DEFAULT_DELAY_MS);
    expect(mockGetArtist).not.toHaveBeenCalled();

    /*
     * The configured period is pinned at its own edge the same way, and for the
     * same reason: a `waitFor` would let `shouldAdvanceTime`'s clock tick past
     * the timer, so it would pass for whatever period the component applied.
     * Stopping one millisecond short of `delayMs` fails instead if the prop was
     * ignored, and synchronous advances cannot drift past it.
     */
    vi.advanceTimersByTime(delayMs - DEFAULT_DELAY_MS - 1);
    expect(mockGetArtist).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(mockGetArtist).toHaveBeenCalledTimes(1);
    expect(mockGetArtist).toHaveBeenCalledWith('elvis', expect.any(AbortSignal));
  });

  it('reports the search as loading, then the resolved appearances', async () => {
    const onChange = vi.fn();
    render(<ArtistSearch onChange={onChange} />);
    const input = screen.getByPlaceholderText('Artist');

    fireEvent.change(input, { target: { value: 'Elvis Presley' } });
    await vi.advanceTimersByTimeAsync(DEFAULT_DELAY_MS);

    // The trimmed term is what reaches the client, and the request it makes is
    // reported before it is awaited: that in-flight report is what the panel
    // shows its loading marker for.
    await waitFor(() =>
      expect(mockGetArtist).toHaveBeenCalledWith('Elvis Presley', expect.any(AbortSignal)),
    );
    expect(onChange).toHaveBeenCalledWith({
      artist: 'Elvis Presley',
      loading: true,
      tracks: [],
      error: null,
    });

    await waitFor(() =>
      expect(onChange).toHaveBeenLastCalledWith({
        artist: 'Elvis Presley',
        loading: false,
        tracks: artistAppearances,
        error: null,
      }),
    );
  });

  /*
   * The first branch of the failure contract: a rejection that carried an HTTP
   * response arrives as an `ApiError` whose message is that response's status
   * text — the copy the Tracks and Trends panels have always shown — and the
   * report clears `loading`, so the panel settles out of its loading marker.
   * The instance is built from the class the mocked module re-exports, which is
   * the real one, so the component's `instanceof` check is what narrows it.
   */
  it('reports the status text and clears loading when the API answers with an error', async () => {
    const onChange = vi.fn();
    mockGetArtist.mockRejectedValueOnce(new ApiError('NOT FOUND', 404, { error: 'not found' }));
    render(<ArtistSearch onChange={onChange} />);
    const input = screen.getByPlaceholderText('Artist');

    fireEvent.change(input, { target: { value: 'elvis' } });
    await vi.advanceTimersByTimeAsync(DEFAULT_DELAY_MS);

    await waitFor(() =>
      expect(onChange).toHaveBeenLastCalledWith({
        artist: 'elvis',
        loading: false,
        tracks: [],
        error: 'NOT FOUND',
      }),
    );
    // The in-flight report was made first and is not the last one: the panel
    // showed its loading marker for this term before the failure replaced it.
    expect(onChange).toHaveBeenCalledWith({
      artist: 'elvis',
      loading: true,
      tracks: [],
      error: null,
    });
  });

  /*
   * The second branch: a rejection with no response — an unreachable backend, or
   * a request the component itself aborted — carries no status text, so the
   * report names it with the client's shared `UNREACHABLE_MESSAGE` and clears
   * `loading` too. This is the one failure the frozen panels stay silent for and
   * this panel deliberately does not, so the divergence is pinned here.
   */
  it('reports the shared unreachable message when a failure carries no response', async () => {
    const onChange = vi.fn();
    mockGetArtist.mockRejectedValueOnce(new Error('Network Error'));
    render(<ArtistSearch onChange={onChange} />);
    const input = screen.getByPlaceholderText('Artist');

    fireEvent.change(input, { target: { value: 'elvis' } });
    await vi.advanceTimersByTimeAsync(DEFAULT_DELAY_MS);

    await waitFor(() =>
      expect(onChange).toHaveBeenLastCalledWith({
        artist: 'elvis',
        loading: false,
        tracks: [],
        error: UNREACHABLE_MESSAGE,
      }),
    );
    expect(onChange).toHaveBeenCalledWith({
      artist: 'elvis',
      loading: true,
      tracks: [],
      error: null,
    });
  });

  /*
   * Supersession: the user types on while a request is in flight, so the effect's
   * cleanup aborts that request's controller and neither a late reply nor a late
   * failure may overwrite the newer term's report or raise a banner for a term
   * nobody is looking at. The abandoned request's two settle shapes are the two
   * rows of one case, because the component's guard is the same either way.
   */
  it.each([
    {
      outcome: 'answers late',
      settleAbandoned: (abandoned: DeferredRequest) => abandoned.resolve(artistAppearances),
    },
    {
      outcome: 'fails late',
      settleAbandoned: (abandoned: DeferredRequest) => abandoned.reject(new Error('canceled')),
    },
  ])('keeps the newer report when the abandoned request $outcome', async ({ settleAbandoned }) => {
    const onChange = vi.fn();
    const abandoned = deferred();
    const current = deferred();
    mockGetArtist
      .mockImplementationOnce(() => abandoned.promise)
      .mockImplementationOnce(() => current.promise);
    render(<ArtistSearch onChange={onChange} />);
    const input = screen.getByPlaceholderText('Artist');

    fireEvent.change(input, { target: { value: 'elvis' } });
    await vi.advanceTimersByTimeAsync(DEFAULT_DELAY_MS);
    expect(mockGetArtist).toHaveBeenCalledTimes(1);

    // The term moves on while the first request is still unanswered, which is
    // the only moment the cleanup's abort is observable: the abandoned run's
    // signal is aborted, the current run's — created by the next effect — is not.
    const abandonedSignal = mockGetArtist.mock.calls[0][1];
    fireEvent.change(input, { target: { value: 'costello' } });
    expect(abandonedSignal?.aborted).toBe(true);

    await vi.advanceTimersByTimeAsync(DEFAULT_DELAY_MS);
    expect(mockGetArtist).toHaveBeenNthCalledWith(2, 'costello', expect.any(AbortSignal));
    expect(mockGetArtist.mock.calls[1][1]?.aborted).toBe(false);

    // The current term settles first, and its report is what the panel shows...
    current.resolve(singleAppearance);
    await waitFor(() =>
      expect(onChange).toHaveBeenLastCalledWith({
        artist: 'costello',
        loading: false,
        tracks: singleAppearance,
        error: null,
      }),
    );

    /*
     * ...and it stays shown once the abandoned request settles, whichever way it
     * settles: the mocked client ignores the abort, so only the component's
     * `superseded` guard can keep this reply or this failure from overwriting
     * the newer report. The flush drains that continuation before the assertion.
     */
    settleAbandoned(abandoned);
    await vi.advanceTimersByTimeAsync(0);
    expect(onChange).toHaveBeenLastCalledWith({
      artist: 'costello',
      loading: false,
      tracks: singleAppearance,
      error: null,
    });
  });

  /*
   * A search that matched nothing is a success with no rows, not a failure: the
   * endpoint answers with an empty array, so the report carries it with `loading`
   * cleared and no error, which is the state the container renders an empty
   * results region for instead of a banner. `emptyAppearances` is the shared
   * fixture for exactly that answer.
   */
  it('reports a search that matched nothing as an empty result, not an error', async () => {
    const onChange = vi.fn();
    mockGetArtist.mockResolvedValueOnce(emptyAppearances);
    render(<ArtistSearch onChange={onChange} />);
    const input = screen.getByPlaceholderText('Artist');

    fireEvent.change(input, { target: { value: 'Nobody At All' } });
    await vi.advanceTimersByTimeAsync(DEFAULT_DELAY_MS);

    await waitFor(() =>
      expect(onChange).toHaveBeenLastCalledWith({
        artist: 'Nobody At All',
        loading: false,
        tracks: emptyAppearances,
        error: null,
      }),
    );
  });
});
