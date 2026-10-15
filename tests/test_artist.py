'''Tests for the GET /api/artist/<artist> contract.

The route matches its path segment against the chart's artist names as a
case-insensitive substring and answers newest chart week first. The Artist
Explorer groups these rows by track name, so both the match semantics and the
ordering are load-bearing for that feature, and this module pins them.

Every test uses the `client` fixture from tests/conftest.py, whose seed holds
four chart appearances: three weeks of Artist One across two tracks, plus a
second artist sharing the newest week.

Request paths carry the space of an artist name as %20, which is what the
browser client percent-encodes before it calls.

A path segment carrying a NUL byte is the one input this route refuses:
psycopg2 refuses a NUL byte inside a bound literal before the statement
leaves the client, so the segment is answered by the route's own 400 rather
than by a 500 raised out of the ORM's execute. Every other control byte is a
bound parameter like any other character and stays accepted, which the last
case below pins.
'''

from datetime import date

import pytest

# The fields TrackSchema serializes (api/models.py): the row shape the browser
# receives through frontend/src/api/client.ts's getArtist.
ROW_FIELDS = {
    'id', 'week', 'rank', 'track', 'artist', 'spotify_id', 'energy',
    'danceability', 'valence', 'liveness', 'speechiness', 'acousticness',
    'instrumentalness', 'loudness', 'tempo',
}


def test_artist_lookup_returns_its_appearances_newest_week_first(client):
    response = client.get('/api/artist/artist%20one')

    assert response.status_code == 200
    rows = response.get_json()
    # newest chart week first, which is the opposite of the rank ordering the
    # track and week routes use
    assert [row['week'] for row in rows] == [
        '2021-11-27', '2021-11-20', '2021-11-13',
    ]
    assert [row['rank'] for row in rows] == [5, 1, 3]
    assert [row['spotify_id'] for row in rows] == ['sid-b', 'sid-a', 'sid-a']
    assert {row['artist'] for row in rows} == {'Artist One'}


def test_artist_lookup_matches_case_insensitively(client):
    lower = client.get('/api/artist/artist%20one')
    assert lower.status_code == 200

    for term in ('ARTIST%20ONE', 'ArTiSt%20OnE'):
        response = client.get(f'/api/artist/{term}')

        assert response.status_code == 200
        # the same appearances by identity, not merely the same count
        assert [row['id'] for row in response.get_json()] == [3, 2, 1]
        assert response.get_json() == lower.get_json()


def test_partial_term_spans_more_than_one_artist(client):
    response = client.get('/api/artist/artist')

    assert response.status_code == 200
    rows = response.get_json()
    # 'artist' is a substring of both seeded names, which is what shows the
    # route matches on a pattern rather than on an exact name
    assert len(rows) == 4
    assert {row['artist'] for row in rows} == {'Artist One', 'Artist Two'}

    weeks = [row['week'] for row in rows]
    assert weeks == sorted(weeks, reverse=True)
    # The route orders by week descending and by nothing else, so the two rows
    # sharing the newest week (ids 3 and 4) have no specified relative order.
    # SQLite happens to return them in insertion order; that is not a contract,
    # so this module asserts the week sequence is non-increasing and never a
    # strict total order over the rows.


def test_artist_lookup_returns_only_the_named_artist(client):
    response = client.get('/api/artist/artist%20two')

    assert response.status_code == 200
    rows = response.get_json()
    assert len(rows) == 1
    assert (rows[0]['week'], rows[0]['rank'], rows[0]['track'],
            rows[0]['artist'], rows[0]['spotify_id']) == (
        '2021-11-27', 2, 'Track C', 'Artist Two', 'sid-c')


def test_unmatched_artist_returns_an_empty_list(client):
    response = client.get('/api/artist/zzz')

    # a term that matches nothing is an empty result, never a 404
    assert response.status_code == 200
    assert response.get_json() == []


def test_row_carries_the_serialized_track_fields(client):
    rows = client.get('/api/artist/artist%20one').get_json()

    assert set(rows[0]) == ROW_FIELDS
    # marshmallow serializes the DATE column as an ISO 8601 string
    assert isinstance(rows[0]['week'], str)
    assert date.fromisoformat(rows[0]['week']) == date(2021, 11, 27)


def test_nul_byte_in_the_artist_segment_is_rejected(client):
    '''A NUL byte never reaches the bound query parameter.

    The driver refuses a NUL byte inside a bound literal client-side, so the
    segment is answered by this route's own refusal instead of a 500 raised out
    of the execute that carries the LIKE value.
    '''
    response = client.get('/api/artist/a%00b')

    assert response.status_code == 400
    assert response.get_json() == {
        'error': 'Invalid artist: a NUL byte is not allowed in a path segment',
    }


@pytest.mark.parametrize('segment', ['a%09b', 'a%0ab'])
def test_other_control_bytes_are_still_bound_parameters(client, segment):
    '''Only the NUL byte is refused: a tab and a newline bound like any other
    character, so they are an unmatched term rather than a rejected one.'''
    response = client.get(f'/api/artist/{segment}')

    assert response.status_code == 200
    assert response.get_json() == []
