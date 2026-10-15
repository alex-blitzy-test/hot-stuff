'''Tests for GET /api/track/<spotify_id> in api/routes.py.

The endpoint returns every chart appearance of one Spotify id, ordered by
rank ascending. That ordering and the serialized row shape are frozen
behaviour; the Artist Explorer's rank-over-time chart re-sorts the
appearances by week itself, so nothing here asserts a chronological order.

Rows come from the canonical seed in tests/conftest.py, reached through the
`client` fixture: sid-a appears twice, sid-b once, and 'nope' matches nothing.
'''

# The serializer's field set (TrackSchema.Meta.fields) exactly.
TRACK_FIELDS = {
    'id', 'week', 'rank', 'track', 'artist', 'spotify_id',
    'energy', 'danceability', 'valence', 'liveness',
    'speechiness', 'acousticness', 'instrumentalness',
    'loudness', 'tempo',
}


def test_track_appearances_are_ordered_by_rank_not_by_week(client):
    response = client.get('/api/track/sid-a')

    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 2

    # Rank ascending, deliberately NOT chronological: sid-a's best rank is its
    # newer week (rank 1 in 2021-11-20) and its worse rank is the older week
    # (rank 3 in 2021-11-13), so the two orders disagree. TrackHistoryChart.tsx
    # sorts by week for its time axis; this endpoint keeps the order it has.
    assert [row['rank'] for row in body] == [1, 3]
    assert [row['week'] for row in body] == ['2021-11-20', '2021-11-13']
    assert [row['id'] for row in body] == [2, 1]

    # The marshmallow dump renders the Date column as an ISO date string.
    assert all(isinstance(row['week'], str) for row in body)
    assert all(row['spotify_id'] == 'sid-a' for row in body)
    assert all(set(row) == TRACK_FIELDS for row in body)


def test_track_with_a_single_appearance_returns_one_row(client):
    response = client.get('/api/track/sid-b')

    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 1
    row = body[0]
    assert (row['rank'], row['week'], row['track'],
            row['spotify_id']) == (5, '2021-11-27', 'Track B', 'sid-b')


def test_track_with_an_unmatched_id_returns_an_empty_list(client):
    response = client.get('/api/track/nope')

    # An unmatched id is an empty collection, never a 404: the route has no
    # not-found branch, and the frontend reads [] as "no appearances".
    assert response.status_code == 200
    assert response.get_json() == []


def test_nul_byte_in_the_spotify_id_segment_is_rejected(client):
    '''A NUL byte never reaches the bound query parameter.

    psycopg2 refuses a NUL byte inside a bound literal client-side, before the
    statement leaves the client, so the segment is answered by this route's own
    refusal instead of a 500 raised out of the execute.
    '''
    response = client.get('/api/track/a%00b')

    assert response.status_code == 400
    assert response.get_json() == {
        'error': (
            'Invalid spotify_id: a NUL byte is not allowed in a path segment'),
    }
