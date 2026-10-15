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
import { getArtistSummary, ApiError, UNREACHABLE_MESSAGE } from '../../api/client';
import type { ArtistSearchState } from './ArtistSearch';
import type { ArtistTrackSelection } from './ArtistResults';
import type { ArtistSummary } from '../../types/api';

interface ArtistsSectionProps {
  showNav: () => void;
}

const EMPTY_METRIC = '—';

/**
 * The summary card's labelled metrics, in the order the panel presents them.
 *
 * An artist the chart has never held answers with zero counts, a null rank and
 * null weeks, so those are rendered as an em dash rather than as "null", and the
 * feature list collapses to the same dash instead of an empty line.
 * The best rank is the card's headline figure, so it is the one entry marked as
 * such: it is the same figure the ranked rows present at the larger `.rank` size.
 * `Object.entries` visits the keys in the order the response body carried them,
 * so the feature list reads the same on every render of a given payload.
 */
function summariseMetrics(
  summary: ArtistSummary
): Array<{ label: string; value: string; headline: boolean }> {
  const averageFeatures = Object.entries(summary.avg_features)
    .map(([feature, mean]) => `${feature} ${mean}`)
    .join(' · ');

  return [
    { label: 'Total weeks', value: `${summary.total_weeks}`, headline: false },
    { label: 'Unique tracks', value: `${summary.unique_tracks}`, headline: false },
    { label: 'Best rank', value: `${summary.best_rank ?? EMPTY_METRIC}`, headline: true },
    { label: 'First week', value: `${summary.first_week ?? EMPTY_METRIC}`, headline: false },
    { label: 'Last week', value: `${summary.last_week ?? EMPTY_METRIC}`, headline: false },
    {
      label: 'Average features',
      value: averageFeatures === '' ? EMPTY_METRIC : averageFeatures,
      headline: false
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
         * status text to report, so it is named with the client's shared
         * `UNREACHABLE_MESSAGE` instead of being swallowed: this panel settles
         * on a message rather than sitting on its loading marker.
         */
        setSummaryError(
          err instanceof ApiError ? err.message : UNREACHABLE_MESSAGE
        );
      });
  }, []);

  const handleSelectTrack = useCallback((next: ArtistTrackSelection) => {
    setSelection(next);
  }, []);

  /*
   * The search and the summary own separate error state. The search's failure
   * belongs inside the results region, which has nothing to show without it;
   * the summary's failure belongs against the card slot, which is the only
   * element the summary request feeds. Both are shown, so a failed summary
   * never removes results a search already found.
   */
  const loading = search.loading;

  return (
    <div className='section'>
      <div className='topBar'>
        <ArtistSearch onChange={handleSearch} delayMs={300} />
        <Hamburger showNav={showNav} />
      </div>
      {/* The panel's whole content is search-driven and changes without a page
          load, so the regions that change are live. This one is the summary's
          slot and is rendered from first paint, so the card or the error message
          arrives inside a region that already exists. */}
      <div aria-live='polite'>
        {/* The summary's own outcome takes the card slot: on a failure the card
            is already null, because the handler clears it before issuing the
            request, so the error text stands in its place and the results below
            — which the search produced — stay on screen. */}
        {summaryError !== null && <h1 className='error'>{summaryError}</h1>}
        {summary !== null && (
          <div className='artistSummary'>
            {/* The panel's subject is the artist it describes, so its name is the
                panel's top-level heading: the chart caption below sits one level
                down, the loading and error text keeps the level the other panels
                use, and the result rows carry no heading at all. The class still
                supplies the card-title treatment, so the element costs no visual
                change. */}
            <h1 className='rowEl artist'>{summary.artist}</h1>
            {summariseMetrics(summary).map((metric) => (
              <div className='artistSummaryRow' key={metric.label}>
                <span className='artistSummaryLabel'>{metric.label}</span>
                <span
                  className={
                    metric.headline
                      ? 'artistSummaryValue artistSummaryHeadline'
                      : 'artistSummaryValue'
                  }
                >
                  {metric.value}
                </span>
              </div>
            ))}
            {/* No appearance answers with zero weeks, so the card says so rather
                than showing a dash for every metric. */}
            {summary.total_weeks === 0 && (
              <p className='rowEl track'>No chart appearances</p>
            )}
          </div>
        )}
      </div>
      {/* The results region is live as well: its loading marker, a search
          failure and the matched rows replace one another here with no page
          load, and the banner is the assertive one of the two. The banner and
          the loading marker keep the markup the Tracks and Trends panels use,
          so the same text and the same three-dot marker render at the same size
          as on those tabs. */}
      <div className='scroll' aria-live='polite'>
        {search.error !== null && (
          <h1 className='error' role='alert'>{search.error}</h1>
        )}
        {loading && <h1 className='loading'>. . .</h1>}
        {!loading && search.error === null && (
          <ArtistResults
            tracks={search.tracks}
            selectedTrack={selection === null ? null : selection.track}
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
            <h2 className='rowEl artist'>{selection.track}</h2>
            <TrackHistoryChart spotifyId={selection.spotifyId} />
          </div>
        )}
      </div>
    </div>
  );
}
