/**
 * The Artist Explorer panel: the fourth tab of the Hot Stuff UI.
 *
 * This container owns the whole of the feature's state — the search term the
 * field reports, the matched chart appearances, the selected track, the summary
 * card and the loading and error state — and sequences the two artist requests:
 * `ArtistSearch` performs only the debounced artist search and reports its
 * outcome upward, and the summary request is issued here when that search
 * completes, matched or not, so the header card's no-appearances state is
 * reachable too. Selecting a track row reveals that track's rank history.
 *
 * Every request goes through the typed API client, which is the only module that
 * talks to the network; nothing here builds a path, reads a credential or stores
 * anything outside React state.
 */

import { useCallback, useRef, useState } from 'react';
import ArtistSearch from './ArtistSearch';
import ArtistResults from './ArtistResults';
import TrackHistoryChart from './TrackHistoryChart';
import Hamburger from '../navigation/Hamburger';
import { getArtistSummary, ApiError } from '../../api/client';
import type { ArtistSearchState } from './ArtistSearch';
import type { ArtistTrackSelection } from './ArtistResults';
import type { ArtistSummary } from '../../types/api';

interface ArtistsSectionProps {
  showNav: () => void;
}

/**
 * The copy shown when a request never reached the API, which is the only
 * failure carrying no HTTP status text to display.
 */
const UNREACHABLE_MESSAGE = 'Unable to reach the server';

const EMPTY_METRIC = '—';

/**
 * The summary card's labelled metrics, in the order the panel presents them.
 *
 * An artist the chart has never held answers with zero counts, a null rank and
 * null weeks, so those are rendered as an em dash rather than as "null", and the
 * feature list collapses to the same dash instead of an empty line.
 * `Object.entries` visits the keys in the order the response body carried them,
 * so the feature list reads the same on every render of a given payload.
 */
function summariseMetrics(
  summary: ArtistSummary
): Array<{ label: string; value: string }> {
  const averageFeatures = Object.entries(summary.avg_features)
    .map(([feature, mean]) => `${feature} ${mean}`)
    .join(' · ');

  return [
    { label: 'Total weeks', value: `${summary.total_weeks}` },
    { label: 'Unique tracks', value: `${summary.unique_tracks}` },
    { label: 'Best rank', value: `${summary.best_rank ?? EMPTY_METRIC}` },
    { label: 'First week', value: `${summary.first_week ?? EMPTY_METRIC}` },
    { label: 'Last week', value: `${summary.last_week ?? EMPTY_METRIC}` },
    {
      label: 'Average features',
      value: averageFeatures === '' ? EMPTY_METRIC : averageFeatures
    }
  ];
}

export default function ArtistsSection(props: ArtistsSectionProps): JSX.Element {
  const { showNav } = props;

  const [search, setSearch] = useState<ArtistSearchState>({
    artist: '',
    loading: false,
    tracks: [],
    error: null
  });
  const [selection, setSelection] = useState<ArtistTrackSelection | null>(null);
  const [summary, setSummary] = useState<ArtistSummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  /*
   * The term the newest search belongs to. A summary reply is accepted only
   * while this still names it, so a response that outlived its term — the user
   * kept typing — cannot overwrite the card of the current search.
   */
  const latestArtistRef = useRef('');

  const handleSearch = useCallback((state: ArtistSearchState) => {
    setSearch(state);

    // A blank field is not a search: the results, the selection, the chart and
    // the card are cleared and no summary request is owed.
    if (state.artist === '') {
      latestArtistRef.current = '';
      setSelection(null);
      setSummary(null);
      setSummaryError(null);
      return;
    }

    // The request is in flight; the terminal report below is where the summary
    // is sequenced from, so exactly one is issued per completed search.
    if (state.loading) {
      return;
    }

    // The artist request failed, so there is no artist to summarise. The panel's
    // error text comes from the search state; the card is cleared instead of
    // showing a summary for a term that was never resolved.
    if (state.error !== null) {
      latestArtistRef.current = '';
      setSummary(null);
      setSummaryError(null);
      return;
    }

    latestArtistRef.current = state.artist;
    // A new result set invalidates the previously selected track and its chart.
    setSelection(null);
    setSummary(null);
    setSummaryError(null);

    getArtistSummary(state.artist)
      .then((result) => {
        if (latestArtistRef.current !== state.artist) {
          return;
        }
        setSummary(result);
      })
      .catch((err: unknown) => {
        if (latestArtistRef.current !== state.artist) {
          return;
        }
        /*
         * ApiError is raised only for a failure that carried an HTTP response,
         * and its message is that response's status text — the same copy the
         * Tracks and Trends panels have always shown. A rejection without a
         * response, an unreachable backend, arrives here unwrapped and has no
         * status text to report, so it is named instead of swallowed: this panel
         * settles on a message rather than sitting on its loading marker.
         */
        setSummaryError(
          err instanceof ApiError ? err.message : UNREACHABLE_MESSAGE
        );
      });
  }, []);

  const handleSelectTrack = useCallback((next: ArtistTrackSelection) => {
    setSelection(next);
  }, []);

  // The search owns its own loading and error state; the summary's failure is
  // reported through the same banner, so the panel always settles on one of them.
  const loading = search.loading;
  const error = search.error ?? summaryError;

  return (
    <div className='section'>
      <div className='topBar'>
        <ArtistSearch onChange={handleSearch} delayMs={300} />
        <Hamburger showNav={showNav} />
      </div>
      {summary !== null && (
        <div className='artistSummary'>
          <h4 className='rowEl artist'>{summary.artist}</h4>
          {summariseMetrics(summary).map((metric) => (
            <div className='artistSummaryRow' key={metric.label}>
              <span className='artistSummaryLabel'>{metric.label}</span>
              <span className='artistSummaryValue'>{metric.value}</span>
            </div>
          ))}
          {/* No appearance answers with zero weeks, so the card says so rather
              than showing a dash for every metric. */}
          {summary.total_weeks === 0 && (
            <h5 className='rowEl track'>No chart appearances</h5>
          )}
        </div>
      )}
      <div className='scroll'>
        {error && <h1 className='error'>{error}</h1>}
        {loading && <h1 className='loading'>. . .</h1>}
        {!loading && !error && (
          <ArtistResults
            tracks={search.tracks}
            onSelectTrack={handleSelectTrack}
          />
        )}
        {/* The selected track's chart is revealed beneath the results, inside
            the scrolling region rather than beside it. The panel is a
            fixed-height flex column, and this region is its only item whose
            overflow gives it a zero minimum height, so a chart placed after the
            region would instead shrink the region — and with it the rows the
            user just selected from — to nothing on a short viewport. Inside the
            region, rows and chart stay reachable by scrolling the panel. */}
        {selection !== null && (
          <div>
            <h4 className='rowEl artist'>{selection.track}</h4>
            <TrackHistoryChart spotifyId={selection.spotifyId} />
          </div>
        )}
      </div>
    </div>
  );
}
