import type { Track } from '../../types/api';

/** Identity of the track the user selected in the results list. */
export interface ArtistTrackSelection {
  track: string;
  spotifyId: string;
}

interface ArtistResultsProps {
  tracks: Track[];
  onSelectTrack: (selection: ArtistTrackSelection) => void;
}

/** One track's chart appearances collapsed into the figures a result row shows. */
interface ArtistTrackGroup {
  track: string;
  peakRank: number;
  weeksOnChart: number;
  firstWeek: string;
  lastWeek: string;
  spotifyId: string;
  /** Earliest chart week at which the group's current peak rank was reached. */
  peakRankWeek: string;
}

/**
 * Collapse an artist's appearances into one entry per distinct track.
 *
 * Rank 1 is the best position, so a track's peak rank is the minimum of its
 * ranks, and the Spotify id is taken from the peak-ranked appearance. A tie on
 * that rank is settled by the earliest week among the tied rows, so the chart
 * selection does not depend on the order the payload happens to arrive in.
 * `week` is an ISO `YYYY-MM-DD` string, which orders correctly as plain text.
 */
function groupAppearances(tracks: Track[]): ArtistTrackGroup[] {
  const groups = new Map<string, ArtistTrackGroup>();

  tracks.forEach((appearance) => {
    const group = groups.get(appearance.track);

    if (group === undefined) {
      groups.set(appearance.track, {
        track: appearance.track,
        peakRank: appearance.rank,
        weeksOnChart: 1,
        firstWeek: appearance.week,
        lastWeek: appearance.week,
        spotifyId: appearance.spotify_id,
        peakRankWeek: appearance.week,
      });
      return;
    }

    group.weeksOnChart += 1;

    if (appearance.week < group.firstWeek) {
      group.firstWeek = appearance.week;
    }
    if (appearance.week > group.lastWeek) {
      group.lastWeek = appearance.week;
    }

    if (appearance.rank < group.peakRank) {
      group.peakRank = appearance.rank;
      group.peakRankWeek = appearance.week;
      group.spotifyId = appearance.spotify_id;
    } else if (appearance.rank === group.peakRank && appearance.week < group.peakRankWeek) {
      group.peakRankWeek = appearance.week;
      group.spotifyId = appearance.spotify_id;
    }
  });

  return Array.from(groups.values());
}

export default function ArtistResults(props: ArtistResultsProps): JSX.Element {
  const { tracks, onSelectTrack } = props;
  const groups = groupAppearances(tracks);

  return (
    <>
      {groups.map((group) => {
        const metricsLine = `${group.weeksOnChart} weeks · ${group.firstWeek} → ${group.lastWeek}`;

        return (
          // The row is itself the selection control, exactly as the ranked rows
          // of the Tracks tab are, so no nested control or ARIA role is added.
          //
          // BLITZY [A11Y]: that leaves the row reachable by pointer only — it is
          // not focusable and no key activates it. Implemented this way for
          // structural parity with the frozen Tracks-tab row; flagged for
          // designer review rather than silently changed.
          <div
            className='trackRow'
            key={group.track}
            onClick={() => onSelectTrack({ track: group.track, spotifyId: group.spotifyId })}
          >
            <h1 className='rowEl rank'>{group.peakRank}</h1>
            <span className='trackData'>
              {/* The whole panel is one artist, so the track is the primary line here. */}
              <h4 className='rowEl artist'>{group.track}</h4>
              <h5 className='rowEl track'>{metricsLine}</h5>
            </span>
          </div>
        );
      })}
    </>
  );
}
