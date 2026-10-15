from datetime import datetime
from math import isfinite
from typing import Any

import pandas as pd
from flask import Blueprint, Response, jsonify, redirect
from api.models import Tracks, TrackSchema, YearlyAvg, YearlyAvgSchema
from sqlalchemy import func
from api.funcs import get_query_week, get_rolling_avg, get_weekly_data

tracks_schema = TrackSchema(many=True)
yearly_schema = YearlyAvgSchema(many=True)

# features the analysis route may project: the yearly averages the table holds,
# which are its columns without the row key and the year label
ANALYSIS_FEATURES: frozenset[str] = frozenset(
    column.name for column in YearlyAvg.__table__.columns
) - {'index', 'year'}

# the six numeric columns the weekly helper reads: the summary's matched-row
# read projects them instead of the whole wide row, which nothing there uses
SUMMARY_FEATURES: tuple[str, ...] = (
    'energy', 'danceability', 'speechiness', 'acousticness',
    'instrumentalness', 'tempo',
)

# registered by create_app, which passes no prefix: a prefix given to
# register_blueprint replaces this one instead of extending it
bp = Blueprint('api', __name__, url_prefix='/api')


def _computable_avg_features(songs: list[dict[str, Any]]) -> dict[str, int]:
    '''Averages the weekly features whose cast the weekly helper can make.

    get_weekly_data averages SUMMARY_FEATURES in one pass and casts each mean,
    so a single column it cannot cast costs every feature the same rows could
    supply. This settles the features one at a time over those same rows, in
    the helper's own order and with the helper's own arithmetic - a percentage
    for the five averaged features and the bare mean for tempo - over a
    DataFrame built the same way, whose mean skips NULL values. Only the
    features whose value has no integer to cast to are left out.
    '''
    df = pd.DataFrame(songs)
    features: dict[str, int] = {}
    for feature in SUMMARY_FEATURES:
        mean = float(df[feature].mean())
        # the helper's cast, made on Python floats so an out-of-range
        # percentage is infinity rather than a numpy warning: a mean NULL
        # across the rows and a percentage too large to represent both fail
        # the finiteness test, which is exactly the set their int() cannot take
        value = mean if feature == 'tempo' else mean * 100
        if isfinite(value):
            features[feature] = int(value)
    return features


def _is_iso_week(segment: str) -> bool:
    '''Whether a week segment is the padded ISO date its payload echoes.

    The segment has to parse and to round-trip through that same format:
    strptime accepts an unpadded month and day, so '2021-1-3' parses while the
    week computed from it - 2021-01-02 - is a chart week of its own; and a
    segment that is no date at all is refused here rather than raising out of
    the handler's get_query_week call.
    '''
    try:
        parsed = datetime.strptime(segment, '%Y-%m-%d')
    except ValueError:
        return False
    return parsed.strftime('%Y-%m-%d') == segment


# psycopg2 refuses a NUL byte inside a bound literal before the statement
# leaves the client, so the artist, summary and track rules hold their path
# segment to that one byte rather than handing it to the driver to raise. The
# other control bytes bind like any other character and stay accepted.
def _nul_byte_refusal(
        segment: str, parameter: str) -> tuple[Response, int] | None:
    '''The 400 a rule answers for a segment carrying a NUL byte, else None.

    `parameter` is the rule's own path parameter, so the refusal reads as the
    route that produced it.
    '''
    if '\x00' in segment:
        refusal = (f'Invalid {parameter}: a NUL byte is not allowed in a '
                   'path segment')
        return jsonify({'error': refusal}), 400
    return None


# api/ route redirects to current week
@bp.route('/', methods=['GET'])
def home() -> Response:
    currentWeek = get_query_week(None)
    return redirect(f'week/{currentWeek}')


# get track by id
@bp.route('/track/<spotify_id>', methods=['GET'])
def get_track_by_id(spotify_id: str) -> Response | tuple[Response, int]:
    refusal = _nul_byte_refusal(spotify_id, 'spotify_id')
    if refusal is not None:
        return refusal
    resultObj = Tracks.query.filter_by(spotify_id=spotify_id).order_by(
        Tracks.rank).all()
    return_list = tracks_schema.dump(resultObj)
    return jsonify(return_list)


