/**
 * Shared `Track` fixtures for the frontend test suite.
 *
 * Plain data only: each array stands for the body of a read-only API call —
 * `GET /api/artist/<artist>` and `GET /api/track/<spotify_id>`. The explicit
 * `Track[]` annotations check every literal against the interface declared in
 * `src/types/api.ts`, so a missing field or a mis-typed value fails the
 * `npx tsc --noEmit` gate.
 */

import type { Track } from '../types/api';

// Three appearances by one artist: one track twice with different ranks plus a second track.
export const artistAppearances: Track[] = [
  {
    id: 1,
    week: '2021-10-30',
    rank: 7,
    track: 'September',
    artist: 'Earth, Wind & Fire',
    spotify_id: '4cOdK2wGLETKBW3PvgPWqT',
    energy: 0.83,
    danceability: 0.72,
    valence: 0.94,
    liveness: 0.14,
    speechiness: 0.057,
    acousticness: 0.052,
    instrumentalness: 0.021,
    loudness: -6.5,
    tempo: 124.8,
  },
  {
    id: 2,
    week: '2021-11-06',
    rank: 3,
    track: 'September',
    artist: 'Earth, Wind & Fire',
    spotify_id: '4cOdK2wGLETKBW3PvgPWqT',
    energy: 0.84,
    danceability: 0.73,
    valence: 0.95,
    liveness: 0.15,
    speechiness: 0.058,
    acousticness: 0.049,
    instrumentalness: 0.022,
    loudness: -6.2,
    tempo: 124.9,
  },
  {
    id: 3,
    week: '2021-11-13',
    rank: 12,
    track: 'Boogie Wonderland',
    artist: 'Earth, Wind & Fire',
    spotify_id: '6zsUG8WZR3n1RJKuKzZ2c4',
    energy: 0.86,
    danceability: 0.76,
    valence: 0.91,
    liveness: 0.11,
    speechiness: 0.041,
    acousticness: 0.031,
    instrumentalness: 0.018,
    loudness: -5.8,
    tempo: 128.6,
  },
];

// A single appearance, for the one-point rank-history series.
export const singleAppearance: Track[] = [
  {
    id: 1,
    week: '1968-09-28',
    rank: 1,
    track: 'Hey Jude',
    artist: 'The Beatles',
    spotify_id: '0aym2LBJBk9DAYuHHutrIl',
    energy: 0.41,
    danceability: 0.51,
    valence: 0.51,
    liveness: 0.11,
    speechiness: 0.028,
    acousticness: 0.47,
    instrumentalness: 0.012,
    loudness: -8.1,
    tempo: 74.4,
  },
];

// No appearances, for the search that matches nothing.
export const emptyAppearances: Track[] = [];
