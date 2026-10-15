'''Tests for the ``GET /api/artist/<artist>/summary`` contract.

The endpoint aggregates a search term's chart appearances server-side, so the
Artist Explorer's header card can render without the browser aggregating. Its
match is the artist route's own case-insensitive one - the term selects the
rows ``GET /api/artist/<artist>`` returns - and it reports the term exactly as
the path carried it: a partial term can match several artists, so echoing the
request is the only deterministic choice.
'''

from datetime import date

import pytest

from api import db
from api.models import Tracks

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


# A single appearance carrying a NULL week. `week` is nullable, and SQL counts
# DISTINCT over non-NULL values only, so this row contributes 0 to the
# distinct-week count while being a matched row. Its feature values are dyadic
# rationals whose percentages are exact, so the weekly helper's integer means
# are the row's own values.
NULL_WEEK_APPEARANCE = {
    'id': 5, 'week': None, 'rank': 7,
    'track': 'Track D', 'artist': 'Null Week Artist', 'spotify_id': 'sid-d',
    'tempo': 100.0, 'energy': 0.50, 'danceability': 0.25,
    'valence': 0.75, 'liveness': 0.10, 'speechiness': 0.75,
    'acousticness': 0.50, 'instrumentalness': 0.25, 'loudness': -8.0,
}

# No week to count and no week to bound, but the matched row still carries
# features, so `avg_features` is that row's own values.
NULL_WEEK_SUMMARY = {
    'artist': 'Null Week Artist',
    'total_weeks': 0,
    'unique_tracks': 1,
    'best_rank': 7,
    'first_week': None,
    'last_week': None,
    'avg_features': {
        'energy': 50,
        'danceability': 25,
        'speechiness': 75,
        'acousticness': 50,
        'instrumentalness': 25,
        'tempo': 100,
    },
}


def test_summary_reports_a_matched_row_whose_week_is_null(app, client):
    '''The empty-match guard keys on the matched rows, not on weeks.

    `week` is nullable and the guard's premise is "rows matched", so an artist
    whose matched rows all carry a NULL week must still report features: the
    distinct-week count of 0 describes the weeks, not the match.
    '''
    db.session.add(Tracks(**NULL_WEEK_APPEARANCE))
    db.session.commit()

    response = client.get('/api/artist/Null%20Week%20Artist/summary')

    assert response.status_code == 200
    assert response.get_json() == NULL_WEEK_SUMMARY


# Two appearances whose helper input carries a whole NULL column: five feature
# columns NULL with tempo present, and tempo NULL with the five features
# present. Both carry a week and a rank, so every aggregate reports the row.
# Either shape leaves the weekly helper a column it cannot average, and both
# are matched rows all the same, so the term is still answered - with the empty
# `avg_features` a term matching nothing answers.
NULL_FEATURE_APPEARANCE = {
    'id': 6, 'week': date(2021, 11, 13), 'rank': 4,
    'track': 'Track E', 'artist': 'Null Feature Artist',
    'spotify_id': 'sid-e', 'tempo': 120.0, 'energy': None,
    'danceability': None, 'valence': 0.40, 'liveness': 0.20,
    'speechiness': None, 'acousticness': None,
    'instrumentalness': None, 'loudness': -6.0,
}

NULL_TEMPO_APPEARANCE = {
    'id': 7, 'week': date(2021, 11, 13), 'rank': 6,
    'track': 'Track F', 'artist': 'Null Tempo Artist',
    'spotify_id': 'sid-f', 'tempo': None, 'energy': 0.50,
    'danceability': 0.50, 'valence': 0.50, 'liveness': 0.50,
    'speechiness': 0.50, 'acousticness': 0.50,
    'instrumentalness': 0.50, 'loudness': -6.0,
}

# The two shapes differ only in which column is NULL, so one parameterised
# case covers both: a single appearance of its own artist, one distinct week
# and one distinct track, the row's own rank, both week bounds the row's ISO
# week, and no averages at all.
NULL_COLUMN_CASES = [
    (NULL_FEATURE_APPEARANCE, '/api/artist/Null%20Feature%20Artist/summary', {
        'artist': 'Null Feature Artist',
        'total_weeks': 1,
        'unique_tracks': 1,
        'best_rank': 4,
        'first_week': '2021-11-13',
        'last_week': '2021-11-13',
        'avg_features': {},
    }),
    (NULL_TEMPO_APPEARANCE, '/api/artist/Null%20Tempo%20Artist/summary', {
        'artist': 'Null Tempo Artist',
        'total_weeks': 1,
        'unique_tracks': 1,
        'best_rank': 6,
        'first_week': '2021-11-13',
        'last_week': '2021-11-13',
        'avg_features': {},
    }),
]


@pytest.mark.parametrize('row, path, expected', NULL_COLUMN_CASES)
def test_summary_answers_a_column_that_is_null_across_the_match(
        app, client, row, path, expected):
    '''A column the helper cannot average is not a failed request.

    The weekly helper derives each `avg_features` value from a mean, which a
    column that is NULL throughout its input cannot supply, so the matched set
    keeps the empty object the unmatched case reports instead of raising.
    '''
    db.session.add(Tracks(**row))
    db.session.commit()

    response = client.get(path)

    assert response.status_code == 200
    assert response.get_json() == expected
