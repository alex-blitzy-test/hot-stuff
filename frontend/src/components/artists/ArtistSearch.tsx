/**
 * Debounced artist search for the Artist Explorer.
 *
 * The component owns the text in the field and reports the outcome of every
 * artist request upward through a single `onChange` callback; the section
 * container owns the matched appearances, the selected track and the summary
 * card. All HTTP access goes through the typed client, which is the only module
 * that talks to the network or builds a URL, so this file names no path and
 * stores nothing.
 */

import { useEffect, useRef, useState } from 'react';
import { getArtist, ApiError, UNREACHABLE_MESSAGE } from '../../api/client';
import type { Track } from '../../types/api';

/** The outcome of one artist search, as reported to the container. */
export interface ArtistSearchState {
  /**
   * The trimmed term this state belongs to, and empty once the field is
   * cleared. The container needs it because an artist's summary is a separate
   * path, requested when the search completes, and because it is what lets the
   * container tell the state of the current search from a superseded one.
   */
  artist: string;
  loading: boolean;
  /** Matching chart appearances, flat as the artist endpoint returns them. */
  tracks: Track[];
  error: string | null;
}

interface ArtistSearchProps {
  onChange: (state: ArtistSearchState) => void;
  /** Quiet period after the last keystroke, before a request is issued. */
  delayMs?: number;
}

const DEFAULT_DELAY_MS = 300;

export default function ArtistSearch(props: ArtistSearchProps): JSX.Element {
  const { onChange, delayMs } = props;
  const [term, setTerm] = useState('');

  /*
   * The callback is read through a ref so that the effect below depends on the
   * term alone. A container passing an inline arrow — which is how a section
   * wires its children — would otherwise hand over a new function identity on
   * every render, restarting the timer each time and leaving the debounce
   * permanently reset.
   */
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    const artist = term.trim();

    // A blank field is not a search: it clears the container's results,
    // selection, chart and summary card, and issues nothing.
    if (artist === '') {
      onChangeRef.current({ artist: '', loading: false, tracks: [], error: null });
      return;
    }

    // Raised by the cleanup below, so a reply that outlived its term — the user
    // typed on while it was in flight — cannot overwrite the current search.
    let superseded = false;

    /*
     * The handle on this run's request. One controller belongs to one run of the
     * effect, and the cleanup aborts it: a term the user has already left stops
     * transferring and parsing a body whose reply would be dropped anyway,
     * instead of running to completion long after the timer that started it is
     * gone. It is not created above the blank-term return, because a field with
     * nothing in it issues no request to stop.
     */
    const controller = new AbortController();

    const timer = window.setTimeout(async () => {
      onChangeRef.current({ artist, loading: true, tracks: [], error: null });

      try {
        const tracks = await getArtist(artist, controller.signal);

        if (superseded) {
          return;
        }

        onChangeRef.current({ artist, loading: false, tracks, error: null });
      } catch (err) {
        if (superseded) {
          return;
        }

        onChangeRef.current({
          artist,
          loading: false,
          tracks: [],
          /*
           * ApiError is raised only for a failure that carried an HTTP
           * response, and its message is that response's status text — the same
           * copy the Tracks and Trends panels have always shown. A rejection
           * without a response, an unreachable backend, arrives here unwrapped
           * and has no status text to report, so it is named with the client's
           * shared `UNREACHABLE_MESSAGE` instead of being swallowed: the panel
           * settles on a message rather than sitting on its loading marker.
           */
          error: err instanceof ApiError ? err.message : UNREACHABLE_MESSAGE,
        });
      }
    }, delayMs ?? DEFAULT_DELAY_MS);

    return () => {
      /*
       * `superseded` is raised before the abort because the abort is what makes
       * the awaited request reject, and the handlers above drop a reply only
       * once that flag is set: an aborted request arrives as a rejection with no
       * response, and it is the flag rather than the rejection's shape that says
       * this reply belonged to a term that is gone.
       */
      superseded = true;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [term, delayMs]);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setTerm(event.target.value);
  };

  return (
    <input
      className='inputField'
      type='text'
      value={term}
      onChange={handleChange}
      placeholder='Artist'
      aria-label='Artist'
    />
  );
}
