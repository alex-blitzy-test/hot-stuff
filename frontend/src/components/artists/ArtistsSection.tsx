/**
 * The Artist Explorer panel: the fourth tab of the Hot Stuff UI.
 *
 * This container owns the whole of the feature's state — the search term the
 * field reports, that term's result payload, the selected track and the loading
 * and error state — and sequences the two artist requests: `ArtistSearch`
 * performs only the debounced artist search and reports its outcome upward, and
 * the summary request is issued here when that search completes, matched or not,
 * so the header card's no-appearances state is reachable too. Selecting a track
 * row reveals that track's rank history.
 *
 * A completed search and its summary are one payload, published in a single
 * commit: the card and the rows it describes therefore appear together, and the
 * payload already on screen is kept until the next one is complete. The card,
 * the results and the chart all sit inside the scrolling region, whose only
 * sibling is the fixed top bar, so nothing is ever inserted above content the
 * user is already reading and the region's top edge never moves.
 *
 * Every request goes through the typed API client, which is the only module that
 * talks to the network; nothing here builds a path, reads a credential or stores
 * anything outside React state.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import ArtistSearch from './ArtistSearch';
import ArtistResults from './ArtistResults';
import TrackHistoryChart from './TrackHistoryChart';
import Hamburger from '../navigation/Hamburger';
import { getArtistSummary, ApiError, UNREACHABLE_MESSAGE } from '../../api/client';
import type { ArtistSearchState } from './ArtistSearch';
import type { ArtistTrackSelection } from './ArtistResults';
import type { ArtistSummary, Track } from '../../types/api';

interface ArtistsSectionProps {
  showNav: () => void;
}

const EMPTY_METRIC = '—';

/**
 * One term's whole payload: the appearances its artist search returned and the
 * summary that describes them.
 *
 * The two requests are separate — the summary is issued only once the artist
 * search has completed — but they are one payload to this panel, because the
 * card belongs above the rows it describes. Both halves are therefore set in the
 * same callback, which React batches into one commit, so the rows are never
 * painted without the card that precedes them. `artist` names the term the
 * payload answers, which is how the panel tells a settled payload from one that
 * is still settling.
 */
interface ArtistPanelResult {
  /** The trimmed term this payload answers. */
  artist: string;
  /** The appearances that term's search returned. */
  tracks: Track[];
  summary: ArtistSummary | null;
  summaryError: string | null;
}