# get tracks by week
@bp.route('/week/<week>', methods=['GET'])
def get_tracks_by_week(week: str) -> Response | tuple[Response, int]:
    if not _is_iso_week(week):
        return jsonify({'error': f'Invalid week: {week}'}), 400
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
@bp.route('/artist/<artist>', methods=['GET'])
def get_tracks_by_artist(artist: str) -> Response | tuple[Response, int]:
    refusal = _nul_byte_refusal(artist, 'artist')
    if refusal is not None:
        return refusal
    resultObj = Tracks.query.filter(
        func.lower(Tracks.artist).like(func.lower(f'%{artist}%'))).order_by(
            Tracks.week.desc()).all()
    return_list = tracks_schema.dump(resultObj)
    return jsonify(return_list)


# get an artist's chart appearances summarised
@bp.route('/artist/<artist>/summary', methods=['GET'])
def get_artist_summary(artist: str) -> tuple[Response, int]:
    refusal = _nul_byte_refusal(artist, 'artist')
    if refusal is not None:
        return refusal
    match = func.lower(Tracks.artist).like(func.lower(f'%{artist}%'))
    matchedRows, totalWeeks, uniqueTracks, bestRank, firstWeek, lastWeek = (
        Tracks.query.with_entities(
            func.count(),
            func.count(func.distinct(Tracks.week)),
            func.count(func.distinct(Tracks.track)),
            func.min(Tracks.rank),
            func.min(Tracks.week),
            func.max(Tracks.week),
        ).filter(match).one()
    )
    summaryObj = {
        'artist': artist,
        'total_weeks': totalWeeks,
        'unique_tracks': uniqueTracks,
        'best_rank': bestRank,
        'first_week': str(firstWeek)[:10] if firstWeek else None,
        'last_week': str(lastWeek)[:10] if lastWeek else None,
        'avg_features': {},
    }
    # the weekly helper raises on an empty row list, so an artist with no
    # appearance at all is answered from the aggregate alone: the matched-row
    # count is the premise, because a matched row can carry a NULL week and so
    # count towards no distinct week at all
    if matchedRows:
        songs = [
            dict(zip(SUMMARY_FEATURES, row))
            for row in Tracks.query.with_entities(
                Tracks.energy, Tracks.danceability, Tracks.speechiness,
                Tracks.acousticness, Tracks.instrumentalness,
                Tracks.tempo).filter(match)
        ]
        try:
            weeklyData = get_weekly_data(songs)
        except (ValueError, OverflowError):
            # the helper averages all six features in one pass, so an
            # arithmetic failure settles only the features it affects: a
            # column NULL across the whole match and a value too large to cast
            # each leave their own feature out, and a matched row set is still
            # a legal answer that keeps every computable one
            summaryObj['avg_features'] = _computable_avg_features(songs)
        else:
            avgFeatures = {item['feature'].lower(): item['mean']
                           for item in weeklyData['averages']}
            avgFeatures['tempo'] = weeklyData['avgTempo']
            summaryObj['avg_features'] = avgFeatures
    return jsonify(summaryObj), 200


# get yearly mean
# and rolling average of feature
@bp.route('/analysis/<feature>', methods=['GET'])
def get_avg_feature(feature: str) -> tuple[Response, int]:
    if feature not in ANALYSIS_FEATURES:
        return jsonify({'error': f'Unknown feature: {feature}'}), 400
    returnObj = {}
    resultObj = YearlyAvg.query.with_entities(
        YearlyAvg.year, getattr(YearlyAvg, feature)).order_by(YearlyAvg.year)
    data = yearly_schema.dump(resultObj)
    dataDict = get_rolling_avg(data)
    returnObj['feature'] = feature
    returnObj['data'] = dataDict
    return jsonify(returnObj), 200
