'''Contract tests for ``GET /api/week/<week>``.

The Tracks tab renders exactly what this route returns, so the payload is
pinned as the serializer emits it rather than approximately: the four
top-level keys, the per-song field set, the rank ordering of the songs, the
title-cased feature names of the weekly averages, the ISO date the marshmallow
dump yields for a song's week, and an integer ``avgTempo``. The seed in
``tests/conftest.py`` was chosen so every mean is an exact integer before
truncation, which is what lets each expectation below be a literal.

The week the route echoes is the week the handler *computed* through
``get_query_week``, not the string that was requested, so the Sunday case is a
normalisation assertion and not a second copy of the Saturday one.

This module deliberately holds no case for a week that carries no seeded rows.
``get_weekly_data([])`` raises ``KeyError`` on an empty row list, and
``TestConfig`` sets ``TESTING = True``, so the test client re-raises that
instead of answering 500. That is a frozen limitation of the weekly helper and
not part of this route's contract - do not add an empty-week case here to
"fix" it.
'''

# the field set of api.models.TrackSchema, which is the serializer for `songs`
TRACK_FIELDS = frozenset({
    'id', 'week', 'rank', 'track', 'artist', 'spotify_id', 'energy',
    'danceability', 'valence', 'liveness', 'speechiness', 'acousticness',
    'instrumentalness', 'loudness', 'tempo',
})

# the two seeded weeks that carry rows: one holding a single song and one
# holding two, so both the ordering and the means are meaningful
NEWEST_WEEK = '2021-11-27'
OLDEST_WEEK = '2021-11-13'


def test_week_payload_keys_and_echoed_week(client):
    '''The body holds exactly the four frozen keys and echoes the week
    served.'''
    response = client.get(f'/api/week/{NEWEST_WEEK}')

    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {'week', 'songs', 'averages', 'avgTempo'}
    assert body['week'] == NEWEST_WEEK


def test_week_songs_are_ordered_by_rank(client):
    '''Songs come back in rank order, best rank first.'''
    songs = client.get(f'/api/week/{NEWEST_WEEK}').get_json()['songs']

    assert len(songs) == 2
    assert [song['rank'] for song in songs] == [2, 5]
    assert [song['track'] for song in songs] == ['Track C', 'Track B']
    assert [song['spotify_id'] for song in songs] == ['sid-c', 'sid-b']


def test_week_song_field_set_and_iso_week(client):
    '''Each song carries the serializer's 15 fields and a YYYY-MM-DD week
    string.'''
    songs = client.get(f'/api/week/{NEWEST_WEEK}').get_json()['songs']

    for song in songs:
        assert set(song) == TRACK_FIELDS
        assert song['week'] == NEWEST_WEEK
        assert isinstance(song['week'], str)


def test_week_averages_are_exact_integers_in_feature_order(client):
    '''The weekly means are exact integers in the helper's fixed column
    order.'''
    body = client.get(f'/api/week/{NEWEST_WEEK}').get_json()

    assert body['averages'] == [
        {'feature': 'Energy', 'mean': 65, 'full': 100},
        {'feature': 'Danceability', 'mean': 45, 'full': 100},
        {'feature': 'Speechiness', 'mean': 25, 'full': 100},
        {'feature': 'Acousticness', 'mean': 40, 'full': 100},
        {'feature': 'Instrumentalness', 'mean': 35, 'full': 100},
    ]
    assert all(isinstance(item['mean'], int) for item in body['averages'])
    assert body['avgTempo'] == 115
    assert isinstance(body['avgTempo'], int)


def test_week_single_song_week(client):
    '''A one-song week reports that song's own feature values.'''
    response = client.get(f'/api/week/{OLDEST_WEEK}')

    assert response.status_code == 200
    body = response.get_json()
    assert body['week'] == OLDEST_WEEK
    assert len(body['songs']) == 1
    song = body['songs'][0]
    assert song['rank'] == 3
    assert song['track'] == 'Track A'
    assert song['spotify_id'] == 'sid-a'
    assert [item['mean'] for item in body['averages']] == [60, 50, 10, 20, 5]
    assert body['avgTempo'] == 120


def test_week_sunday_request_normalises_to_the_saturday_chart_week(client):
    '''A Sunday request resolves to the preceding Saturday and serves its
    rows.'''
    sunday = client.get('/api/week/2021-11-14')
    saturday = client.get(f'/api/week/{OLDEST_WEEK}')

    assert sunday.status_code == 200
    assert sunday.get_json() == saturday.get_json()
    assert sunday.get_json()['week'] == OLDEST_WEEK
