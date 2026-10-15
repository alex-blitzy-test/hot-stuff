import type { KeyboardEvent } from 'react';
import type { Track } from '../../types/api';

/** Identity of the track the user selected in the results list. */
export interface ArtistTrackSelection {
  track: string;
  spotifyId: string;
}

interface ArtistResultsProps {
  tracks: Track[];
  /** Track name of the row whose rank history is displayed, `null` for none. */
  selectedTrack: string | null;
  onSelectTrack: (selection: ArtistTrackSelection) => void;
}

/** One track's chart appearances collapsed into the figures a result row shows. */
interface ArtistTrackGroup {
  track: string;
  /** The peak-ranked appearance's artist; `null` when the payload carries none. */
  artist: string | null;
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
 * The artist travels with that same appearance, so the row's artist line always
 * names the artist whose Spotify id the chart plots rather than whichever row
 * arrived first. `week` is an ISO `YYYY-MM-DD` string, which orders correctly as
 * plain text.
 *
 * A row that is missing any of those four fields is left out of the results
 * entirely: without a `track` there is nothing to group it by, without a `rank`
 * nothing to list it under, without a `week` no span to report and no order to
 * sort it into, and without a `spotify_id` no chart to open. It never becomes a
 * row.
 */
function groupAppearances(tracks: Track[]): ArtistTrackGroup[] {
  const groups = new Map<string, ArtistTrackGroup>();

  tracks.forEach((appearance) => {
    // Every `tracks` column but `id` is nullable in `api/models.py`, and the
    // serializer emits a JSON `null` for a NULL rather than dropping the key.
    if (
      appearance.track === null ||
      appearance.rank === null ||
      appearance.week === null ||
      appearance.spotify_id === null
    ) {
      return;
    }

    const group = groups.get(appearance.track);

    if (group === undefined) {
      groups.set(appearance.track, {
        track: appearance.track,
        artist: appearance.artist,
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
      group.artist = appearance.artist;
    } else if (appearance.rank === group.peakRank && appearance.week < group.peakRankWeek) {
      group.peakRankWeek = appearance.week;
      group.spotifyId = appearance.spotify_id;
      group.artist = appearance.artist;
    }
  });

  return Array.from(groups.values());
}

export default function ArtistResults(props: ArtistResultsProps): JSX.Element {
  const { tracks, selectedTrack, onSelectTrack } = props;
  const groups = groupAppearances(tracks);

  return (
    <>
      {groups.map((group) => {
        const metricsLine =
          `${group.weeksOnChart} ${group.weeksOnChart === 1 ? 'week' : 'weeks'} · ` +
          `${group.firstWeek} → ${group.lastWeek}`;

        // The row is itself the selection control, so the pointer and the
        // keyboard activations share this one call and cannot drift apart.
        const select = () => onSelectTrack({ track: group.track, spotifyId: group.spotifyId });

        const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
          if (event.key !== 'Enter' && event.key !== ' ') {
            return;
          }
          // Space would otherwise scroll the region the rows sit in.
          event.preventDefault();
          select();
        };

        return (
          // The row is itself the selection control, exactly as the ranked rows
          // of the Tracks tab are, and it carries the control semantics that make
          // it reachable without a pointer: focusable, marked while its chart is
          // displayed, and activated by Enter or Space as well as by a click.
          <div
            className='trackRow artistTrackRow'
            key={group.track}
            role='button'
            tabIndex={0}
            aria-pressed={group.track === selectedTrack}
            onClick={select}
            onKeyDown={handleKeyDown}
          >
            <span className='rowEl rank'>{group.peakRank}</span>
            <div className='trackData'>
              {/* The whole panel is one artist, so the track is the primary line here. */}
              <p className='rowEl artist'>{group.track}</p>
              {/* An appearance can carry a null artist, so the row then reports
                  the figures it does have rather than an empty second line. */}
              {group.artist !== null && (
                <p className='rowEl track'>{group.artist}</p>
              )}
              <p className='rowEl track'>{metricsLine}</p>
            </div>
          </div>
        );
      })}
    </>
  );
}