/**
 * The summary card's labelled metrics, in the order the panel presents them.
 *
 * An artist the chart has never held answers with zero counts, a null rank and
 * null weeks, so those are rendered as an em dash rather than as "null", and the
 * feature list collapses to the same dash instead of an empty line.
 * The best rank is the card's headline figure, so it is the one entry marked as
 * such: it is the one value rendered at the card's 25px headline size, flush
 * with the other five values in the card's single value column.
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
  /*
   * How many times a result row has been activated, which is the key the chart
   * below renders under. Selecting the row that is already selected hands the
   * chart the Spotify id it already has, so the chart's own effect — keyed on
   * that id — would never run again and could neither retry a failed request nor
   * rebuild a chart. A count of activations is what tells a second activation
   * apart from the first, and it is kept here because the activation is the
   * container's to observe: the chart's props stay the selection's id alone.
   */
  const [selectionActivation, setSelectionActivation] = useState(0);
  /*
   * The payload on screen, or `null` while the panel has none to show. One piece
   * of state rather than one per half is what makes the card and its rows a
   * single commit: a separate summary state would be set by a later render and
   * would land above rows that had already been painted.
   */
  const [result, setResult] = useState<ArtistPanelResult | null>(null);

  /*
   * The summary request that is in flight, held by identity rather than by the
   * term it was issued for. Every report this handler receives supersedes the
   * request that came before it: the old one is aborted and the ref dropped, and
   * a reply is accepted only while the ref still holds the controller it was
   * issued under. Identity is what a term cannot supply here, because an abort
   * rejects with no response and the user can come back to a term whose aborted
   * request is still settling: a term-matching guard would take that rejection
   * for a failure of the live search and put an unreachable-server message on
   * the card.
   */
  const summaryRequestRef = useRef<AbortController | null>(null);

  const handleSearch = useCallback((state: ArtistSearchState) => {
    setSearch(state);

    /*
     * Every report — blank field, request in flight, failed search or completed
     * one — stops the previous summary request here instead of letting it run to
     * completion for a reply this handler would drop.
     */
    summaryRequestRef.current?.abort();
    summaryRequestRef.current = null;

    // A blank field is not a search: the results, the selection, the chart and
    // the card are cleared and no summary request is owed.
    if (state.artist === '') {
      setSelection(null);
      setResult(null);
      return;
    }

    /*
     * The artist request is in flight, so no payload is owed yet. What is on
     * screen is left exactly as it is: the previous term's rows and card stay
     * until the terminal report below brings the new payload, which is what keeps
     * the region from emptying itself — and from blinking — for the length of the
     * debounce and the request after it.
     */
    if (state.loading) {
      return;
    }

    /*
     * The artist request failed, so there is no artist to summarise and no
     * payload to keep: the payload and the chart the previous payload's selection
     * had opened are cleared together, in this one report, so the region shows
     * this report's error text alone rather than beside a track the panel no
     * longer lists.
     */
    if (state.error !== null) {
      setSelection(null);
      setResult(null);
      return;
    }

    /*
     * The summary is asked for under the controller the ref now holds: it is what
     * both handlers below check to know whether this is still the summary the
     * panel is waiting on. Nothing is cleared here: the payload on screen stays
     * whole — its rows, its card and the chart its selection opened — until the
     * new one is published, and the previous selection is then cleared in the
     * same commit as that payload.
     */
    const controller = new AbortController();
    summaryRequestRef.current = controller;

    getArtistSummary(state.artist, controller.signal)
      .then((summary) => {
        if (summaryRequestRef.current !== controller) {
          return;
        }
        /*
         * The payload replaces the one on screen whole, in this one commit: the
         * previous payload's selection — and with it the chart that selection
         * opened — leaves with the rows and the card it belonged to, so the panel
         * never shows a chart captioned for a track its rows no longer list.
         */
        setSelection(null);
        setResult({
          artist: state.artist,
          tracks: state.tracks,
          summary,
          summaryError: null
        });
      })
      .catch((err: unknown) => {
        if (summaryRequestRef.current !== controller) {
          return;
        }
        /*
         * The copy the Tracks and Trends panels show — except that a failure
         * with no response is reported here rather than leaving the card
         * silent: it settles on the client's shared `UNREACHABLE_MESSAGE`. The
         * payload and the previous selection's chart are published and cleared
         * together here too, so this payload — its rows and its error text, with
         * no card — arrives as one whole replacement.
         */
        setSelection(null);
        setResult({
          artist: state.artist,
          tracks: state.tracks,
          summary: null,
          summaryError: err instanceof ApiError ? err.message : UNREACHABLE_MESSAGE
        });
      });
  }, []);

  /*
   * A summary still settling when the panel goes away is stopped, and the ref is
   * emptied first so its rejection finds no request to belong to and sets no
   * state. Without this the request outlives the component whose card it was
   * fetched for.
   */
  useEffect(
    () => () => {
      const pending = summaryRequestRef.current;
      summaryRequestRef.current = null;
      pending?.abort();
    },
    []
  );

  const handleSelectTrack = useCallback((next: ArtistTrackSelection) => {
    setSelection(next);

    /*
     * Counted on every activation, because the activation and not the track is
     * what the chart must re-run its request for: a second activation of the
     * selected row is the panel's only gesture that asks for that track's rank
     * history again, and it is what recovers the chart once the API answers
     * again. The count has to move before the chart renders, so the key changes
     * in the same commit as the selection does.
     */
    setSelectionActivation((activation) => activation + 1);
  }, []);

  /*
   * A term is still settling while its artist request is in flight, or while the
   * summary of a completed search for it has not yet arrived: the payload's own
   * term is what says which of those it is, so no flag has to be kept in step
   * with the requests. `result.artist` is the term whose rows are on screen, and
   * a payload answering some other term is the one that is still settling — the
   * rows below it belong to the previous search and stay there until this one is
   * complete.
   */
  const artist = search.artist;
  const pending =
    search.error === null &&
    (search.loading || (artist !== '' && result?.artist !== artist));
  const summary = result?.summary ?? null;
  const summaryError = result?.summaryError ?? null;
  const tracks = result?.tracks ?? null;

  return (
    <div className='section'>
      <div className='topBar'>
        <ArtistSearch onChange={handleSearch} delayMs={300} />
        <Hamburger showNav={showNav} />
      </div>
      {/* Everything below the top bar is search-driven and changes without a
          page load, so it is one live region, and it is also the panel's only
          scrolling one: the card, the results, the states and the chart all
          live inside it. That is what holds the region's top edge still — the
          fixed top bar is its only sibling — so a payload arriving can only
          move content inside the region, never the region itself. It is
          rendered from first paint, so the card or the error message arrives
          inside a region that already exists. */}
      <div className='scroll' aria-live='polite' aria-busy={pending}>
        {/* The summary's own outcome takes the card slot ahead of the rows it
            describes: a failed summary carries no card, so its error text stands
            where the card would be and the results below — which the search
            produced — stay on screen. */}
        {/* The class sits on a wrapper rather than on the heading, because the
            shared stylesheet rule centres an `h1` that is inside `.error`: the
            wrapper is what makes this banner centre like the loading marker. */}
        {summaryError !== null && (
          <div className='error'>
            <h1>{summaryError}</h1>
          </div>
        )}
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
                  className={metric.headline ? 'artistSummaryHeadline' : 'artistSummaryValue'}
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
        {/* A failed search has no payload at all, so its banner stands alone in
            the region and is the assertive one of the two. The class and the
            assertive role sit on a wrapper, which is what lets the shared
            stylesheet rule centre the banner; its text and heading size stay the
            ones the Tracks and Trends panels show, and the loading marker keeps
            the markup those panels use. */}
        {search.error !== null && (
          <div className='error' role='alert'>
            <h1>{search.error}</h1>
          </div>
        )}
        {/* The marker is shown only while there is no payload to keep: the first
            search of a mount, and the one after a blank field or a failed search.
            A retained payload reports the search in flight through `aria-busy`
            instead, so the user never loses the results they were reading. */}
        {pending && result === null && <h1 className='loading'>. . .</h1>}
        {search.error === null && tracks !== null && (
          <ArtistResults
            tracks={tracks}
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
            {/* Keyed on the activation count rather than on the selected track,
                so activating a row rebuilds the chart: a fresh element means a
                fresh effect — new request, error cleared, host rebuilt — which
                is what re-asks for the track whose history is already on screen.
                An unchanged Spotify id cannot carry that, because it is the same
                on the re-activation as it was on the request that failed. */}
            <TrackHistoryChart
              key={selectionActivation}
              spotifyId={selection.spotifyId}
            />
          </div>
        )}
      </div>
    </div>
  );
}
