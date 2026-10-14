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
 * test throw the moment a rejection was exercised. `vi.mock` is hoisted above
 * the imports below, which is why this factory may name the module id it mocks.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { getArtist } from '../../api/client';
import { artistAppearances } from '../../test/fixtures';
import ArtistSearch from './ArtistSearch';

vi.mock('../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../api/client')>();
  return { ...actual, getArtist: vi.fn() };
});

const mockGetArtist = vi.mocked(getArtist);

/** The quiet period the component applies when no `delayMs` is given. */
const DEFAULT_DELAY_MS = 300;

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

    await vi.advanceTimersByTimeAsync(DEFAULT_DELAY_MS);

    // One request for four keystrokes, not four: every keystroke cleared the
    // timer before it, so only the last one survived — the debounce itself.
    await waitFor(() => expect(mockGetArtist).toHaveBeenCalledTimes(1));
    expect(mockGetArtist).toHaveBeenCalledWith('elvis');
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
    await vi.advanceTimersByTimeAsync(DEFAULT_DELAY_MS);
    expect(mockGetArtist).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(delayMs - DEFAULT_DELAY_MS);
    await waitFor(() => expect(mockGetArtist).toHaveBeenCalledTimes(1));
    expect(mockGetArtist).toHaveBeenCalledWith('elvis');
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
    await waitFor(() => expect(mockGetArtist).toHaveBeenCalledWith('Elvis Presley'));
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
});
