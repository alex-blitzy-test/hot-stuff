"""HTTP route layer defining the hot-stuff REST API contract.

This module registers every Flask route against the shared application object
``app`` (imported from the ``api`` package; Source: api/__init__.py). The app
uses a single-origin design: one Flask process serves the compiled React
single-page application (SPA) at ``/`` and the JSON API under ``/api/*``.

Three module-level Marshmallow schema singletons are instantiated once and
reused for serialization by the route handlers (Source: api/routes.py:L7-L9):

    * ``track_schema``  -- serialize a single track (``TrackSchema()``).
    * ``tracks_schema`` -- serialize many tracks (``TrackSchema(many=True)``).
    * ``yearly_schema`` -- serialize many yearly audio-feature averages
      (``YearlyAvgSchema(many=True)``).

The handlers normalize chart weeks, query Billboard Hot 100 chart data, and
compute weekly aggregates and rolling averages. This module depends on
``api.models`` for the ORM models/schemas and on ``api.funcs`` for the
chart-week normalization, weekly-aggregation, and rolling-average helpers.

Source: api/routes.py:L1-L69
"""
from flask import redirect, request, jsonify
from api.models import Tracks, TrackSchema, YearlyAvg, YearlyAvgSchema
from sqlalchemy import func
from api import app
from api.funcs import get_query_week, get_rolling_avg, get_weekly_data

track_schema = TrackSchema()
tracks_schema = TrackSchema(many=True)
yearly_schema = YearlyAvgSchema(many=True)


# home route serves app from react build folder
@app.route('/')
def index():
    """Serve the compiled React single-page application.

    Route:
        ``GET /``

    Returns:
        flask.Response: The static ``index.html`` from the compiled frontend
        build folder (an HTML response), produced by
        ``app.send_static_file('index.html')``.

    Source: api/routes.py:L13-L15
    """
    return app.send_static_file('index.html')


# api/ route redirects to current week
@app.route('/api/', methods=['GET'])
def home():
    """Redirect the API root to the current chart week.

    Route:
        ``GET /api/``

    Returns:
        flask.Response: A ``302`` redirect to ``week/{currentWeek}``, where
        ``currentWeek = get_query_week(None)`` -- today normalized to its
        Saturday chart week (Source: api/funcs.py).

    Source: api/routes.py:L19-L22
    """
    currentWeek = get_query_week(None)
    return redirect(f'week/{currentWeek}')


# get track by id
@app.route('/api/track/<spotify_id>', methods=['GET'])
def get_track_by_id(spotify_id):
    """Fetch every chart appearance for a single Spotify track.

    Route:
        ``GET /api/track/<spotify_id>``

    Args:
        spotify_id (str): The Spotify track ID matched against
            ``Tracks.spotify_id``.

    Returns:
        flask.Response: A JSON array of track objects matching ``spotify_id``,
        ordered by ``rank`` and serialized with ``TrackSchema(many=True)``.

    Source: api/routes.py:L26-L31
    """
    resultObj = Tracks.query.filter_by(spotify_id=spotify_id).order_by(
        Tracks.rank).all()
    return_list = tracks_schema.dump(resultObj)
    return jsonify(return_list)


# get tracks by week
@app.route('/api/week/<week>', methods=['GET'])
def get_tracks_by_week(week):
    """Fetch the Hot 100 for a chart week plus weekly aggregates.

    Route:
        ``GET /api/week/<week>``

    Args:
        week (str): A ``YYYY-MM-DD`` date; normalized to its Saturday chart
            week via ``get_query_week`` (Source: api/funcs.py).

    Returns:
        flask.Response: A JSON object of the form
        ``{"week": <normalized>, "songs": [...TrackSchema...],
        "averages": [{"feature", "mean", "full"}], "avgTempo": <int>}``,
        where ``averages`` and ``avgTempo`` are produced by
        ``get_weekly_data`` (Source: api/funcs.py).

    Source: api/routes.py:L35-L45
    """
    week = get_query_week(week)
    returnObj = {'week': week}
    songsObj = Tracks.query.filter_by(week=week).order_by(Tracks.rank).all()
    songs = tracks_schema.dump(songsObj)
    weeklyData = get_weekly_data(songs)
    returnObj['songs'] = songs
    returnObj['averages'] = weeklyData['averages']
    returnObj['avgTempo'] = weeklyData['avgTempo']
    return jsonify(returnObj)


# get tracks by artist
@app.route('/api/artist/<artist>', methods=['GET'])
def get_tracks_by_artist(artist):
    """Search tracks by (case-insensitive) artist name.

    Route:
        ``GET /api/artist/<artist>``

    Args:
        artist (str): A case-insensitive substring matched against the artist
            column via ``LOWER(artist) LIKE %artist%``.

    Returns:
        flask.Response: A JSON array of matching tracks ordered by ``week``
        descending (newest chart week first), serialized with
        ``TrackSchema(many=True)``.

    Source: api/routes.py:L49-L55
    """
    resultObj = Tracks.query.filter(
        func.lower(Tracks.artist).like(func.lower(f'%{artist}%'))).order_by(
            Tracks.week.desc()).all()
    return_list = tracks_schema.dump(resultObj)
    return jsonify(return_list)


# get yearly mean
# and rolling average of feature
@app.route('/api/analysis/<feature>', methods=['GET'])
def get_avg_feature(feature):
    """Return the yearly mean and rolling average for one audio feature.

    Route:
        ``GET /api/analysis/<feature>``

    Args:
        feature (str): An audio-feature column name (e.g. ``energy``,
            ``danceability``, ``valence``, ``tempo``) resolved dynamically
            via ``getattr(YearlyAvg, feature)``.

    Returns:
        tuple: HTTP ``200`` with a JSON object of the form
        ``{"feature": <feature>, "data": [{"year", "value", "rolling"}]}``,
        where ``rolling`` is the 5-period rolling average computed by
        ``get_rolling_avg`` (Source: api/funcs.py:L27-L37).

    Source: api/routes.py:L60-L69
    """
    returnObj = {}
    resultObj = YearlyAvg.query.with_entities(YearlyAvg.year,
                                              getattr(YearlyAvg, feature))
    data = yearly_schema.dump(resultObj)
    dataDict = get_rolling_avg(data)
    returnObj['feature'] = feature
    returnObj['data'] = dataDict
    return jsonify(returnObj), 200
