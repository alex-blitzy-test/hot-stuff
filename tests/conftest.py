'''Shared fixtures for the API test suite.

This module is the suite's only application builder and its only source of
test data. The application is always constructed through
``create_app(TestConfig)`` - the test configuration is never selected
implicitly by the factory - and every fixture writes only into the in-memory
SQLite database that ``TestConfig`` binds, which is discarded with the test
that used it.
'''

from datetime import date

import pytest
from flask.testing import FlaskClient

from api import create_app, db
from api.config import TestConfig
from api.models import Tracks, YearlyAvg


class CompatFlaskClient(FlaskClient):
    """Flask 2.0.1 forwards an `as_tuple` keyword Werkzeug 2.2.3 rejects.

    Every request would otherwise raise TypeError out of EnvironBuilder, so
    the keyword is dropped here before the call reaches Werkzeug's client.
    """

    def open(self, *args, **kwargs):
        kwargs.pop('as_tuple', None)
        return super(FlaskClient, self).open(*args, **kwargs)


# Four chart appearances: three weeks of Artist One spread over two tracks,
# plus a second artist sharing the newest week, so per-week averages, rank
# ordering and the artist aggregates are all exercisable from one data set.
# `week` must be a date object - the pinned SQLAlchemy SQLite DATE bind rejects
# a string on INSERT, unlike the comparison the /api/week/<week> query does.
WEEKLY_ROWS = [
    {
        'id': 1, 'week': date(2021, 11, 13), 'rank': 3,
        'track': 'Track A', 'artist': 'Artist One', 'spotify_id': 'sid-a',
        'tempo': 120.0, 'energy': 0.60, 'danceability': 0.50,
        'valence': 0.40, 'liveness': 0.25, 'speechiness': 0.10,
        'acousticness': 0.20, 'instrumentalness': 0.05, 'loudness': -5.0,
    },
    {
        'id': 2, 'week': date(2021, 11, 20), 'rank': 1,
        'track': 'Track A', 'artist': 'Artist One', 'spotify_id': 'sid-a',
        'tempo': 110.0, 'energy': 0.70, 'danceability': 0.50,
        'valence': 0.50, 'liveness': 0.15, 'speechiness': 0.25,
        'acousticness': 0.30, 'instrumentalness': 0.10, 'loudness': -6.0,
    },
    {
        'id': 3, 'week': date(2021, 11, 27), 'rank': 5,
        'track': 'Track B', 'artist': 'Artist One', 'spotify_id': 'sid-b',
        'tempo': 130.0, 'energy': 0.85, 'danceability': 0.55,
        'valence': 0.60, 'liveness': 0.35, 'speechiness': 0.35,
        'acousticness': 0.60, 'instrumentalness': 0.45, 'loudness': -4.0,
    },
    {
        'id': 4, 'week': date(2021, 11, 27), 'rank': 2,
        'track': 'Track C', 'artist': 'Artist Two', 'spotify_id': 'sid-c',
        'tempo': 100.0, 'energy': 0.45, 'danceability': 0.35,
        'valence': 0.45, 'liveness': 0.20, 'speechiness': 0.15,
        'acousticness': 0.20, 'instrumentalness': 0.25, 'loudness': -7.0,
    },
]

# Six consecutive chart years, so the five-row rolling window of the analysis
# endpoint produces exactly its last two values.
YEARLY_ROWS = [
    {
        'index': 0, 'year': '2015', 'energy': 0.1, 'danceability': 0.2,
        'valence': 0.3, 'liveness': 0.4, 'speechiness': 0.5,
        'acousticness': 0.6, 'instrumentalness': 0.05, 'tempo': 100.0,
    },
    {
        'index': 1, 'year': '2016', 'energy': 0.2, 'danceability': 0.3,
        'valence': 0.4, 'liveness': 0.5, 'speechiness': 0.6,
        'acousticness': 0.7, 'instrumentalness': 0.06, 'tempo': 110.0,
    },
    {
        'index': 2, 'year': '2017', 'energy': 0.3, 'danceability': 0.4,
        'valence': 0.5, 'liveness': 0.6, 'speechiness': 0.7,
        'acousticness': 0.8, 'instrumentalness': 0.07, 'tempo': 120.0,
    },
    {
        'index': 3, 'year': '2018', 'energy': 0.4, 'danceability': 0.5,
        'valence': 0.6, 'liveness': 0.7, 'speechiness': 0.8,
        'acousticness': 0.9, 'instrumentalness': 0.08, 'tempo': 130.0,
    },
    {
        'index': 4, 'year': '2019', 'energy': 0.5, 'danceability': 0.6,
        'valence': 0.7, 'liveness': 0.8, 'speechiness': 0.9,
        'acousticness': 1.0, 'instrumentalness': 0.09, 'tempo': 140.0,
    },
    {
        'index': 5, 'year': '2020', 'energy': 0.6, 'danceability': 0.7,
        'valence': 0.8, 'liveness': 0.9, 'speechiness': 1.0,
        'acousticness': 1.1, 'instrumentalness': 0.10, 'tempo': 150.0,
    },
]


@pytest.fixture
def app():
    '''Builds the test application and seeds it with the canonical rows.'''
    application = create_app(TestConfig)
    # installed before any client exists: without it every request raises
    # TypeError on the `as_tuple` keyword the pinned pair cannot agree on
    application.test_client_class = CompatFlaskClient
    with application.app_context():
        db.create_all()
        for row in WEEKLY_ROWS:
            db.session.add(Tracks(**row))
        for row in YEARLY_ROWS:
            db.session.add(YearlyAvg(**row))
        db.session.commit()
        try:
            yield application
        finally:
            db.session.remove()
            db.drop_all()


@pytest.fixture
def client(app):
    '''A test client for the seeded application.'''
    return app.test_client()
