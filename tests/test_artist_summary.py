'''Tests for the new ``GET /api/artist/<artist>/summary`` contract.

The endpoint aggregates a search term's chart appearances server-side, so the
Artist Explorer's header card can render without the browser aggregating. Its
match is the artist route's own case-insensitive one - the term selects the
rows ``GET /api/artist/<artist>`` returns - and it reports the term exactly as
the path carried it: a partial term can match several artists, so echoing the
request is the only deterministic choice.
'''

import pytest

# The shared seed (tests/conftest.py) holds four chart appearances: Artist One
# over two tracks and three weeks, and Artist Two sharing the newest week.
# `total_weeks` and `unique_tracks` are distinct counts over the matched rows -
# Artist One has three rows but only two tracks - `best_rank` is the minimum
# rank, and `first_week`/`last_week` are ISO date strings, as the week
# serializer emits them, which is also what makes min/max over them
# chronological without parsing.

ARTIST_ONE_SUMMARY = {
    'artist': 'Artist One',
    'total_weeks': 3,
    'unique_tracks': 2,
    'best_rank': 1,
    'first_week': '2021-11-13',
    'last_week': '2021-11-27',
    # the five weekly helper features lowercased plus tempo: the truncated
    # percentage means of the matched rows' own values
    'avg_features': {
        'energy': 71,
        'danceability': 51,
        'speechiness': 23,
        'acousticness': 36,
        'instrumentalness': 20,
        'tempo': 120,
    },
}

# A single appearance: the aggregate is that row's own values.
ARTIST_TWO_SUMMARY = {
    'artist': 'Artist Two',
    'total_weeks': 1,
    'unique_tracks': 1,
    'best_rank': 2,
    'first_week': '2021-11-27',
    'last_week': '2021-11-27',
    'avg_features': {
        'energy': 45,
        'danceability': 35,
        'speechiness': 15,
        'acousticness': 20,
        'instrumentalness': 25,
        'tempo': 100,
    },
}

# The lowercase term matches both seeded artists: three distinct weeks, three
# distinct tracks, and the minimum rank across all four appearances.
PARTIAL_MATCH_SUMMARY = {
    'artist': 'artist',
    'total_weeks': 3,
    'unique_tracks': 3,
    'best_rank': 1,
    'first_week': '2021-11-13',
    'last_week': '2021-11-27',
    'avg_features': {
        'energy': 65,
        'danceability': 47,
        'speechiness': 21,
        'acousticness': 32,
        'instrumentalness': 21,
        'tempo': 115,
    },
}

SUMMARY_CASES = [
    ('/api/artist/Artist%20One/summary', ARTIST_ONE_SUMMARY),
    ('/api/artist/Artist%20Two/summary', ARTIST_TWO_SUMMARY),
    ('/api/artist/artist/summary', PARTIAL_MATCH_SUMMARY),
]

# The weekly helper's five title-cased features lowercased, plus tempo.
AVERAGE_FEATURE_KEYS = {
    'energy', 'danceability', 'speechiness', 'acousticness',
    'instrumentalness', 'tempo',
}


@pytest.mark.parametrize('path, expected', SUMMARY_CASES)
def test_summary_reports_the_matched_appearances(client, path, expected):
    response = client.get(path)

    assert response.status_code == 200
    # the whole payload, so an extra field, a missing one, a re-ordered
    # first/last week or an untruncated mean all fail here
    assert response.get_json() == expected


def test_summary_echoes_the_search_term_as_received(client):
    '''A term is answered as asked, not re-cased to a row's spelling.'''
    response = client.get('/api/artist/ARTIST%20ONE/summary')
    expected = {**ARTIST_ONE_SUMMARY, 'artist': 'ARTIST ONE'}

    assert response.status_code == 200
    assert response.get_json() == expected


@pytest.mark.parametrize('path', [path for path, _ in SUMMARY_CASES])
def test_avg_features_key_its_features_by_lowercase_name(client, path):
    avg_features = client.get(path).get_json()['avg_features']

    assert set(avg_features) == AVERAGE_FEATURE_KEYS
    assert all(isinstance(value, int) for value in avg_features.values())


def test_summary_for_an_unmatched_artist_is_empty_rather_than_an_error(client):
    '''A term matching nothing is an answer, not a failure.

    This branch must never reach ``get_weekly_data``, which raises KeyError on
    an empty row list. Because the fixture's TestConfig sets TESTING = True,
    such a mistake would surface here as a raised KeyError rather than a 500 -
    which is exactly why the case is asserted.
    '''
    response = client.get('/api/artist/zzz/summary')

    assert response.status_code == 200
    assert response.get_json() == {
        'artist': 'zzz',
        'total_weeks': 0,
        'unique_tracks': 0,
        'best_rank': None,
        'first_week': None,
        'last_week': None,
        'avg_features': {},
    }
