"""HTTP route layer defining the hot-stuff REST API contract.

Registers every Flask route against the shared ``app`` object imported from
the ``api`` package (Source: api/__init__.py). Implements the application's
single-origin design: the compiled React single-page application (SPA) is
served at ``/`` from the static build folder, while the JSON API is served
under ``/api/*`` by the same Flask process.

Three module-level schema singletons are instantiated once and reused for
serialization across the handlers (Source: api/routes.py:L7-L9):
    * ``track_schema``  -- serializes a single track (``TrackSchema``).
    * ``tracks_schema`` -- serializes a list of tracks (``TrackSchema(many=True)``).
    * ``yearly_schema`` -- serializes yearly audio-feature averages
      (``YearlyAvgSchema(many=True)``).

Terminology used throughout this module:
    * audio feature: a Spotify-derived numeric attribute of a track
      (e.g. energy, danceability, valence, tempo).
    * chart week: a Billboard Hot 100 week, normalized to its Saturday date.
    * rolling average: the 5-period rolling mean of a yearly feature series.

Depends on ``api.models`` (ORM models and Marshmallow schemas) and
``api.funcs`` (chart-week normalization, weekly aggregation, and
rolling-average helpers).
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
    """Serve the compiled React single-page application (SPA).

    Route:
        GET /

    Returns:
        flask.Response: The static ``index.html`` from the compiled frontend
        build folder (an HTML response), returned via
        ``app.send_static_file('index.html')``. This is the browser entry
        point for the client, per the single-origin design.

    Source:
        api/routes.py:L13-L15
    """
    return app.send_static_file('index.html')


# api/ route redirects to current week
@app.route('/api/', methods=['GET'])
def home():
    """Redirect the JSON API root to the current chart week.

    Route:
        GET /api/

    Returns:
        flask.Response: A 302 redirect to ``week/{currentWeek}``, where
        ``currentWeek`` is ``get_query_week(None)`` -- today's date normalized
        to its Saturday chart week (Source: api/funcs.py).

    Source:
        api/routes.py:L19-L22
    """
    currentWeek = get_query_week(None)
    return redirect(f'week/{currentWeek}')


# get track by id
@app.route('/api/track/<spotify_id>', methods=['GET'])
def get_track_by_id(spotify_id):
    """Fetch every Hot 100 chart appearance for a single Spotify track.

    Route:
        GET /api/track/<spotify_id>

    Args:
        spotify_id (str): The Spotify track ID to look up.

    Returns:
        flask.Response: A JSON array of track objects whose ``spotify_id``
        matches, ordered by ``rank`` ascending and serialized with
        ``tracks_schema`` (``TrackSchema``, many). Empty array when no track
        matches.

    Source:
        api/routes.py:L26-L31
    """
    resultObj = Tracks.query.filter_by(spotify_id=spotify_id).order_by(
        Tracks.rank).all()
    return_list = tracks_schema.dump(resultObj)
    return jsonify(return_list)


# get tracks by week
@app.route('/api/week/<week>', methods=['GET'])
def get_tracks_by_week(week):
    """Fetch the Hot 100 for a chart week plus weekly feature aggregates.

    Route:
        GET /api/week/<week>

    Args:
        week (str): A ``YYYY-MM-DD`` date, normalized to its Saturday chart
            week via ``get_query_week`` (Source: api/funcs.py).

    Returns:
        flask.Response: A JSON object of the shape
        ``{"week", "songs", "averages", "avgTempo"}`` where:

            * ``week`` (str): the normalized Saturday chart week.
            * ``songs`` (list): ``TrackSchema`` objects ordered by ``rank``.
            * ``averages`` (list): ``get_weekly_data`` entries, each shaped
              ``{"feature", "mean", "full"}`` (mean is an int percentage,
              full is 100).
            * ``avgTempo`` (int): mean tempo across the week's songs.

        The ``averages`` and ``avgTempo`` values are produced by
        ``get_weekly_data`` (Source: api/funcs.py).

    Source:
        api/routes.py:L35-L45
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
    """Search tracks by a partial, case-insensitive artist name.

    Route:
        GET /api/artist/<artist>

    Args:
        artist (str): A case-insensitive substring of the artist name,
            matched via ``LOWER(artist) LIKE %artist%``.

    Returns:
        flask.Response: A JSON array of matching track objects ordered by
        ``week`` descending (newest chart week first), serialized with
        ``tracks_schema`` (``TrackSchema``, many).

    Source:
        api/routes.py:L49-L55
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
        GET /api/analysis/<feature>

    Args:
        feature (str): An audio-feature column name (e.g. ``energy``,
            ``danceability``, ``valence``, ``tempo``) resolved dynamically
            against the ``YearlyAvg`` model via ``getattr(YearlyAvg, feature)``.

    Returns:
        tuple[flask.Response, int]: HTTP 200 paired with a JSON object of the
        shape ``{"feature", "data"}`` where ``data`` is a list of
        ``{"year", "value", "rolling"}`` records. ``value`` is the yearly mean
        of the feature and ``rolling`` is the 5-period rolling average computed
        by ``get_rolling_avg`` (Source: api/funcs.py:L27-L37).

    Source:
        api/routes.py:L60-L69
    """
    returnObj = {}
    resultObj = YearlyAvg.query.with_entities(YearlyAvg.year,
                                              getattr(YearlyAvg, feature))
    data = yearly_schema.dump(resultObj)
    dataDict = get_rolling_avg(data)
    returnObj['feature'] = feature
    returnObj['data'] = dataDict
    return jsonify(returnObj), 200
