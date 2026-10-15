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

# registered by create_app, which passes no prefix: a prefix given to
# register_blueprint replaces this one instead of extending it
bp = Blueprint('api', __name__, url_prefix='/api')


# api/ route redirects to current week
@bp.route('/', methods=['GET'])
def home() -> Response:
    currentWeek = get_query_week(None)
    return redirect(f'week/{currentWeek}')


# get track by id
@bp.route('/track/<spotify_id>', methods=['GET'])
def get_track_by_id(spotify_id: str) -> Response:
    resultObj = Tracks.query.filter_by(spotify_id=spotify_id).order_by(
        Tracks.rank).all()
    return_list = tracks_schema.dump(resultObj)
    return jsonify(return_list)


# get tracks by week
@bp.route('/week/<week>', methods=['GET'])
def get_tracks_by_week(week: str) -> Response:
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
def get_tracks_by_artist(artist: str) -> Response:
    resultObj = Tracks.query.filter(
        func.lower(Tracks.artist).like(func.lower(f'%{artist}%'))).order_by(
            Tracks.week.desc()).all()
    return_list = tracks_schema.dump(resultObj)
    return jsonify(return_list)


# get an artist's chart appearances summarised
@bp.route('/artist/<artist>/summary', methods=['GET'])
def get_artist_summary(artist: str) -> tuple[Response, int]:
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
        songs = tracks_schema.dump(Tracks.query.filter(match).all())
        weeklyData = get_weekly_data(songs)
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
    resultObj = YearlyAvg.query.with_entities(YearlyAvg.year,
                                              getattr(YearlyAvg, feature))
    data = yearly_schema.dump(resultObj)
    dataDict = get_rolling_avg(data)
    returnObj['feature'] = feature
    returnObj['data'] = dataDict
    return jsonify(returnObj), 200
